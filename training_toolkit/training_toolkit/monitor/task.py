import os
import subprocess
from typing import Optional, List
from contextlib import ContextDecorator

from training_toolkit.utils.validator import DirValidator
from training_toolkit.utils.ranktable import Device
from training_toolkit.config.config import ASCEND_DEVICE_ID_ENV_KEY, DEVICE_ID_ENV_KEY, RANK_ID_ENV_KEY, \
    PYTORCH_RANK_ENV_KEY, PlatformType, DEVICE_INDEX_ENV_KEY, DEFAULT_LOG_SUB_DIR
from training_toolkit.logger.log import run_log
from training_toolkit.utils.common import get_host_ip, substitute_arg_with_env


class CDContextManager(ContextDecorator):
    def __init__(self, directory: str):
        self.directory = directory
        self.raw_wd = os.getcwd()
        self.cwd = self.raw_wd
        self.changed = False

    def __enter__(self):
        if not self.directory:
            return self

        if not DirValidator().validate(self.directory):
            run_log.warning(f"target working dir '{self.directory}' is not valid, please check. keep current working"
                            f"directory '{self.raw_wd}' unchanged")
            return self

        try:
            os.chdir(self.directory)
            self.changed = True
            self.cwd = self.directory
            run_log.info(f"changing directory to: {self.directory}")
        except Exception:
            run_log.warning(f"failed to change working dir to : {self.directory}, current working dir is: {self.cwd}")

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.changed:
            os.chdir(self.raw_wd)


class Task:
    def __init__(self, task_index: int, device: Optional[Device], cmd: str, device_num: int):
        self.task_index = task_index
        self.device = device
        self.device_num = device_num
        self.cmd = cmd
        self.training_process: Optional[subprocess.Popen] = None
        self.log_redirect_process: Optional[subprocess.Popen] = None
        self.envs = None
        self.log_file_path = None

    def _get_env_for_current_task(self):
        self.envs = os.environ.copy()
        if self.device is not None:
            self.envs[ASCEND_DEVICE_ID_ENV_KEY] = self.device.device_id
            self.envs[DEVICE_ID_ENV_KEY] = self.device.device_id
            self.envs[RANK_ID_ENV_KEY] = self.device.rank_id
            self.envs[DEVICE_INDEX_ENV_KEY] = self.device.rank_id

    def _add_extra_envs(self, extra_env: Optional[List[str]]):
        """
        add custom environment variables
        Args:
            extra_env: ["ENV_KEY=ENV_VAL", "ENV_KEY=ENV_VAL"]

        Returns:

        """
        if extra_env is None or len(extra_env) == 0:
            return

        for env in extra_env:
            parts = env.split("=", maxsplit=1)
            if len(parts) != 2:
                continue

            env_key, env_val = parts
            if env_key in self.envs:
                continue

            self.envs[env_key] = substitute_arg_with_env(env_val, self.envs)

    def _make_log_file_path(self, log_dir: str, platform: str, cwd: str):
        if log_dir is None:
            return

        if not log_dir or not DirValidator().validate(log_dir):
            log_dir = os.path.join(cwd, DEFAULT_LOG_SUB_DIR)
            run_log.warning(f"log dir not valid, using working dir as default: {log_dir}")

        # cannot get rank info without ranktable, using ip as node identity
        if self.device is None and platform == PlatformType.TensorFlow.value:
            log_dir = os.path.join(log_dir, get_host_ip(use_env=False))

        os.makedirs(log_dir, exist_ok=True)

        if platform == PlatformType.Pytorch.value:
            log_name = f"node_{os.environ[PYTORCH_RANK_ENV_KEY]}.log"
        else:
            index = self.device.rank_id if self.device is not None else self.task_index
            log_name = f"{index}.log"

        self.log_file_path = os.path.join(log_dir, log_name)

    def run(self, log_dir: str, platform: str, enable_stdout: bool, cd_dir: str, extra_env: Optional[List[str]]):
        self._get_env_for_current_task()
        self._add_extra_envs(extra_env)

        with CDContextManager(cd_dir) as cd:
            self.cmd = substitute_arg_with_env(self.cmd, self.envs)
            # os.setsid set process group. SIGTERM that send to parent process, also can be received by all processes
            # in this group.
            self.training_process = subprocess.Popen(self.cmd.split(),
                                                     env=self.envs,
                                                     preexec_fn=os.setsid,
                                                     stdout=subprocess.PIPE,
                                                     stderr=subprocess.STDOUT)

            self._make_log_file_path(log_dir, platform, cd.cwd)
            run_log.info(f"{str(self)}")

            if self.log_file_path is not None:
                self.log_redirect_process = subprocess.Popen(["tee", self.log_file_path],
                                                             stdin=self.training_process.stdout,
                                                             stdout=None if enable_stdout else subprocess.DEVNULL)

    def __repr__(self):
        if self.device is None:
            value = f"training process info: " \
                    f"(log-path->{self.log_file_path}), " \
                    f"(pid->{self.training_process.pid}), " \
                    f"(cmd->{self.cmd}, " \
                    f"(envs->{self.envs})"
        else:
            value = f"training process info: " \
                    f"(log-path->{self.log_file_path}), " \
                    f"(pid->{self.training_process.pid}), " \
                    f"(cmd->{self.cmd}, " \
                    f"(device-id->{self.device.device_id}, " \
                    f"(rank-id->{self.device.rank_id}, " \
                    f"(envs->{self.envs})"
        return value
