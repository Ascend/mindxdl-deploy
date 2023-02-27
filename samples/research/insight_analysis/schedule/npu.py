# _*_ coding:utf-8 _*_
# Copyright 2023 Huawei Technologies Co., Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ============================================================================
from ctypes import *
import json
import os

from constants.constants import RANK_TABLE_FILE


class NPUHealthCheck:
    """
    Auto Check NPU card health
    """
    def __init__(self):
        self.dsmi_handle = cdll.LoadLibrary('libdrvdsmi_host.so')

        self.p_device_count = pointer(c_int())
        self.p_health = pointer(c_int())

    def get_device_count(self):
        """
        get device count on server
        """
        self.dsmi_handle.dsmi_get_device_count(self.p_device_count)
        device_count = self.p_device_count.contents.value
        return device_count

    def read_from_file(self, file_path):
        with open(file_path) as json_file:
            return json.load(json_file)

    def get_device_rank_map(self, device_id):
        RANK_TABLE_FILE_DEFAULT_VALUE = RANK_TABLE_FILE
        rank_table_file_content = self.read_from_file(
            RANK_TABLE_FILE_DEFAULT_VALUE)
        rank_table_file_status = rank_table_file_content.get("status")
        if "completed" != rank_table_file_status:
            print("rank table file status is not completed")
            return

        server_list = rank_table_file_content.get("server_list")
        for server in server_list:
            if server.get("server_id") == os.getenv("XDL_IP"):
                devices = server.get("device")
                for device in devices:
                    if int(device.get("device_id")) == device_id:
                        return int(device.get("rank_id"))
        return None

    def get_fault_ranks(self):
        fault_ranks = set()
        device_count = self.get_device_count()
        for device_id in range(device_count):
            self.dsmi_handle.dsmi_get_device_health(device_id, self.p_health)
            health = self.p_health.contents.value
            if health != 0 and health != 1:
                rank_id = self.get_device_rank_map(device_id)
                if rank_id:
                    fault_ranks.add(rank_id)
        return fault_ranks