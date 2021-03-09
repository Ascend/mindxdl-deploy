# coding: utf-8

# Copyright(C) 2020. Huawei Technologies Co.,Ltd. All rights reserved.
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
import sys

HCCL_JSON_FILE_PATH = "/user/serverid/devindex/config/hccl.json"
RANK_ID_INFO_FILE_PATH = "/hccl_config/rank_id_info.txt"


def read_json_content():
    """
    根据hccl.json文件，将json格式数据转换为字典类型
    :return: dict
    """
    try:
        with open(HCCL_JSON_FILE_PATH, "r") as hccl_json_file:
            hccl_json_str = hccl_json_file.read()
    except FileNotFoundError:
        print("File {} not exists!".format(HCCL_JSON_FILE_PATH))
        sys.exit(1)

    if not hccl_json_str:
        print("File {} is empty!".format(HCCL_JSON_FILE_PATH))
        sys.exit(1)

    try:
        hccl_json = json.loads(hccl_json_str)
    except TypeError:
        print("File {} content format is incorrect."
              .format(HCCL_JSON_FILE_PATH))
        sys.exit(1)

    return hccl_json


def create_rank_id_info():
    """
    解析转换为字典后的json数据，获取特定字段
    将获取的信息整理为 rank_id_info_list 字典
    字典内容包含:
        server_id: pod中使用的芯片的 逻辑id 物理id
        rank_size: 训练任务使用的芯片总数
        single_pod_npu_count: 单个pod使用的npu芯片个数
    :return: tuple
    """
    hccl_json = read_json_content()
    server_list = hccl_json.get("server_list")
    server_count = hccl_json.get("server_count")
    if not server_count:
        print("Incorrect hccl.json content.")
        sys.exit(1)
    single_pod_npu_count = len(server_list[0].get("device"))
    rank_id_info_list = []
    device_count = 0

    for server in server_list:
        device_info_list = server.get("device")
        device_count += len(device_info_list)
        server_id = server.get("server_id")
        rank_instance_info_list = [server_id]
        device_info_list = sorted(device_info_list,
                                  key=lambda x: int(x.get("device_id")))
        for device_info in device_info_list:
            device_id = device_info.get("device_id")
            rank_id = device_info.get("rank_id")

            rank_info = device_id + " " + rank_id
            rank_instance_info_list.append(rank_info)

        rankid_info_str = ":".join(rank_instance_info_list)
        rank_id_info_list.append(rankid_info_str)

    rank_id_info_list.append("rank_size:{}".format(device_count))
    rank_id_info_list.append("single_pod_npu_count:{}"
                             .format(single_pod_npu_count))

    return tuple(rank_id_info_list)


def write_new_info_to_file():
    """
    创建 rank_id_info.txt 文件，记录训练任务所需的资源分配信息
    将 rank_id_info_list 内容输出至 rank_id_info.txt 文件中
    该文件用于后续训练任务使用
    """
    rank_id_info_list = create_rank_id_info()

    with open(RANK_ID_INFO_FILE_PATH, "w") as node_info_f:
        for rank_id_info in rank_id_info_list:
            node_info_f.write(rank_id_info)
            node_info_f.write("\n")


if __name__ == "__main__":
    write_new_info_to_file()
