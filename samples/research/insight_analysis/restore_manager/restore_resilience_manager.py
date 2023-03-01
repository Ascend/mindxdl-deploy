#!/usr/bin/python3
# -*- coding: utf-8 -*-
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
import os
import warnings
from ast import literal_eval
from typing import List, Optional

import mindspore.communication.management as D
import mindspore.train.serialization as serialization

from constants import constants
from constants.constants import MAX_RANK_STRING_LENGTH
from logger.log import srv_log, run_log
from validator.validators import DirectoryValidator, StringValidator, RankSizeValidator


class RestoreManager:
    """
    Get configmap resource class
    """

    def __init__(self):
        self.__strategy_input_file_path = os.path.realpath(os.getenv(constants.DEFAULT_STRATEGY_INPUT_ENV)) if \
            os.getenv(constants.DEFAULT_STRATEGY_INPUT_ENV) else None

    @staticmethod
    def _handle_input_strategy_file(input_strategy_file: str) -> [str, str]:
        path = os.path.dirname(input_strategy_file)
        strategy_name = os.path.basename(input_strategy_file)
        input_strategy_file_processed, _ = os.path.split(path)
        return input_strategy_file_processed, strategy_name

    @staticmethod
    def _check_input_parameter_fault_ranks(fault_ranks: str) -> bool:
        """
        Check input parameter fault ranks. For rank, its valid value range is [0, 4095]. Any value not in this range
        will be judged as invalid.
        :param fault_ranks: unhealthy npu rank id list
        :return: valid or not
        """
        fault_ranks_validation = StringValidator(fault_ranks, max_len=MAX_RANK_STRING_LENGTH)\
            .check_string_length()\
            .check()
        if not fault_ranks_validation.is_valid():
            return False

        fault_ranks_splits = fault_ranks.split(",")
        for rank in fault_ranks_splits:
            if not isinstance(literal_eval(rank), int):
                return False

            rank_flag = RankSizeValidator(literal_eval(rank))\
                .check_rank_size_valid()\
                .check()\
                .is_valid()
            if not rank_flag:
                return False
        return True

    @staticmethod
    def _check_path(path: str) -> str:
        validation = DirectoryValidator(path).check()
        if not validation.is_valid():
            return ""
        return validation.get_value()

    @staticmethod
    def _init_communication_group() -> bool:
        """
        Init commnucation group for multi-card training job.
        :return: action status
        """
        try:
            D.init()
        except TypeError:
            srv_log.error("MindSpore communication init raise TypeError, if backend_name is not a string.")
            return False
        except RuntimeError:
            srv_log.error("MindSpore communication init raise RuntimeError, if device target is invalid, or backend "
                          "is invalid, or distributed initialization fails, or the environment variables "
                          "RANK_ID/MINDSPORE_HCCL_CONFIG_PATH have not been exported when backend is HCCL.")
            return False
        else:
            srv_log.info("MindSpore communication init success.")
            return True

    @staticmethod
    def _get_communication_group_size() -> int:
        """
        Get multi-card training job used communication group size.
        :return: group size num
        """
        try:
            device_num = D.get_group_size()
        except TypeError:
            srv_log.error("MindSpore get group size raise TypeError, check if group is not a string.")
            return -1
        except ValueError:
            srv_log.error("MindSpore get group size raise ValueError, check if backend id invalid.")
            return -1
        except RuntimeError:
            srv_log.error("MindSpore get group size raise RuntimeError, check if HCCL/NCCL is not available.")
            return -1
        else:
            srv_log.info(f"device_num is {device_num}.")
            return device_num

    @staticmethod
    def _check_device_num(device_num: int) -> bool:
        """
        Check device num is valid or not.
        :param device_num: number of npu
        :return: bool, valid or not
        """
        device_num_flag = RankSizeValidator(device_num).check_device_num_valid().check().is_valid()
        if not device_num_flag:
            return False

        if device_num == 1:
            run_log.info("Stand alone training job is not supported for strategy recovery.")
            return False
        return True

    @staticmethod
    def _generate_fault_ranks_list(fault_ranks: str) -> List[int]:
        """
        Generate fault ranks list according to input fault ranks string.
        :param fault_ranks: input fault ranks string
        :return: fault ranks list
        """
        fault_ranks_list = []
        if not fault_ranks:
            return fault_ranks_list

        fault_ranks_splits = fault_ranks.split(",")
        for ele in fault_ranks_splits:
            if StringValidator(ele).can_be_transformed2int().is_valid():
                fault_ranks_list.append(int(ele))
        return fault_ranks_list

    @staticmethod
    def _process_strategy(device_group_info_list: List, fault_ranks_list: List[int] = None) -> [str, str]:
        """
        Generate restore ranks string and restore ranks map based on inputs of device group info and fault ranks list.
        :param device_group_info_list: GROUP_INFO_FILE path list
        :param fault_ranks_list: fault ranks list
        :return: restore ranks string and restore ranks map
        """
        restore_ranks = set()
        restore_rank_dict = dict()
        normal_rank_dict = dict()
        element_already_use = []

        for fault_rank in fault_ranks_list:
            elements = device_group_info_list[fault_rank]
            try:
                if not fault_ranks_list:
                    elements_for_use = set(elements) - set(element_already_use)
                else:
                    elements_for_use = set(elements) - set(fault_ranks_list) - set(element_already_use)
            except TypeError:
                restore_ranks = '-1'
                restore_rank_map_str = ""
                srv_log.error(f"Get fault ranks for use raise type error, restore ranks is {restore_ranks}, "
                              f"restore ranks map is {restore_rank_map_str}.")
                return restore_ranks, restore_rank_map_str

            if not elements_for_use:
                restore_ranks = '-1'
                restore_rank_map_str = ""
                srv_log.info(f"Fault ranks for use is empty, restore ranks is {restore_ranks}, "
                             f"restore ranks map is {restore_rank_map_str}.")
                return restore_ranks, restore_rank_map_str

            use_element = sorted(list(elements_for_use))[0]
            element_already_use.append(use_element)
            restore_rank_dict[str(fault_rank)] = use_element
            normal_rank_dict[str(use_element)] = fault_rank
            restore_ranks.add(sorted(list(elements_for_use))[0])

        restore_ranks_list = []
        for idx in restore_ranks:
            restore_ranks_list.append(str(idx))
        restore_ranks_str = ",".join(restore_ranks_list)
        restore_ranks_json = str(json.dumps(restore_rank_dict))
        normal_ranks_json = str(json.dumps(normal_rank_dict))

        if not restore_ranks_str or not restore_ranks_json:
            return "-1", ""

        srv_log.info(f"Restore ranks is {restore_ranks_str}, restore ranks map is {restore_ranks_json}")
        return normal_ranks_json, restore_ranks_json,

    @staticmethod
    def _get_restore_group_info_list(sub_strategy_input_file_name: str) -> List[int]:
        """
        Get parallel model communication information from group info file.
        :param sub_strategy_input_file_name: group info file
        :return: group information
        """
        try:
            if not os.path.exists(sub_strategy_input_file_name):
                return []
            res = serialization.restore_group_info_list(sub_strategy_input_file_name)
        except ValueError:
            srv_log.error("MindSpore restore group info list raise ValueError, check if group information file "
                          "is correct.")
            return []
        except TypeError:
            srv_log.error("MindSpore restore group info list raise TypeError, check if group_info_file_name is "
                          "string.")
            return []
        else:
            return res

    def _prepare_device_info(self,
                             device_num: int,
                             strategy_input_file_path: str,
                             strategy_name: str) -> Optional[list]:
        """
        Generate distributed deep learning cluster communication info.
        :param device_num: device number used for distributed deep learning
        :param strategy_input_file_path: GROUP_INFO_FILE path
        :param strategy_name: GROUP_INFO_FILE name
        :return: cluster communication info list
        """
        device_group_info_list = []
        for index in range(device_num):
            sub_strategy_input_file_path = os.path.join(strategy_input_file_path, f"device{index}")
            sub_strategy_input_file_name = os.path.join(sub_strategy_input_file_path, strategy_name)
            res = self._get_restore_group_info_list(sub_strategy_input_file_name)
            if not res:
                continue

            if res not in device_group_info_list:
                device_group_info_list.append(sorted(res))
        return device_group_info_list

    def process_data_parallel_strategy(self, fault_ranks):
        self._init_communication_group()
        device_num = self._get_communication_group_size()
        fault_ranks_check_flag = self._check_input_parameter_fault_ranks(fault_ranks)
        if not fault_ranks_check_flag:
            return "-1", ""

        fault_ranks_list = self._generate_fault_ranks_list(fault_ranks)
        fault_ranks_list_sort = sorted(fault_ranks_list)

        if device_num < len(fault_ranks_list_sort) * 2:
            return "-1", ""

        restore_ranks = set()
        restore_rank_dict = dict()
        normal_rank_dict = dict()
        element_already_use = []

        for fault_rank in fault_ranks_list_sort:
            elements = [i for i in range(device_num)]
            try:
                if not fault_ranks_list_sort:
                    elements_for_use = set(elements) - set(element_already_use)
                else:
                    elements_for_use = set(elements) - set(fault_ranks_list_sort) - set(element_already_use)
            except TypeError:
                restore_ranks = '-1'
                restore_rank_map_str = ""
                srv_log.error(f"Get fault ranks for use raise type error, restore ranks is {restore_ranks}, "
                              f"restore ranks map is {restore_rank_map_str}.")
                return restore_ranks, restore_rank_map_str

            if not elements_for_use:
                restore_ranks = '-1'
                restore_rank_map_str = ""
                srv_log.info(f"Fault ranks for use is empty, restore ranks is {restore_ranks}, "
                             f"restore ranks map is {restore_rank_map_str}.")
                return restore_ranks, restore_rank_map_str

            use_element = sorted(list(elements_for_use))[0]
            element_already_use.append(use_element)
            restore_rank_dict[str(fault_rank)] = use_element
            normal_rank_dict[str(use_element)] = fault_rank
            restore_ranks.add(sorted(list(elements_for_use))[0])

        restore_ranks_list = []
        for idx in restore_ranks:
            restore_ranks_list.append(str(idx))
        restore_ranks_str = ",".join(restore_ranks_list)
        restore_ranks_json = str(json.dumps(restore_rank_dict))
        normal_ranks_json = str(json.dumps(normal_rank_dict))

        if not restore_ranks_str or not restore_ranks_json:
            return "-1", ""

        srv_log.info(f"Restore ranks is {restore_ranks_str}, restore ranks map is {restore_ranks_json}")
        return normal_ranks_json, restore_ranks_json

    def generate_restore_strategy(self, fault_ranks: Optional[str]) -> [str, str]:
        """
        Generate restore strategy given fault ranks
        :param fault_ranks: input fault rank string
        :return: restore rank string and restore rank map
        """
        warnings.simplefilter('ignore', ResourceWarning)

        strategy_input_file_path = self._check_path(self.__strategy_input_file_path)
        if not strategy_input_file_path:
            return self.process_data_parallel_strategy(fault_ranks)

        strategy_input_file_path, strategy_name = self._handle_input_strategy_file(strategy_input_file_path)
        if not strategy_input_file_path or not strategy_name:
            return "-1", ""

        if not self._init_communication_group():
            return "-1", ""

        device_num = self._get_communication_group_size()
        if device_num == -1:
            return "-1", ""

        is_valid_device_num = self._check_device_num(device_num)
        if not is_valid_device_num:
            return "-1", ""

        device_group_info_list = self._prepare_device_info(device_num, strategy_input_file_path, strategy_name)

        if not fault_ranks:
            return self._process_strategy(device_group_info_list)

        fault_ranks_check_flag = self._check_input_parameter_fault_ranks(fault_ranks)
        if not fault_ranks_check_flag:
            return "-1", ""

        fault_ranks_list = self._generate_fault_ranks_list(fault_ranks)
        return self._process_strategy(device_group_info_list, fault_ranks_list)

