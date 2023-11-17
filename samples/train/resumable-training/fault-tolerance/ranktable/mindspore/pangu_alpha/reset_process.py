import copy
import os
import argparse
import signal
import time
import logging
import re
import multiprocessing
import subprocess
import psutil

from typing import Optional
from ast import literal_eval
from apscheduler.executors.pool import ProcessPoolExecutor
from apscheduler.schedulers.background import BackgroundScheduler
from pytz import utc
from abc import ABC, abstractmethod

from mindx_elastic.validator.file_process import safe_open
from mindx_elastic.constants import constants
from mindx_elastic.validator.validators import FileValidator, DirectoryValidator

logger = logging.getLogger('recover_logger')
logger.setLevel(logging.INFO)
pattern = re.compile(r'^[a-z0-9]+[a-z0-9\-]*[a-z0-9]+$')
MAX_STR_LEN = 1024


def check_input_file(file_path: Optional[str]) -> bool:
    """
    Validate input file
    """
    validation = DirectoryValidator(file_path, max_len=constants.MAX_FILE_PATH_LENGTH) \
        .check_is_not_none() \
        .check_dir_name() \
        .path_should_exist(is_file=True, msg="Cannot find the file.") \
        .should_not_contains_sensitive_words() \
        .with_blacklist() \
        .check()

    if not validation.is_valid():
        logger.error("File is invalid")
        return False

    if not FileValidator(file_path).check_file_size().check().is_valid():
        logger.error("File size exceeds limited size.")
        return False
    return True


def get_file_info(file_path: str) -> dict:
    with safe_open(file_path, mode="r", encoding='utf-8') as fault_config_out:
        try:
            file_content = literal_eval(fault_config_out.read(constants.MAX_SIZE))
        except Exception as e:
            logger.error(f"an unexpected exception {e} happen when get {file_path}")
            file_content = dict()
        return file_content


class BaseProcessManager(ABC):
    def __init__(self, pids: list):
        super().__init__()
        self._restart = False
        self.pids = copy.deepcopy(pids)
        self._pid_dict = dict()
        self._env_dict = dict()
        self._cmd_dict = dict()

    @abstractmethod
    def kill_fault_process(self, abnormal_rank_list: Optional[list]):
        """
        Kill fault process
        """
        raise NotImplementedError

    @abstractmethod
    def _get_train_process_info(self):
        raise NotImplementedError

    def restore_train_process(self):
        """
        Recover all target processes in this node
        """
        new_pid_list = []
        if not self.all_stopped() or self._restart:
            return new_pid_list

        new_proc_list = []
        for rank in self._cmd_dict:
            command = self._cmd_dict[rank]
            pwd_path = self._env_dict[rank]['PWD']
            env_info = self._env_dict[rank]
            with open(f'{pwd_path}/newlog', 'w') as of:
                proc = subprocess.Popen(command, shell=False, stdout=of, stderr=of,
                                        cwd=pwd_path, env=env_info)
            new_pid_list.append(proc.pid)
            new_proc_list.append(proc)

        self._restart = True
        logger.info(f"new pids are:{new_pid_list}")
        return new_pid_list, new_proc_list

    def all_stopped(self):
        """
        Return true if all target process stopped
        """
        for pid in self.pids:
            process_dir = os.path.join('/proc', str(pid))
            if os.path.exists(process_dir):
                return False
        return True

    def _kill_process(self, rank_list: list, kill_signal):
        """
        Kill processes according to rank list
        """
        for rank in rank_list:
            if rank not in self._pid_dict.keys():
                logger.warning(f"get invalid rank: {rank}")
                continue
            try:
                process_dir = os.path.join('/proc', str(self._pid_dict[rank]))
                if os.path.exists(process_dir):
                    os.kill(self._pid_dict[rank], kill_signal)
            except ProcessLookupError:
                logger.warning(f"{ProcessLookupError} occur when kill the process of {rank}")
            except Exception as e:
                logger.error(f"An unexpected error {e} occur when kill the process of {rank}, "
                             f"please check your setting")
                raise e
        logger.info(f"the signal {kill_signal} has been send to {rank_list}")


class RankProcessManager(BaseProcessManager):
    """
    Get information of process with rank-table and manage it
    """

    def __init__(self, pids: list):
        super().__init__(pids)
        self._get_train_process_info()

    def _get_train_process_info(self):
        """
        Get target process information and save in dict
        """
        if len(self.pids) == 0:
            logger.error("found no process here")
            return

        for train_pid in self.pids:
            train_process = psutil.Process(train_pid)
            uid, _, _ = train_process.uids()
            if uid != os.getuid():
                logger.warning(f"process {train_pid} owner is not valid")
                continue
            process_env = train_process.environ()
            rank_id = process_env['RANK_ID']
            if not rank_id.isdigit():
                logger.warning(f"unexpected RANK_ID: {rank_id} in process {train_pid}, please check you env")
                continue
            rank = int(rank_id)
            self._pid_dict[rank] = train_process.pid
            self._env_dict[rank] = process_env
            self._cmd_dict[rank] = train_process.cmdline()

    def stop_healthy_process(self, normal_rank_list: list):
        """
        Stop healthy process
        """
        self._kill_process(normal_rank_list, signal.SIGTERM)

    def kill_fault_process(self, abnormal_rank_list: Optional[list]):
        """
        Kill fault process
        """
        self._kill_process(abnormal_rank_list, signal.SIGKILL)


class NoRankProcessManager(BaseProcessManager):
    """
    Get information of process without rank-table and manage it
    """

    def __init__(self, pids: list):
        super().__init__(pids)
        self._init_pid = copy.deepcopy(pids)
        self._get_train_process_info()

    def _get_train_process_info(self):
        """
        Get target process information and save in dict
        """
        if len(self._init_pid) == 0:
            logger.error("found no process here")
            return

        time.sleep(5)
        for train_pid in self._init_pid:
            train_process = psutil.Process(train_pid)
            uid, _, _ = train_process.uids()
            if uid != os.getuid():
                logger.warning(f"process {train_pid} owner is not valid")
                continue
            for child_process in train_process.children(recursive=False):
                self.pids.append(child_process.pid)
                self._pid_dict[child_process.pid] = child_process.pid
            self._env_dict[train_pid] = train_process.environ()
            self._cmd_dict[train_pid] = train_process.cmdline()
            self._pid_dict[train_pid] = train_pid

        logger.info(f"get main pid and sub pids are {self.pids}")

    def kill_fault_process(self, abnormal_rank_list: Optional[list]):
        """
        Kill fault process
        """
        self._kill_process(self.pids, signal.SIGKILL)


class ResetWorker:
    def __init__(self, kill_time=50, mode="common", framework="mindspore", pids=None, with_rank=False):
        super().__init__()
        if pids is None:
            pids = []
        self.begin_time = 0
        self.now_time = 0
        self.kill_time = kill_time
        self.recover_mode = mode
        self.train_framework = framework
        self.reset_flag = False
        self.killed_abnormal = False
        self.killed_normal = False
        self.stopped_normal = False
        self.with_rank = with_rank
        self.reset_cm_path = "/user/restore/reset/config/reset.json"
        self.rank_table_path = "/user/serverid/devindex/config/hccl.json"
        self.fault_rank_list = []
        self.recover_rank_list = []
        self.init_pids = pids
        self.new_proc = []
        if self.with_rank:
            self._local_rank = self._init_local_ranks(self.rank_table_path)
        else:
            self._local_rank = []

        self.executors = {
            'default': {'type': 'threadpool',
                        'max_workers': 1},
            'processpool': ProcessPoolExecutor(max_workers=1)
        }
        self.job_defaults = {
            'coalesce': False,
            'max_instances': 1,
        }
        self._sched = BackgroundScheduler(executors=self.executors,
                                          job_defaults=self.job_defaults,
                                          timezone=utc)
        self._process_manager = self._init_process_manager(self.init_pids)

    def _init_process_manager(self, pids):
        if self.with_rank:
            return RankProcessManager(pids)
        return NoRankProcessManager(pids)

    @staticmethod
    def _init_local_ranks(rank_table_path: str) -> list:
        if not check_input_file(rank_table_path):
            logger.error("invalid file path")
            return []
        local_rank_list = []
        server_list_key = "server_list"
        server_id_key = "server_id"
        device_key = "device"
        rank_id_key = "rank_id"
        rank_table_content = get_file_info(rank_table_path)
        if not isinstance(rank_table_content, dict):  # optimize check method
            logger.error("get unexpected file content")
            return []
        if server_list_key not in rank_table_content.keys():
            logger.error(f"found no {server_list_key} in file")
            return []
        if not isinstance(rank_table_content[server_list_key], list):
            logger.error("get unexpected file content of server_list")
            return []

        for server_info in rank_table_content[server_list_key]:
            if device_key not in server_info.keys():
                logger.error(f"found no {device_key} in file")
                return []
            if server_id_key not in server_info.keys():
                logger.error(f"found no {server_id_key} in file")
                return []
            local_ip = os.getenv("XDL_IP")
            if len(local_ip) == 0:
                logger.error("cannot get XDL_IP from env")
                return []
            if server_info[server_id_key] != local_ip:
                continue
            devices_list = server_info[device_key]
            for deivce in devices_list:
                local_rank_list.append(int(deivce[rank_id_key]))

        return local_rank_list

    def _get_ranks_from_cm(self, ranks_path: str, key: str) -> list:
        fault_key = "RankList"
        if not check_input_file(ranks_path):
            logger.error("invalid file path")
            return []
        file_content = get_file_info(ranks_path)
        if not isinstance(file_content, dict):
            logger.error("get unexpected file content")
            return []
        if fault_key not in file_content.keys():
            return []
        rank_list = []
        for rank_info in file_content[fault_key]:
            rank_id = int(rank_info["RankId"])
            if rank_info["Status"] == key and rank_id not in rank_list:
                rank_list.append(rank_id)

        return rank_list

    def exit_recover_process(self):
        logger.error("reset process exit abnormally")
        exit(1)

    def check_all_alive(self):
        for proc in self.new_proc:
            if proc.poll() is None:
                continue
            if proc.poll() == 0:
                os.kill(os.getpid(), signal.SIGTERM)
                return

        killed_by_process = self.killed_abnormal or self.killed_normal or self.stopped_normal
        if self._process_manager.all_stopped() and not killed_by_process:
            os.kill(os.getpid(), signal.SIGUSR2)

    def _kill_abnormal_process(self, abnormal_rank_list: list):
        if self.killed_abnormal:
            return
        try:
            logger.info(f"to kill abnormal rank {abnormal_rank_list}")
            self._process_manager.kill_fault_process(abnormal_rank_list)
            self.killed_abnormal = True
        except Exception as e:
            logger.error(f"an unexpected error {e} occur when kill abnormal process")
            self.exit_recover_process()

    def _stop_normal_process(self, normal_rank_list: list):
        if self.stopped_normal:
            return
        try:
            logger.info(f"to stop normal rank {normal_rank_list}")
            self._process_manager.stop_healthy_process(normal_rank_list)
            self.begin_time = time.time()
            self.stopped_normal = True
        except Exception as e:
            logger.error(f"an unexpected error {e} occur when stop normal process")
            self.exit_recover_process()

    def _kill_normal_process(self, normal_rank_list: list):
        if self.killed_normal:
            return
        try:
            logger.info(f"to kill normal rank {normal_rank_list}")
            self._process_manager.kill_fault_process(normal_rank_list)
            self.killed_normal = True
        except Exception as e:
            logger.error(f"an unexpected error {e} occur when kill normal process")
            self.exit_recover_process()

    def _restore_train_start(self):
        new_pids = []
        try:
            new_pids, self.new_proc = self._process_manager.restore_train_process()
        except Exception as e:
            logger.error(f"an unexpected error {e} occur when recover process")
            self.exit_recover_process()

        self._reset_all_status(new_pids)

    def _is_cur_node(self) -> bool:
        for rank in self.fault_rank_list:
            if rank not in self._local_rank:
                logger.info("fault not on cur node")
                return False
        logger.info("fault on cur node")
        return True

    def _is_stopped(self):
        return self._process_manager.all_stopped()

    def _is_recover(self) -> bool:
        if set(self.fault_rank_list) == set(self.recover_rank_list):
            logger.info("chip has recoverd")
            return True
        return False

    def _is_no_fault_happen(self):
        return len(self.fault_rank_list) == 0

    def _reset_all_status(self, new_pids):
        if len(new_pids) != len(self.init_pids):
            logger.error("recover error")
            self.exit_recover_process()

        self.killed_abnormal = False
        self.killed_normal = False
        self.stopped_normal = False
        self.resart_flag = False
        self._process_manager = self._init_process_manager(new_pids)
        self.fault_rank_list = []
        self.recover_rank_list = []

    def get_fault_ranks(self):
        fault_rank_list = self._get_ranks_from_cm(self.reset_cm_path, "unrecovered")
        if len(fault_rank_list) != 0:
            self.fault_rank_list = fault_rank_list
        return fault_rank_list

    def get_recover_ranks(self):
        recover_rank_list = self._get_ranks_from_cm(self.reset_cm_path, "recovered")
        if len(recover_rank_list) != 0:
            self.recover_rank_list = recover_rank_list
        return recover_rank_list

    def common_recover_process(self):
        logger.info("to recover task in common way")
        self._kill_abnormal_process(self._local_rank)

        if self._is_stopped() and self._is_recover():
            self._restore_train_start()

    def elastic_recover_process(self):
        logger.info("to recover task with elastic")
        if self._is_cur_node():
            normal_rank_list = list(set(self._local_rank) - set(self.fault_rank_list))
            self._stop_normal_process(self._local_rank)
            time.sleep(10)
            self._kill_abnormal_process(self.fault_rank_list)
            self.now_time = int(time.time())
            if self.now_time - self.begin_time < self.kill_time:
                return
            self._kill_normal_process(normal_rank_list)
        else:
            self._stop_normal_process(self._local_rank)
            self.now_time = int(time.time())
            if self.now_time - self.begin_time < self.kill_time:
                return
            self._kill_normal_process(self._local_rank)

        if self._is_stopped() and self._is_recover():
            logger.info("start to recover all process ")
            self._restore_train_start()

    def reset_npu_process(self):
        logger.info("new loop start")
        self.check_all_alive()
        fault_rank_list = self.get_fault_ranks()
        if len(fault_rank_list) != 0:
            logger.info(f"fault rank list is {fault_rank_list}")
        recover_rank_list = self.get_recover_ranks()
        if len(recover_rank_list) != 0:
            logger.info(f"recover rank list is {recover_rank_list}")
        if self._is_no_fault_happen():
            return
        logger.info(f"start to process fault")
        if self.recover_mode == 'common':
            self.common_recover_process()
        else:
            self.elastic_recover_process()

    def start(self):
        self._sched.add_job(self.reset_npu_process, "interval", seconds=5)
        self._sched.start()


def is_valid_input_param(args) -> bool:
    if args.time > 3000 or args.time < 0:
        return False
    if args.mode != 'common' and args.mode != 'elastic':
        return False
    valid_frameworks = ['ms', 'mindspore', 'tf', 'tensorflow', 'pt', 'pytorch']
    if args.frame not in valid_frameworks:
        return False
    return True


def success_shut_down(signum, frame):
    logger.info(f"receive {signum} signal of {frame}, training finished successfully!")
    exit(0)


def err_shut_down(signum, frame):
    logger.info(f"receive {signum} signal of {frame}, training may failed, exit")
    exit(1)


def register_singal():
    signal.signal(signal.SIGTERM, success_shut_down)
    signal.signal(signal.SIGUSR2, err_shut_down)
    logger.info("register signal sucess")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Setting of reset_process')
    parser.add_argument('-t', '--time', dest='time', type=int, help="Time to save elastic ckpt, it doesn't work when "
                                                                    "set mode as common (default=50)", default=50)
    parser.add_argument('-m', '--mode', dest='mode', type=str, help='Mode of recover process'
                                                                    '(default=common)', default='common')
    parser.add_argument('-f', '--frame', dest='frame', type=str, help='Training framework (default=ms,mindspore), '
                                                                      'just support mindspore now', default='ms')
    parser.add_argument('-r', '--with_rank', action='store_true', help='set this param if run with rank-table')
    parser.add_argument('-p', '--pids', dest='pids', type=int, nargs='+', help='the pids of training process which '
                                                                               'monitored by reset_process', default=-1)

    args = parser.parse_args()
    logger.info("reset process begin!")
    logger.info(f"running param {args.time}, {args.mode}, {args.frame}")
    if not is_valid_input_param(args):
        logger.error('get unexpected input')
        exit(1)

    host_name = os.getenv("HOSTNAME")
    if len(host_name) > MAX_STR_LEN:
        logger.error('HOSTNAME is too long')
        exit(1)
    if not pattern.match(host_name):
        logger.error('HOSTNAME is invalid')
        exit(1)
    file_name = f"recover-{host_name}.log"
    file_handler = logging.FileHandler(os.path.join(os.getcwd(), file_name))
    print("log of reset process will be saved in:", file_handler.baseFilename)

    LOG_FORMAT = '%(asctime)s - %(pathname)s[line:%(lineno)d] - [%(levelname)s]: %(message)s'
    formatter = logging.Formatter(LOG_FORMAT)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.info(f"get pid {args.pids}")
    register_singal()

    reset_worker = ResetWorker(kill_time=args.time, mode=args.mode, framework=args.frame,
                               pids=args.pids, with_rank=args.with_rank)
    reset_worker.start()
    while True:
        time.sleep(5)
