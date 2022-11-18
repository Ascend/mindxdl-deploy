import json
import os
import time
from typing import List, Optional

from training_toolkit.logger.log import run_log
from training_toolkit.utils.common import get_host_ip


class RankTable:
    OS_ENV_NAME = "RANK_TABLE_FILE"
    DEFAULT_PATH = "/user/serverid/devindex/config/hccl.json"
    CHECK_INTERVAL = 5
    COMPLETE_STATUS = "completed"
    STATUS_FIELD = "status"
    SERVER_COUNT_FIELD = "server_count"
    SERVER_INFO_FIELD = "server_list"
    SERVER_ID_FIELD = "server_id"
    DEVICE_FIELD = "device"
    DEVICE_ID_FIELD = "device_id"
    DEVICE_IP_FIELD = "device_ip"
    RANK_ID_FIELD = "rank_id"

    def __init__(self):
        self.file_path = self._get_rank_table_path()
        self.content = None

    @staticmethod
    def _get_rank_table_path():
        if RankTable.OS_ENV_NAME in os.environ:
            env_path = os.environ.get(RankTable.OS_ENV_NAME)
            if not os.path.exists(env_path):
                raise ValueError(f"ranktable env is set to {RankTable.OS_ENV_NAME}:{env_path}, but not exist.")
            return env_path

        if not os.path.exists(RankTable.DEFAULT_PATH):
            raise ValueError(f"default rank table file doesn't exist: {RankTable.DEFAULT_PATH}")

        # set rank table env
        os.environ[RankTable.OS_ENV_NAME] = RankTable.DEFAULT_PATH

        return RankTable.DEFAULT_PATH

    def wait_for_complete(self):
        run_log.info("wait for the status of rank table to be ready")
        elapsed_time = 0
        while True:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if RankTable.STATUS_FIELD not in data:
                    msg = f"field: {RankTable.STATUS_FIELD} not in file, please check the format and content"
                    run_log.error(msg)
                    raise ValueError(msg)

                if data[RankTable.STATUS_FIELD] != RankTable.COMPLETE_STATUS:
                    time.sleep(RankTable.CHECK_INTERVAL)
                    elapsed_time += RankTable.CHECK_INTERVAL
                    run_log.info(f"waiting for ranktable to be ready, {elapsed_time} seconds elapsed")
                    continue

                self.content = data
                break

        run_log.info(f"ranktable is ready: \n {json.dumps(self.content, ensure_ascii=False, indent=4)}")

    def get_server_count(self):
        return int(self.content[RankTable.SERVER_COUNT_FIELD])

    def get_total_device_num(self):
        num = 0
        for server_info in self.content[RankTable.SERVER_INFO_FIELD]:
            num += len(server_info[RankTable.DEVICE_FIELD])
        return num

    def get_master_ip(self):
        """
        assign the first server in ranktable file as the master node in training task
        Returns:
        """
        return self.content[RankTable.SERVER_INFO_FIELD][0][RankTable.SERVER_ID_FIELD]

    def get_current_server_info(self) -> Optional['Server']:
        host_ip = get_host_ip()
        if not host_ip:
            return None

        server_index = -1
        server_info = None

        for index, server_info_tmp in enumerate(self.content[RankTable.SERVER_INFO_FIELD]):
            if server_info_tmp[RankTable.SERVER_ID_FIELD] == host_ip:
                server_info = server_info_tmp
                server_index = index
                break

        if server_info is None:
            msg = f"cannot get server info from ranktable for host: {host_ip}, please check"
            run_log.error(msg)
            return None

        server = Server(server_info[RankTable.SERVER_ID_FIELD], server_info[RankTable.DEVICE_FIELD], server_index)
        return server


class Server:
    def __init__(self, server_ip: str, devices: list, server_index: int):
        self.ip = server_ip
        self.devices: List[Device] = self.parse_devices(devices)
        self.server_index = server_index

    @staticmethod
    def parse_devices(devices: list) -> list:
        device_list = []
        for device in devices:
            device_list.append(
                Device(
                    device[RankTable.DEVICE_ID_FIELD],
                    device[RankTable.RANK_ID_FIELD],
                    device[RankTable.DEVICE_IP_FIELD],
                )
            )

        return device_list

    def __len__(self):
        return len(self.devices)

    def __repr__(self):
        return f"Server ip: {self.ip}; Device num: {len(self)}; Device info: {' || '.join(map(str, self.devices))}"


class Device:
    def __init__(self, device_id: str, rank_id: str, device_ip: str):
        self.device_id = device_id
        self.rank_id = rank_id
        self.device_ip = device_ip

    def __repr__(self):
        return f"[ip:{self.device_ip}, rank id:{self.rank_id}, device id: {self.device_id}]"
