# 监视configmap
from __future__ import print_function

import os

from kubernetes import client, config
from kubernetes.client.rest import ApiException

INCLUSTER_FLAG = os.getenv("INCLUSTER_FLAG")
if INCLUSTER_FLAG=="True":
    config.load_incluster_config()
else:
    config.load_kube_config()

client_core_api = client.CoreV1Api()

class BaseResource:
# 获取configmap内容
    def __init__(self):
        super().__init__()
        self._cls_name = self.__class__.__name__
        self.func_get_list = None
        self.init_method()

    def init_method(self):
        raise NotImplementedError

    def get_resource_list(self, namespace, **kwargs):
        """
        获取资源列表
        """
        res_list = []
        verbose = kwargs.get("verbose", False)
        try:
            res_list = self.func_get_list(namespace).items
            res_list = [item.to_dict() for item in res_list]

            if not verbose:
                res_list = [r["metadata"].get("name") for r in res_list]
        except (KeyError, ApiException):
            return False, res_list
        else:
            return True, res_list


