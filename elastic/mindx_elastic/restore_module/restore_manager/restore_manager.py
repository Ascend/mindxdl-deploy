#!/usr/bin/python3
# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2022. All rights reserved.
import json
import os
import warnings

import mindspore.communication.management as D
from mindspore.train.serialization import restore_group_info_list

from mindx_elastic.constants import constants
from mindx_elastic.logger.log import srv_log
from mindx_elastic.validator.validators import DirectoryValidator, StringValidator


class RestoreManager:
    """
    Get configmap resource class
    """

    def __init__(self):
        if os.getenv(constants.DEFAULT_STRATEGY_INPUT_ENV):
            self.strategy_input_file_path = os.path.realpath(os.getenv(constants.DEFAULT_STRATEGY_INPUT_ENV))
        else:
            self.strategy_input_file_path = None

        self.job_id = None
        if os.getenv(constants.JOB_ID_ENV):
            self.job_id = StringValidator(os.getenv(constants.JOB_ID_ENV)).should_match_regexes(
                constants.JOB_ID_PATTERN).get_value(None)

    def _handle_input_strategy_file(self, input_strategy_file):
        if not input_strategy_file:
            tmp_strategy_input_file_path = self.strategy_input_file_path
        else:
            tmp_strategy_input_file_path = input_strategy_file

        if not tmp_strategy_input_file_path:
            return None, None
        path = os.path.dirname(tmp_strategy_input_file_path)
        strategy_name = os.path.basename(tmp_strategy_input_file_path)
        input_strategy_file_processed, _ = os.path.split(path)
        return input_strategy_file_processed, strategy_name

    @staticmethod
    def _input_parameter_fault_ranks_check(fault_ranks):
        restore_ranks = set()
        restore_rank_dict = dict()
        # get ranks
        if not fault_ranks:
            restore_ranks = '-1'
            restore_rank_dict = None
            os.environ["RESTORE_RANKS"] = restore_ranks
            srv_log.info(f"Fault ranks is empty, restore ranks is {restore_ranks}, "
                         f"restore ranks map is {restore_rank_dict}")
            return restore_ranks, restore_rank_dict

        if "-1" == fault_ranks:
            restore_ranks = '-1'
            restore_rank_dict = None
            os.environ["RESTORE_RANKS"] = restore_ranks
            srv_log.info(f"Fault ranks is invalid {fault_ranks}, restore ranks is {restore_ranks}, "
                         f"restore ranks map is {restore_rank_dict}")
            return restore_ranks, restore_rank_dict
        return restore_ranks, restore_rank_dict

    @staticmethod
    def _input_parameter_strategy_info_check(strategy_input_file_path, strategy_name):
        restore_ranks = set()
        restore_rank_dict = dict()

        if not strategy_input_file_path:
            restore_ranks = '-1'
            restore_rank_dict = None
            os.environ["RESTORE_RANKS"] = restore_ranks
            srv_log.info(f"Strategy file is invalid, restore ranks is {restore_ranks}, "
                         f"restore ranks map is {restore_rank_dict}")
            return restore_ranks, restore_rank_dict

        if not strategy_name:
            restore_ranks = '-1'
            restore_rank_dict = None
            os.environ["RESTORE_RANKS"] = restore_ranks
            srv_log.info(f"Strategy file is invalid, restore ranks is {restore_ranks}, "
                         f"restore ranks map is {restore_rank_dict}")
            return restore_ranks, restore_rank_dict
        return restore_ranks, restore_rank_dict

    @staticmethod
    def _check_path(path):
        validation = DirectoryValidator(path)
        if not validation.is_valid():
            return None
        return validation.get_value()

    @staticmethod
    def _get_device_num():
        """
        Strategy recovery is used under condition of hybird model training.
        :return:
        """
        D.init()
        # get_group_size function is provided by MindSpore and its max return value is 4095
        device_num = D.get_group_size()
        srv_log.debug("device_num is {}".format(device_num))
        return device_num

    def generate_restore_strategy(self, strategy_input_file_path, fault_ranks):
        warnings.simplefilter('ignore', ResourceWarning)
        strategy_input_file_path = self._check_path(strategy_input_file_path)
        strategy_input_file_path, strategy_name = self._handle_input_strategy_file(strategy_input_file_path)

        restore_ranks, restore_rank_dict = self._input_parameter_strategy_info_check(strategy_input_file_path,
                                                                                     strategy_name)
        if restore_ranks == "-1":
            return restore_ranks, restore_rank_dict

        device_num = self._get_device_num()
        device_group_info_list = []
        for index in range(device_num):
            sub_strategy_input_file_path = os.path.join(strategy_input_file_path, f"device{index}")
            sub_startegy_input_file_name = os.path.join(sub_strategy_input_file_path, strategy_name)
            res = restore_group_info_list(sub_startegy_input_file_name)
            if res not in device_group_info_list:
                device_group_info_list.append(sorted(res))

        restore_ranks, restore_rank_dict = \
            self._input_parameter_fault_ranks_check(fault_ranks)
        if restore_ranks == '-1':
            return restore_ranks, restore_rank_dict

        fault_ranks_list = []
        fault_ranks_splits = fault_ranks.split(",")
        for ele in fault_ranks_splits:
            if StringValidator(ele).can_be_transformed2int().is_valid():
                fault_ranks_list.append(int(ele))

        for elements in device_group_info_list:
            elements_for_use = set(elements) - set(fault_ranks_list)
            if not elements_for_use:
                restore_ranks = '-1'
                restore_rank_dict = None
                os.environ["RESTORE_RANKS"] = restore_ranks
                srv_log.info(f"Fault ranks for use is empty, restore ranks is {restore_ranks}, "
                             f"restore ranks map is {restore_rank_dict}")
                return restore_ranks, restore_rank_dict

            elements_str = ",".join(map(str, elements))
            restore_rank_dict[elements_str] = sorted(list(elements_for_use))[0]
            restore_ranks.add(sorted(list(elements_for_use))[0])

        restore_ranks_list = []
        for idx in restore_ranks:
            restore_ranks_list.append(str(idx))
        restore_ranks_str = ",".join(restore_ranks_list)
        restore_ranks_json = json.dumps(restore_rank_dict)

        os.environ["RESTORE_RANKS"] = restore_ranks_str
        os.environ["RESTORE_RANKS_MAP"] = str(restore_ranks_json)
        srv_log.info(f"Restore ranks is {restore_ranks_str}, restore ranks map is {str(restore_ranks_json)}")
        return restore_ranks_str, str(restore_ranks_json)
