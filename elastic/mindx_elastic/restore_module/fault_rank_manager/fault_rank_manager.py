#!/usr/bin/python3
# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2022. All rights reserved.
import collections
from ast import literal_eval
import os

from mindx_elastic.constants import constants
from mindx_elastic.constants.constants import MAX_RANK_STRING_LENGTH
from mindx_elastic.logger.log import run_log
from mindx_elastic.validator.validators import StringValidator, MapValidator, DirectoryValidator


def _fault_ranks_process(res: str, fault_ranks: str):
    """
    Get fault ranks process
    """
    if not StringValidator(res).is_valid():
        run_log.warn("The content of the fault config file is invalid.")
        return fault_ranks

    if not MapValidator(literal_eval(res), inclusive_keys=["FaultRankIds"]).is_valid():
        run_log.warn("The content of the fault config file has not key(FaultRankIds)")
        return fault_ranks

    record_fault_rank_list_content = str(literal_eval(res)["FaultRankIds"])
    if len(record_fault_rank_list_content) > MAX_RANK_STRING_LENGTH:
        run_log.error("The content of fault rank exceed the max string length.")
        return fault_ranks

    record_fault_rank_list = literal_eval(record_fault_rank_list_content)
    if not isinstance(record_fault_rank_list, collections.Iterable):
        run_log.warn("The value of the key(FaultRankIds) is not list")
        return fault_ranks

    clear_fault_rank_list = []
    for ele in record_fault_rank_list:
        if ele.isdigit() and constants.MIN_RANK_SIZE <= literal_eval(ele) <= constants.MAX_RANK_SIZE:
            clear_fault_rank_list.append(ele)

    res_config_map_fault_ranks = ",".join(clear_fault_rank_list)
    fault_ranks += res_config_map_fault_ranks
    run_log.info(f"Fault ranks is {fault_ranks}, type is {type(fault_ranks)}")
    return fault_ranks


class FaultRanksManager:
    def __init__(self):
        self.fault_config_path = constants.FAULT_RANK_CONFIG

    def get_fault_ranks(self):
        """
        Get fault ranks in training job when exception happens.
        """
        run_log.info("Start query fault ranks.")
        default_fault_ranks = None
        if '..' in self.fault_config_path:
            raise ValueError("Fault ranks config path is invalid")
        fault_npu_file_path = os.path.join(self.fault_config_path, constants.FAULT_NPU_FILE)
        validation = DirectoryValidator(fault_npu_file_path, max_len=255)\
            .path_should_exist(is_file=True, msg="Cannot find the fault ranks config file.")\
            .should_not_contains_sensitive_words()\
            .with_blacklist()\
            .check()
        if not validation.is_valid():
            return False, default_fault_ranks

        try:
            with open(fault_npu_file_path, "r") as fault_config_out:
                fault_ranks = _fault_ranks_process(fault_config_out.read(), "")
                if not fault_ranks:
                    return False, default_fault_ranks
                return True, fault_ranks
        except Exception as e:
            run_log.error(f"Load fault config file failed, {str(e)}")
            return False, default_fault_ranks
        finally:
            run_log.info("Finish the operation for querying fault ranks")
