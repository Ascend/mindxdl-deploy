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
import os
import datetime

from k8s_client.base import client_core_api, BaseResource


class ConfigMap(BaseResource):
    """
    The k8s config map class.
    It is called to get data in config map.
    """

    def init_method(self):
        self.func_get_list = client_core_api.list_namespaced_config_map
        # TODO: namespace configurable
        self.configmap_namespace = "vcjob"

    def get_fault_ranks(self,
                        namespace,
                        job_id=None,
                        verbose=True):
        """
        Get fault ranks in training job when exception happens.
        :param namespace: training job namespace
        :param job_id: training job id
        :param verbose: whether verbose
        :return: fault ranks string
        """
        if not namespace:
            namespace = self.configmap_namespace

        ret, res_list = super().get_resource_list(namespace, verbose=verbose)

        if not ret:
            return False, None

        if not job_id:
            job_id = os.getenv("mindx-dls-test")

        fault_ranks = ""
        for res in res_list:
            config_map_name = res["metadata"].get("name")
            parts = config_map_name.split("fault-config-")
            if len(parts) < 2:
                continue

            filter_config_map_name = parts[-1]
            if filter_config_map_name in job_id:
                if res.get("data").get("fault-npus"):
                    record_fault_rank_list = eval(res.get("data").get(
                        "fault-npus")).get("FaultRankIds")

                    clear_fault_rank_list = []
                    for ele in eval(record_fault_rank_list):
                        if ele.isdigit() and eval(ele) >= 0 and eval(
                                ele) <= 4095:
                            clear_fault_rank_list.append(ele)

                    res_config_map_fault_ranks = ",".join(clear_fault_rank_list)
                    fault_ranks += res_config_map_fault_ranks

        return True, fault_ranks

    def get_fault_ranks_timestamp(self,
                                  namespace,
                                  job_id=None,
                                  verbose=True):
        """
        Get fault ranks timestamp flag in training job when exception happens.
        :param namespace: training job namespace
        :param job_id: training job id
        :param verbose: whether verbose
        :return: fault ranks string
        """
        if not namespace:
            namespace = self.configmap_namespace

        ret, res_list = super().get_resource_list(namespace, verbose=verbose)

        if not ret:
            return False, None

        if not job_id:
            job_id = os.getenv("mindx-dls-test")

        for res in res_list:
            config_map_name = res["metadata"].get("name")
            parts = config_map_name.split("fault-config-")
            if len(parts) < 2:
                continue
            filter_config_map_name = parts[-1]
            if filter_config_map_name in job_id:
                if not res.get("data").get("fault-npus"):
                    return False

                record_fault_rank_timestamp = eval(res.get("data").get(
                    "fault-npus")).get("CreateTime")
                if not record_fault_rank_timestamp:
                    return False

                dt_early = datetime.datetime.now() - datetime.timedelta(minutes=5)
                if int(dt_early.timestamp()) < record_fault_rank_timestamp:
                    return True

        return False
