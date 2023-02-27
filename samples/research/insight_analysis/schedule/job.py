# Copyright 2021 Huawei Technologies Co., Ltd
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
import json
import os
import signal
import subprocess
from ctypes import *
import psutil

import time
from constants import constants
from constants.constants import RANK_TABLE_FILE
from util.fault_ranks_manager import FaultRanksDLManager


class ScheduleJob(object):
    '''
    classdocs
    '''

    def __init__(self, scheduler):
        '''
        Constructor
        '''
        self._sched = scheduler.get_apscheduler()
        self.stop_process_flag = False
        self.restart_process_flag = False
        self.kill_fault_npu_process_flag = False
        self.reset_npu = False
        self.dsmi_handle = cdll.LoadLibrary('libdrvdsmi_host.so')
        self.p_device_count = pointer(c_int())
        self.p_health = pointer(c_int())
        self.old_restore_ranks = None
        self.reset_status = "init"

    def create_job(self):
        pass

    def _kill_fault_ranks_process(self):
        print("run into kill fault ranks process")
        fault_ranks = FaultRanksDLManager().get_fault_ranks()

        if not os.getenv("mode") == "SMP":
            return

        if fault_ranks and len(fault_ranks) >= 1 and not self.kill_fault_npu_process_flag:
            print("run into kill -9 fault rank process")
            # stop all process
            process_info = [p.info for p in psutil.process_iter(attrs=['pid', 'name', 'cmdline']) if 'python' in
                            p.info['name']]

            target_pid = []
            for process in process_info:
                cmd_lines = process.get("cmdline")
                for cmd_line in cmd_lines:
                    if "resnet" in cmd_line and "engine" not in cmd_line and process.get("pid") not in target_pid:
                        target_pid.append(process.get("pid"))

            print(f"target pid {target_pid}")
            need_kill_pids = []
            fault_extend_ranks = self.get_extend_fault_ranks(fault_ranks)

            print(f"fault extend ranks {fault_extend_ranks}")

            if len(target_pid) == 2:
                fault_rank_id = fault_extend_ranks[0]
                if fault_rank_id >= 4:
                    need_kill_pids.append(target_pid[0])
                else:
                    need_kill_pids.append(target_pid[-1])
            else:
                for fault_rank_id in fault_extend_ranks:
                    print(f"fault ranks {fault_rank_id}")
                    content = target_pid[len(target_pid) - int(fault_rank_id) - 1]
                    print(f"content {content}")
                    need_kill_pids.append(target_pid[len(target_pid) - int(fault_rank_id) - 1])

            print(f"need kill pids {need_kill_pids}")

            for pid in need_kill_pids:
                try:
                    os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            self.kill_fault_npu_process_flag = True

    def get_extend_fault_ranks(self, fault_ranks):
        fault_device_os_list = []
        for rank in fault_ranks:
            fault_device_os = int(rank) // 4
            if fault_device_os not in fault_device_os_list:
                fault_device_os_list.append(fault_device_os)
        print(f"fault device os list {fault_device_os_list}")
        fault_extend_ranks = []
        for fault_device_os in fault_device_os_list:
            print(f"fault device os {fault_device_os}")
            for rank_id in range(fault_device_os * 4, (fault_device_os + 1) * 4):
                print(f"rank {rank_id}")
                if rank_id not in fault_extend_ranks:
                    fault_extend_ranks.append(rank_id)
        return fault_extend_ranks

    def subprocess_popen(self, cmd, **kwargs):
        kwargs['stdin'] = subprocess.PIPE
        kwargs['stdout'] = subprocess.PIPE
        kwargs['shell'] = True
        kwargs['stderr'] = subprocess.PIPE
        p = subprocess.Popen(cmd, **kwargs)
        result = p.communicate()[0]
        return result

    def apl_tool_dos_get_result(self, commands=''):
        try:
            result = self.subprocess_popen(commands)
        except Exception as error:
            result = str(error)
        return result

    def _get_clear_ecc_cmd(self, device_id):
        clear_ecc_cmd = f"npu-smi clear -t ecc-info -i {device_id} -c 0"
        return clear_ecc_cmd

    def _get_reset_npu_cmd(self, device_os_id):
        reset_npu_cmd = f"npu-smi set -t reset -i {device_os_id} -c 0"
        return reset_npu_cmd

    def _add_success_flag_in_file(self, flag):
        fault_npu_file_path = os.path.join(constants.FAULT_RANK_CONFIG, constants.FAULT_NPU_FILE)
        with open(fault_npu_file_path, "r", encoding='utf-8') as fault_config_out:
            load_dict = json.load(fault_config_out)
            load_dict["resetSuccess"] = flag

        with open(fault_npu_file_path, 'w') as f:
            json.dump(load_dict, f)

    def subprocess_popen_with_interactive(self, cmd, **kwargs):
        kwargs['stdin'] = subprocess.PIPE
        kwargs['stdout'] = subprocess.PIPE
        kwargs['shell'] = True
        kwargs['stderr'] = subprocess.PIPE
        p = subprocess.Popen(cmd, **kwargs)
        p.stdin.write(b'Yes')
        p.stdin.flush()
        result = p.communicate()[0]
        return result

    def check_node_rank(self, fault_ranks):
        with open(RANK_TABLE_FILE, "r", encoding='utf-8') as hccl_out:
            rank_table_content = json.load(hccl_out)
            server_list = rank_table_content.get("server_list")
            for server in server_list:
                if server.get("server_id") == os.getenv("XDL_IP"):
                    device_list = server.get("device")
                    for device in device_list:
                        rank_id = device.get("rank_id")
                        if rank_id in fault_ranks:
                            return False
        return True

    def _reset_npu(self):
        fault_ranks = FaultRanksDLManager().get_fault_ranks()
        clear_ecc_devices = self.get_extend_fault_ranks(fault_ranks)
        if self.reset_npu or self.reset_status == "running" or self.reset_status == "completed":
            return

        print(f"clear ecce devices {clear_ecc_devices}")
        if not clear_ecc_devices or len(clear_ecc_devices) == 0:
            return

        reset_devices = list(set([int(device) // 4 for device in clear_ecc_devices]))
        print(f"reset devices {reset_devices}")
        for device_os_id in reset_devices:
            if device_os_id == 1:
                device_id = 7
            else:
                device_id = 3
            print(f"device id for reset {device_id}")
            time.sleep(20)
            self.reset_status = "running"
            res_reset = self.dsmi_handle.dsmi_hot_reset_soc_v2(device_id, 0)
            print(f"reset npu result {res_reset}, type is {type(res_reset)}", flush=True)
            self.dsmi_handle.dsmi_get_device_health(device_id, self.p_health)
            print(f"health status of card {self.p_health.contents.value}", flush=True)
            if self.p_health.contents.value == 0:
                self.reset_npu = True
                self._add_success_flag_in_file(True)
                self.reset_status = "completed"
                print("it is time for stop process")
                self._send_stop_process_signal()
                self._send_start_process_job()

    def _fault_rank_hot_reset(self):
        fault_ranks = FaultRanksDLManager().get_fault_ranks()
        fault_ranks_list = fault_ranks.split(",")
        if len(fault_ranks_list) != 0 and len(fault_ranks_list) % 8 == 0:
           self._node_fault_rank_process(fault_ranks)
        else:
            self._kill_fault_ranks_process()
            print("look at the health of card", flush=True)
            self._reset_npu()
            fault_ranks = FaultRanksDLManager().get_fault_ranks()

            # generate fault ranks strategy
            print(f"fault ranks to check {fault_ranks}")
            if fault_ranks and len(fault_ranks) >= 1:
                if len(fault_ranks) % 8 != 0:
                    self.dsmi_handle.dsmi_get_device_health(7, self.p_health)
                    print(f"health status of card {self.p_health.contents.value}", flush=True)
                    if self.p_health.contents.value == 0:
                        print("it is time for stop process")
                        time.sleep(40)
                        self._send_stop_process_signal()
                        self._send_start_process_job()

                if len(fault_ranks) % 8 == 0:
                    if self.check_node_rank(fault_ranks):
                        time.sleep(40)
                        self._send_stop_process_signal()

    def _send_stop_process_signal(self):
        print("run into send stop signal")
        fault_ranks = FaultRanksDLManager().get_fault_ranks()
        if fault_ranks and len(fault_ranks) >= 1 and self.stop_process_flag == False:
            print("run into stop process")
            # stop all process
            process_info = [p.info for p in psutil.process_iter(attrs=['pid', 'name', 'cmdline']) if 'python' in
                            p.info['name']]

            target_pid = []
            for process in process_info:
                cmd_lines = process.get("cmdline")
                for cmd_line in cmd_lines:
                    if "resnet" in cmd_line and process.get("pid") not in target_pid:
                        target_pid.append(process.get("pid"))

            print(f"target pid {list(set(target_pid))}")
            for pid in list(set(target_pid)):
                try:
                    os.kill(pid, signal.SIGUSR2)
                except ProcessLookupError:
                    pass

            self.stop_process_flag = True

    def _send_start_process_job(self):
        print("run into start process")
        restore_ranks = FaultRanksDLManager().get_restore_ranks()
        print(f"restore ranks {restore_ranks}")

        if restore_ranks and len(restore_ranks) >= 1 and self.old_restore_ranks != restore_ranks and \
                self.restart_process_flag == False:
            self.old_restore_ranks = restore_ranks
            command = "cd /job/code/scripts; bash train_start_hot.sh"
            result = self.apl_tool_dos_get_result(command)

            print(f"execute {command} result: {result}", flush=True)
            self.restart_process_flag = True

    def _node_fault_rank_process(self, fault_ranks):
        # get fault ranks correspoding server id
        if self.check_node_rank(fault_ranks):
            process_info = [p.info for p in psutil.process_iter(attrs=['pid', 'name', 'cmdline']) if 'python' in
                            p.info['name']]

            target_pid = []
            for process in process_info:
                cmd_lines = process.get("cmdline")
                for cmd_line in cmd_lines:
                    if "resnet" in cmd_line and process.get("pid") not in target_pid:
                        target_pid.append(process.get("pid"))

            print(f"target pid {list(set(target_pid))}")
            for pid in list(set(target_pid)):
                try:
                    os.kill(pid, signal.SIGUSR2)
                except ProcessLookupError:
                    pass

            self.stop_process_flag = True

    def create_process_job(self):
        self._sched.add_job(self._fault_rank_hot_reset, "interval",
                            seconds=5)


class ProcessJob(ScheduleJob):
    def __init__(self, scheduler):
        super(ProcessJob, self).__init__(scheduler)

    def create_job(self):
        self.create_process_job()
        super(ProcessJob, self).create_job()
