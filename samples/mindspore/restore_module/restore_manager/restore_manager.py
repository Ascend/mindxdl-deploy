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
import glob
import json
import os
import warnings

import mindspore.communication.management as D
from mindspore.train.serialization import restore_group_info_list
from mindspore.train.serialization import load_checkpoint, load_param_into_net


class RestoreManager:
    """
    Get configmap resource class
    """
    def __init__(self):
        self.strategy_input_file_path = os.getenv("GROUP_INFO_FILE_REFLECT")
        self.job_id = os.getenv("mindx-dls-test")
        self.restore_strategy_output_file_path = "/job/code/restore_ranks.sh"

    def _expand_fault_ranks(self, fault_ranks_list):
        fault_devices = []

        for rank in fault_ranks_list:
            fault_device = rank // 8
            if fault_device not in fault_devices:
                fault_devices.append(fault_device)

        unusable_ranks = []
        for device in fault_devices:
            unusable_ranks.extend([1 * device + i for i in range(8)])
        return unusable_ranks

    def generate_restore_strategy(self, strategy_input_file_path, fault_ranks,
                                  restore_strategy_output_file_path):
        warnings.simplefilter('ignore', ResourceWarning)
        strategy_name = "group_info.pb"
        if not strategy_input_file_path:
            tmp_strategy_input_file_path = self.strategy_input_file_path
            path, strategy_name = os.path.split(tmp_strategy_input_file_path)
            strategy_input_file_path, _ = os.path.split(path)

        D.init()
        device_num = D.get_group_size()
        print("device_num is {}".format(device_num))

        device_group_info_list = []
        for index in range(device_num):
            sub_strategy_input_file_path = os.path.join(
                strategy_input_file_path, f"device{index}")
            sub_startegy_input_file_name = os.path.join(
                sub_strategy_input_file_path, strategy_name)
            res = restore_group_info_list(sub_startegy_input_file_name)
            if res not in device_group_info_list:
                device_group_info_list.append(res)

        restore_ranks = set()

        # get ranks
        if not fault_ranks:
            restore_ranks = '-1'
            with open(restore_strategy_output_file_path, "w") as wfile:
                wfile.write(f"export RESTORE_RANKS={restore_ranks}\n")
            return restore_ranks

        if "-1" == fault_ranks:
            restore_ranks = '-1'
            with open(restore_strategy_output_file_path, "w") as wfile:
                wfile.write(f"export RESTORE_RANKS={restore_ranks}\n")
            return restore_ranks

        fault_ranks_list = []
        fault_ranks_splits = fault_ranks.split(",")
        for ele in fault_ranks_splits:
            fault_ranks_list.append(int(ele))

        if os.getenv("ENABLE_LOCAL_DISK_EXP_STORE"):
            fault_ranks_list = self._expand_fault_ranks(fault_ranks_list)

        restore_rank_dict = dict()
        for elements in device_group_info_list:
            elements_for_use = set(elements) - set(fault_ranks_list)
            if not elements_for_use:
                restore_ranks.add(-1)
                restore_ranks_list = []
                for idx in restore_ranks:
                    restore_ranks_list.append(str(idx))
                restore_ranks_str = ",".join(restore_ranks_list)
                with open(restore_strategy_output_file_path, "w") as wfile:
                    wfile.write(f"export RESTORE_RANKS={restore_ranks_str}\n")

                return restore_ranks_str

            elements_str = ",".join(map(str, elements))
            restore_rank_dict[elements_str] = list(elements_for_use)[0]
            restore_ranks.add(list(elements_for_use)[0])

        with open(restore_strategy_output_file_path, "w") as wfile:
            restore_ranks_list = []
            for idx in restore_ranks:
                restore_ranks_list.append(str(idx))
            restore_ranks_str = ",".join(restore_ranks_list)
            wfile.write(f"export RESTORE_RANKS={restore_ranks_str}\n")

            restore_ranks_json = json.dumps(restore_rank_dict)
            wfile.write(f"export RESTORE_RANKS_MAP='{str(restore_ranks_json)}'\n")
        return restore_ranks_str

    def load_restore_strategy(self, restore_strategy_output_file_path):
        with open(restore_strategy_output_file_path, "r") as rfile:
            restore_ranks_str = rfile.read()

        restore_ranks_list = list(restore_ranks_str.split(","))
        if -1 in restore_ranks_list:
            os.environ["RESTORE_RANKS"] = ""
            return None

        os.environ["RESTORE_RANKS"] = restore_ranks_list
        return restore_ranks_list

    def get_exception_checkpoints(self, params):
        r"""
        Load checkpoint process.
        """
        print("======start exception checkpoint", flush=True)
        restore_ranks = os.getenv("RESTORE_RANKS")
        if not restore_ranks:
            return

        restore_rank_list = list(
            map(lambda rank: int(rank), restore_ranks.split(",")))
        ckpt_file_list = []
        ckpt_name = params.ckpt_name_prefix
        for ckpt_rank in restore_rank_list:
            ckpt_pattern = os.path.join(params.save_checkpoint_path,
                                        f"rank_{ckpt_rank}",
                                        f"{ckpt_name}*_breakpoint.ckpt")
            ckpt_files = glob.glob(ckpt_pattern)
            if not ckpt_files:
                print(
                    f"There is no ckpt file in {params.save_checkpoint_path}, "
                    f"current ckpt_files found is {ckpt_files} "
                    f"with pattern {ckpt_pattern}, so skip the loading.")
                return
            ckpt_files.sort(key=os.path.getmtime, reverse=True)
            ckpt_file_list.append(ckpt_files[0])
        return ckpt_file_list

    def check_exception_checkpoints(self, ckpt_file_list):
        """
        Checkpoint exception checkpoints size.
        Args:
            ckpt_file_list: exception checkpoints

        Returns: result of exception checkpoints size check.

        """
        ckpt_size_list = []
        for ckpt_file in ckpt_file_list:
            ckpt_size_list.append(os.path.getsize(ckpt_file))

        if len(set(ckpt_size_list)) > 1:
            return False

        return True

    def restore_exception_checkpoint(self, args_param, sink_size, dataset, model, network, epoch):
        """
        Restore exception checkpoint.
        Args:
            args_param: training job params
            sink_size: training job sink size
            dataset: dataset for training
            model: model
            network: pangu_alpha network
            epoch: training epoch

        Returns: load exception checkpoint success or not.

        """
        if os.getenv("RESTORE_RANKS") == "-1":
            return False

        ckpt_file_list = self.get_exception_checkpoints(args_param)

        restore_flag = False
        if ckpt_file_list:
            restore_flag = self.check_exception_checkpoints(ckpt_file_list)

        if not restore_flag:
            return False

        ckpt_name = args_param.ckpt_name_prefix
        restore_ranks_map = os.getenv("RESTORE_RANKS_MAP")
        if not restore_ranks_map:
            return False

        try:
            print("whether run into load process")
            restore_ranks_map_json = json.loads(restore_ranks_map)
            map_rank_id = D.get_rank()
            for key in restore_ranks_map_json.keys():
                if str(D.get_rank()) in key:
                    map_rank_id = restore_ranks_map_json.get(key)

            print(f"loading map rank id {map_rank_id}")
            ckpt_pattern = os.path.join(args_param.save_checkpoint_path,
                                        f"rank_{map_rank_id}",
                                        f"{ckpt_name}*breakpoint.ckpt")
            ckpt_files = glob.glob(ckpt_pattern)
            ckpt_files.sort(key=os.path.getmtime, reverse=True)
            print(f" checkpoint files {ckpt_files[0]}")
            param_dict = load_checkpoint(ckpt_files[0])
            print(f" checkpoint param dict epoch num {param_dict.get('epoch_num')}")
            if param_dict.get("epoch_num") and param_dict.get("step_num"):
                args_param.has_trained_epoches = int(
                    param_dict["epoch_num"].data.asnumpy())
                args_param.has_trained_steps = int(
                    param_dict["step_num"].data.asnumpy())

            # Load checkpoint files
            model.build(train_dataset=dataset, sink_size=sink_size, epoch=epoch)
            load_param_into_net(network, param_dict)
        except TypeError:
            return False
        else:
            return True
