import os

from k8s_client.base import client_core_api, BaseResource


class ConfigMap(BaseResource):
    """
    The k8s config map class.
    It is called to get data in config map.
    """
    def init_method(self):
        self.func_get_list = client_core_api.list_namespaced_config_map()
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
                res_config_map_fault_ranks = \
                res.get("data").get("fault-npus").get("FaultRankIds")
                fault_ranks += res_config_map_fault_ranks

        if len(res_list) > 1:
            return False, None

        return True, fault_ranks
