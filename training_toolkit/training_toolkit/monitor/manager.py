import os
import signal
import time
from typing import List, Optional

from training_toolkit.utils.ranktable import Server
from training_toolkit.utils.cpu_bound import get_cpu_bound_subcmd_list
from training_toolkit.monitor.task import Task
from training_toolkit.config import config
from training_toolkit.logger.log import run_log
from training_toolkit.utils.validator import IntValidator, RangeValidator


def signal_handler(func):
    def receive_signal(signum, stack):
        """
        set flag to exit
        Args:
            signum: 
            stack: 

        Returns:

        """
        run_log.info(f"received signal %d, start to notify all forked task processes: {signum} ")
        stack.f_locals["self"].receive_signal = True

    def wait_child(signal, stack):
        """
        avoid zombie process
        Args:
            signal: 
            stask: 

        Returns:

        """
        try:
            c_pid, status = os.waitpid(-1, os.WNOHANG)
            run_log.info(f"child pid: {c_pid} exist, status: {status}")
        except OSError as e:
            run_log.warning(f"failed to wait child process exist, errno: {e.errno}")

    def handle_func(self, *args, **kwargs):
        signal.signal(signal.SIGCHLD, wait_child)

        term_origin_handle = signal.getsignal(signal.SIGTERM)
        int_origin_handle = signal.getsignal(signal.SIGINT)

        signal.signal(signal.SIGTERM, receive_signal)
        signal.signal(signal.SIGINT, receive_signal)

        res = func(self, *args, **kwargs)

        signal.signal(signal.SIGTERM, term_origin_handle)
        signal.signal(signal.SIGINT, int_origin_handle)
        return res

    return handle_func


class ProcessManager:
    """
    Manager for training processes
    """

    def __init__(self, server: Server):
        self.server = server
        self.device_num = int(os.environ[config.RANK_SIZE_ENV_KEY])
        self._cmd = ""
        self._log_dir = ""
        self._platform = ""
        self._cd = ""
        self.receive_signal = False
        self.task_list: List[Task] = []

    @property
    def cmd(self):
        return self._cmd

    @cmd.setter
    def cmd(self, value):
        self._cmd = value

    @property
    def log_dir(self):
        return self._log_dir

    @log_dir.setter
    def log_dir(self, value):
        self._log_dir = value

    @property
    def cd(self):
        return self._cd

    @cd.setter
    def cd(self, value):
        self._cd = value

    @property
    def platform(self):
        return self._platform

    @platform.setter
    def platform(self, value):
        self._platform = value

    def run(self, bind_cpu=False, extra_env: Optional[List[str]] = None):
        """
        fork sub process for each device
        Args:
            bind_cpu:
            extra_env:

        Returns:

        """
        enable_stdout = True
        # Pytorch will spawn its own subprocess.
        if self.platform == config.PlatformType.Pytorch.value:
            train_task = Task(0, None, self.cmd, self.device_num)
            train_task.run(
                self.log_dir,
                self.platform,
                enable_stdout,
                cd_dir=self.cd,
                extra_env=extra_env
            )
            self.task_list.append(train_task)
            return

        process_num = min(self.device_num, config.MAX_CHIP_ONE_NODE)
        cpu_list = get_cpu_bound_subcmd_list(process_num)

        for index in range(process_num):
            if index != 0:
                enable_stdout = False

            device = self.server.devices[index] if self.server is not None else None
            cmd = self.cmd if not bind_cpu else cpu_list[index] + self.cmd
            train_task = Task(index, device, cmd, self.device_num)
            train_task.run(
                self.log_dir,
                self.platform,
                enable_stdout,
                cd_dir=self.cd,
                extra_env=extra_env
            )
            self.task_list.append(train_task)

    @signal_handler
    def wait(self) -> int:
        """
        periodically check the status of training task process
        Returns: exit code

        """
        process_num = len(self.task_list)

        def is_complete():
            complete_num = 0
            code = 0
            for index in range(process_num):
                task = self.task_list[index]
                # poll return None means process is running
                if task.training_process.poll() is not None:
                    code = task.training_process.returncode
                    if code != 0:  # not normally exit
                        run_log.error(f"process exited with non-zero code: {code}, {str(task)}")
                        return False, code
                    complete_num += 1

            return complete_num == process_num, code

        while True:
            done, code = is_complete()
            if code != 0:
                return code

            if done or self.receive_signal:
                return 0

            time.sleep(config.CHECK_INTERVAL)

    def clean_all(self):
        """
        notify forked processes to exist and wait
        Returns:
        """
        run_log.info("notify forked processes to exist")
        for task_index in range(len(self.task_list) - 1, -1, -1):
            task = self.task_list[task_index]
            if task.training_process.poll() is not None:
                run_log.info(f"process: {task.training_process.pid} exists before receiving SIGTERM signal")
                del self.task_list[task_index]

            try:
                os.killpg(task.training_process.pid, signal.SIGTERM)
                run_log.info(f"SIGTERM signal has been send to process: {task.training_process.pid}")
            except ProcessLookupError:
                pass

        waiting_time_str = os.environ.get(config.TERMINATION_GRACE_PERIOD_SECONDS_ENV_KEY,
                                          config.TERMINATION_GRACE_PERIOD_SECONDS_ENV_VAL)
        time_validate_chain = IntValidator()
        time_validate_chain.set_next(RangeValidator(config.MIN_GRACE_TIME, config.MAX_GRACE_TIME))
        flag = time_validate_chain.validate(waiting_time_str)
        if not flag:
            run_log.warning(f"TERMINATION_GRACE_PERIOD_SECONDS not valid (should between {config.MIN_GRACE_TIME} and"
                            f" {config.MAX_GRACE_TIME}), "
                            f"use default value: {config.TERMINATION_GRACE_PERIOD_SECONDS_ENV_VAL}")
        waiting_time = int(waiting_time_str)
        run_log.info(f"wait forked process to exist, max waiting time: {waiting_time}s")

        st = time.time()
        while len(self.task_list) > 0 and (time.time() - st) < waiting_time:
            for task_index in range(len(self.task_list) - 1, -1, -1):
                task = self.task_list[task_index]
                if task.training_process.poll() is not None:
                    run_log.info(f"process: {task.training_process.pid} exists")
                    del self.task_list[task_index]

            if not self.task_list:
                break
            time.sleep(config.CHECK_INTERVAL)

        if not self.task_list:
            return

        run_log.info(f"{len(self.task_list)} processes still running:"
                     f" {','.join([str(t.training_process.pid) for t in self.task_list])}."
                     f"start to force killing")

        for task_index in range(len(self.task_list) - 1, -1, -1):
            task = self.task_list[task_index]
            if task.training_process.poll() is not None:
                run_log.info(f"send kill signal to process: {task.training_process.pid}")

            os.killpg(task.training_process.pid, signal.SIGKILL)
            if task.log_redirect_process is not None:
                os.killpg(task.log_redirect_process.pid, signal.SIGKILL)

        time.sleep(config.CHECK_INTERVAL)
