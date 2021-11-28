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
from k8s_client.config_map import ConfigMap
from restore_manager.restore_manager import RestoreManager

if __name__ == "__main__":
    res_manager = RestoreManager()
    config_map_handler = ConfigMap()
    fault_ranks = config_map_handler.get_fault_ranks(namespace="vcjob")
    res_manager.generate_restore_strategy(
        strategy_input_file_path="",
        fault_ranks=fault_ranks,
        restore_strategy_output_file_path="/job/code/restore_ranks.sh"
    )


