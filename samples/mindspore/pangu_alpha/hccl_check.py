# coding: utf-8

# Copyright(C) 2022. Huawei Technologies Co.,Ltd. All rights reserved.
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
import json
import os
import sys


# Add the following methods to the training code (such as train. py),
# and then call the get_restore_strategy() in main function
def hccl_check(need_device_num) -> bool:
    hccl_path = "/user/serverid/devindex/config/hccl.json"
    with open(hccl_path, 'r', encoding='UTF-8') as f:
        data = json.load(f)

    srv_count = data["server_count"]
    srv_list = data["server_list"]
    if srv_count != 1:
        return True
    device_num = len(srv_list[0]["device"])
    if device_num < need_device_num:
        return False
    if device_num % need_device_num == 0:
        return True
    new_device_num = int(device_num / need_device_num) * need_device_num
    srv_list[0]["device"] = srv_list[0]["device"][:new_device_num]
    data["server_list"] = srv_list

    new_hccl_path = os.path.join(os.getcwd(), "hccl.json")
    if os.path.exists(new_hccl_path):
        return True
    with open(new_hccl_path, 'w') as cf:
        json.dump(data, cf, indent=4)
    sys.stdout.flush()
    os.environ["RANK_TABLE_FILE"] = new_hccl_path
    return True


def get_restore_strategy():
    from mindx_elastic.restore_module.restore_manager.restore_resilience_manager import RestoreResilienceManager
    res_manager = RestoreResilienceManager()
    restore_rank_str, _ = res_manager.generate_restore_strategy(fault_ranks="")
    if len(restore_rank_str) == 0:
        # not exist restore strategy file, skip it
        return
    if not hccl_check(len(restore_rank_str.split(','))):
        print("check hccl failed, restore_rank_str {}, exit!".format(restore_rank_str))
        exit(1)
