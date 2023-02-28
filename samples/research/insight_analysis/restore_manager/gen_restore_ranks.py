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
import json

from restore_manager.restore_resilience_manager import RestoreManager
from util.fault_ranks_manager import FaultRanksDLManager


def serialization_restore_ranks():
    res_manager = RestoreManager()
    fault_ranks = FaultRanksDLManager().get_fault_ranks()
    normal_ranks_json, restore_ranks_json = res_manager.generate_restore_strategy(fault_ranks=fault_ranks)

    restore_strategy_output_file_path = "/job/code/recovery_info.json"

    with open(restore_strategy_output_file_path, "w") as wfile:
        res_dict = {"normal_rank": eval(normal_ranks_json), "abnormal_rank": eval(restore_ranks_json)}
        res_content = str(json.dumps(res_dict))
        wfile.write(f"{res_content}\n")
