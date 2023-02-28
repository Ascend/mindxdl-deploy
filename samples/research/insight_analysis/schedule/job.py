# _*_ coding:utf-8 _*_
# Copyright 2022-2023 Huawei Technologies Co., Ltd
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
from schedule.npu import NPUHealthCheck


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
        self.fault_ranks = set()
        self.node_ranks = self._get_node_ranks()
        self.rank_index = self._get_rank_index()
        self.job_replicas = self._get_job_replicas()

    @staticmethod
    def _get_all_task_pids():
        process_info = [p.info for p in psutil.process_iter(attrs=['pid', 'name', 'cmdline']) if 'python' in
                        p.info['name']]

        target_pid = []
        for process in process_info:
            cmd_lines = process.get("cmdline")
            for cmd_line in cmd_lines:
                if "resnet" in cmd_line and "engine" not in cmd_line and process.get("pid") not in target_pid:
                    target_pid.append(process.get("pid"))
        return target_pid

    @staticmethod
    def _get_device_os_ids(ranks):
        reset_devices = set(int(rank) // 4 for rank in ranks)
        print(f"reset device os {reset_devices}")
        device_os_ids = set()
        for device_os_id in reset_devices:
            if device_os_id == 1:
                device_id = 7
            else:
                device_id = 3
            device_os_ids.add(device_id)
        return device_os_ids

    @staticmethod
    def _check_exception_train_start(s):
        if "exception" in s.decode("utf-8"):
            return True
        return False

    @staticmethod
    def get_extend_fault_ranks(fault_ranks):
        fault_device_os_list = set()
        for rank in fault_ranks:
            fault_device_os = rank // 4
            fault_device_os_list.add(fault_device_os)
        print(f"fault device os list {fault_device_os_list}")
        fault_extend_ranks = set()
        for fault_device_os in fault_device_os_list:
            print(f"fault device os {fault_device_os}")
            for rank_id in range(fault_device_os * 4, (fault_device_os + 1) * 4):
                print(f"rank {rank_id}")
                fault_extend_ranks.add(rank_id)
        return fault_extend_ranks

    @staticmethod
    def _get_node_ranks():
        node_ranks = set()
        with open(RANK_TABLE_FILE, "r", encoding='utf-8') as hccl_out:
            rank_table_content = json.load(hccl_out)
            server_list = rank_table_content.get("server_list")
            if not server_list:
                return node_ranks
            for server in server_list:
                if server.get("server_id") == os.getenv("XDL_IP"):
                    device_list = server.get("device")
                    for device in device_list:
                        node_ranks.add(int(device.get("rank_id")))
        return node_ranks

    @staticmethod
    def _get_job_replicas():
        with open(RANK_TABLE_FILE, "r", encoding='utf-8') as hccl_out:
            rank_table_content = json.load(hccl_out)
            server_list = rank_table_content.get("server_list")
            return len(server_list) if server_list else 0

    @staticmethod
    def _get_clear_ecc_cmd(device_id):
        clear_ecc_cmd = f"npu-smi clear -t ecc-info -i {device_id} -c 0"
        return clear_ecc_cmd

    @staticmethod
    def _get_reset_npu_cmd(device_os_id):
        reset_npu_cmd = f"npu-smi set -t reset -i {device_os_id} -c 0"
        return reset_npu_cmd

    @staticmethod
    def _add_success_flag_in_file(flag):
        fault_npu_file_path = os.path.join(constants.FAULT_RANK_CONFIG, constants.FAULT_NPU_FILE)
        print(f"fault_npu_file_path={fault_npu_file_path}")
        with open(fault_npu_file_path, "r", encoding='utf-8') as fault_config_out:
            load_dict = json.load(fault_config_out)
            load_dict["resetSuccess"] = flag

        with open(fault_npu_file_path, 'w') as f:
            json.dump(load_dict, f)
        print("add flag success")

    @staticmethod
    def _execute_input_str(input_str):
        p = subprocess.run(input_str, shell=False)
        result = p.stdout
        return result

    def apl_tool_dos_get_result(self, commands=''):
        try:
            result = self._execute_input_str(commands)
        except Exception as error:
            result = str(error)
        return result

    def check_node_rank(self, fault_ranks):
        for rank in self.node_ranks:
            if rank in fault_ranks:
                return False
        return True

    def create_process_job(self):
        self._sched.add_job(self._fault_rank_hot_reset_v3, "interval",
                            seconds=5)

    def create_job(self):
        pass

    def _kill_fault_ranks_process(self):
        print("run into kill fault ranks process")
        fault_ranks = FaultRanksDLManager().get_fault_ranks()

        print("-------------npu mode: ", os.getenv("mode"))
        if not os.getenv("mode") == "SMP":
            return
        print("-------------fault_ranks: ", fault_ranks)
        print("-------------self.kill_fault_npu_process_flag", self.kill_fault_npu_process_flag)

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

    def _reset_npu(self):
        if self.reset_npu or self.reset_status == "running" or self.reset_status == "completed":
            print(f"reset_npu_flag={self.reset_npu}, reset_status={self.reset_status}", flush=True)
            return

        fault_ranks = FaultRanksDLManager().get_fault_ranks()
        clear_ecc_devices = self.get_extend_fault_ranks(fault_ranks)

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

    def _fault_rank_hot_reset(self):
        fault_ranks = FaultRanksDLManager().get_fault_ranks()
        fault_ranks_list = fault_ranks.split(",")
        print(f"fault ranks list {fault_ranks_list}")
        if len(fault_ranks_list) != 0 and len(fault_ranks_list) % 8 == 0:
            print("is eight or not")
            time.sleep(120)
            self._node_fault_rank_process(fault_ranks_list)
        else:
            self._kill_fault_ranks_process()
            print("look at the health of card", flush=True)
            self._reset_npu()
            fault_ranks = FaultRanksDLManager().get_fault_ranks()
            print(f"fault ranks to check {fault_ranks}")
            if fault_ranks and len(fault_ranks) >= 1:
                self.dsmi_handle.dsmi_get_device_health(7, self.p_health)
                print(f"health status of card {self.p_health.contents.value}", flush=True)
                if self.p_health.contents.value == 0:
                    self.reset_npu = True
                    self.reset_status = "completed"
                    print("it is time for stop process", flush=True)
                    time.sleep(40)
                    self._send_stop_process_signal()
                    self._send_start_process_job()

    def _fault_rank_hot_reset_v2(self):
        fault_ranks = FaultRanksDLManager().get_fault_ranks()
        print(f"fault ranks: {fault_ranks}", flush=True)

        if not fault_ranks:
            if self.restart_process_flag:
                self.fault_ranks = fault_ranks
                self.restart_process_flag = False
            self.stop_process_flag = False
            self.kill_fault_npu_process_flag = False
            self.reset_npu = False
            self.reset_status = "init"
            print("fault ranks is empty, skip hot reset")
            return

        fault_ranks_list = fault_ranks.split(",")
        if len(fault_ranks_list) % 8 == 0:
            print("node fault occur")
            time.sleep(120)
            self._node_fault_rank_process(fault_ranks_list)
            return

        print("chip fault occur")
        if not os.getenv("mode") == "SMP":
            print("npu work mode is not 'SMP', skip hot reset")
            return

        fault_extend_ranks = self.get_extend_fault_ranks(fault_ranks_list)
        print(f"fault extend ranks {fault_extend_ranks}")

        self._kill_fault_ranks_process_v2(fault_extend_ranks)

        fault_device_os_ids = self._get_device_os_ids(fault_extend_ranks)
        print(f"device id for reset {fault_device_os_ids}")

        self._reset_npu_v2(fault_device_os_ids)

        self._check_card_status(fault_device_os_ids)

    def _fault_rank_hot_reset_v3(self):
        self.node_ranks = self._get_node_ranks()
        self.rank_index = self._get_rank_index()
        self.job_replicas = self._get_job_replicas()
        print(f"node ranks: {self.node_ranks}")
        print(f"rank index: {self.rank_index}")
        print(f"job replicas: {self.job_replicas}")

        fault_ranks = FaultRanksDLManager().get_fault_ranks()
        print(f"fault ranks from fault configmap: {fault_ranks}", flush=True)
        if fault_ranks:
            fault_ranks = set(map(int, fault_ranks.split(",")))
            fault_ranks_map = dict()
            for rank in fault_ranks:
                rank_index = rank // 8
                if rank_index not in fault_ranks_map:
                    fault_ranks_map[rank_index] = []
                fault_ranks_map.get(rank_index).append(rank)

            if len(fault_ranks_map) == self.job_replicas:
                return

            fault_node_rank = set()
            for index, ranks in fault_ranks_map.items():
                if len(ranks) % 8 != 0:
                    print(f"存在不可恢复的芯片故障， rank_index: {index}，开始重调度")
                    return
                fault_node_rank.add(index)
            print("node fault occur")
            time.sleep(120)
            for index in fault_node_rank:
                if self.node_ranks == index:
                    return
                fault_ranks = NPUHealthCheck().get_fault_ranks()
                if fault_ranks:
                    print("fault node contain fault chip")
                    return
                self._node_fault_rank_process()

            return

        fault_ranks = NPUHealthCheck().get_fault_ranks()
        print(f"fault ranks from dsmi interface: {fault_ranks}", flush=True)

        if not fault_ranks and self.restart_process_flag:
            self.fault_ranks = fault_ranks
            self.restart_process_flag = False
            self.stop_process_flag = False
            self.kill_fault_npu_process_flag = False
            self.reset_npu = False
            self.reset_status = "init"
            print("fault ranks is empty, skip hot reset")
            return

        for fault_rank in fault_ranks:
            if fault_rank in self.node_ranks:
                self.fault_ranks.add(fault_rank)

        print(f"node fault ranks: {self.fault_ranks}")
        return

        if not self.fault_ranks:
            print("fault ranks is empty, skip hot reset")
            return

        print("chip fault occur")
        if not os.getenv("mode") == "SMP":
            print("npu work mode is not 'SMP', skip hot reset")
            return

        fault_extend_ranks = self.get_extend_fault_ranks(self.fault_ranks)
        print(f"fault extend ranks {fault_extend_ranks}")
        fault_device_os_ids = self._get_device_os_ids(fault_extend_ranks)
        print(f"device id for reset {fault_device_os_ids}")
        if len(fault_device_os_ids) != 1:
            return

        fault_device_os_id = list(fault_device_os_ids)[0]
        normal_ranks = self.node_ranks - fault_extend_ranks

        self._kill_fault_ranks_process_v2(fault_extend_ranks)

        self._reset_npu_v2(fault_device_os_id)

        if self._check_card_status(fault_device_os_id):
            print("it is time for stop process", flush=True)
            time.sleep(40)
            self._send_stop_process_signal_v2(normal_ranks)
            self._send_start_process_job_v2()

    def _check_card_status(self, device_os_id):
        print("start check card status", flush=True)
        self.dsmi_handle.dsmi_get_device_health(device_os_id, self.p_health)
        print(f"device: {device_os_id}，health code: {self.p_health.contents.value}")
        if self.p_health.contents.value == 0:
            self.reset_npu = True
            self.reset_status = "completed"
            return True
        return False

    def _kill_fault_ranks_process_v2(self, fault_extend_ranks):
        if self.kill_fault_npu_process_flag:
            print("killing fault npu process")
            return

        need_kill_pids = self._get_need_kill_pids_v2(fault_extend_ranks)

        print(f"need kill pids {need_kill_pids}")
        if not need_kill_pids:
            return

        for pid in need_kill_pids:
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        self.kill_fault_npu_process_flag = True

    def _reset_npu_v2(self, device_os_id):
        if self.reset_npu or self.reset_status == "running" or self.reset_status == "completed":
            print(f"reset_npu_flag={self.reset_npu}, reset_status={self.reset_status}", flush=True)
            return

        time.sleep(20)
        self.reset_status = "running"
        print(f"start reset card: {device_os_id}")
        res_reset = self.dsmi_handle.dsmi_hot_reset_soc_v2(device_os_id, 0)
        print(f"reset npu result {res_reset}, type is {type(res_reset)}", flush=True)

    def _get_need_kill_pids(self, fault_extend_ranks):
        all_task_pids = self._get_all_task_pids()
        if not all_task_pids:
            print("task pid is empty")
            return None
        need_kill_pids = []
        if len(all_task_pids) == 2:
            fault_rank_id = fault_extend_ranks[0]
            if fault_rank_id >= 4:
                need_kill_pids.append(all_task_pids[0])
            else:
                need_kill_pids.append(all_task_pids[-1])
            return need_kill_pids

        for fault_rank_id in fault_extend_ranks:
            print(f"fault ranks {fault_rank_id}")
            content = all_task_pids[len(all_task_pids) - int(fault_rank_id) - 1]
            print(f"content {content}")
            need_kill_pids.append(content)
        return need_kill_pids

    def _get_need_kill_pids_v2(self, rank_ids):
        all_task_pids = self._get_all_task_pids()
        if not all_task_pids:
            print("task pid is empty")
            return None
        need_kill_pids = set()
        for pid in all_task_pids:
            p = psutil.Process(pid)
            if int(p.environ().get("RANK_ID")) in rank_ids:
                need_kill_pids.add(pid)
        return need_kill_pids

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
                    if "resnet" in cmd_line and "engine.py" not in cmd_line and process.get("pid") not in target_pid:
                        target_pid.append(process.get("pid"))

            print(f"target pid {list(set(target_pid))}")
            for pid in list(set(target_pid)):
                try:
                    os.kill(pid, signal.SIGUSR2)
                except ProcessLookupError:
                    print(f"ProcessLookupError pid={pid}")
                    pass
            self.stop_process_flag = True

    def _send_stop_process_signal_v2(self, ranks):
        if self.stop_process_flag:
            return
        print("run into stop process")
        # stop all process
        all_task_pids = self._get_all_task_pids()
        if not all_task_pids:
            print("task pid is empty")
            return
        target_pid = []
        for pid in all_task_pids:
            p = psutil.Process(pid)
            if int(p.environ().get("RANK_ID")) in ranks:
                target_pid.append(pid)

        print(f"target pid {target_pid}")
        for pid in target_pid:
            try:
                os.kill(pid, signal.SIGUSR2)
            except ProcessLookupError:
                print(f"ProcessLookupError pid={pid}")
                pass
        self.stop_process_flag = True

    def _send_start_process_job(self):
        print("run into start process")
        restore_ranks = FaultRanksDLManager().get_restore_ranks()
        print(f"restore ranks {restore_ranks}")
        if restore_ranks and len(restore_ranks) >= 1 and self.old_restore_ranks != restore_ranks and \
                not self.restart_process_flag:
            self.old_restore_ranks = restore_ranks
            command = "cd /job/code/resnet_bak/scripts; bash train_start_hot.sh"
            print(f"command：{command}")
            if command == "":
                return
            result = self.apl_tool_dos_get_result(command)

            print(f"execute {command} result: {result}", flush=True)
            self.restart_process_flag = True

    def _send_start_process_job_v2(self):
        if self.restart_process_flag:
            print("restarting process...")
            return
        fault_ranks_str = ",".join(map(str, self.fault_ranks))
        os.putenv("FAULT_RANKS", fault_ranks_str)
        print(f"put env FAULT_RANKS={fault_ranks_str}")

        command = "cd /job/code/resnet_bak/scripts; bash train_start_hot.sh"
        print(f"command: {command}")
        result = self.apl_tool_dos_get_result(command)
        print(f"execute {command} result: {result}", flush=True)

        self.restart_process_flag = True

    def _get_rank_index(self):
        if not self.node_ranks:
            return -1
        for rank in self.node_ranks:
            return rank // 8

    def _node_fault_rank_process(self):
        print("run into check node rank", flush=True)
        print(f"stop process flag: {self.stop_process_flag}")
        if not self.stop_process_flag:
            print("is divided by eight or not")
            target_pid = self._get_all_task_pids()
            print(f"target pid {list(set(target_pid))}", flush=True)
            for pid in list(set(target_pid)):
                try:
                    os.kill(pid, signal.SIGUSR2)
                except ProcessLookupError:
                    print(f"kill process<{pid}> failed")
                    pass

            self.stop_process_flag = True




class ProcessJob(ScheduleJob):
    def __init__(self, scheduler):
        super(ProcessJob, self).__init__(scheduler)

    def create_job(self):
        self.create_process_job()
        super(ProcessJob, self).create_job()
