#!/usr/bin/python3
# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2022. All rights reserved.
import os

from mindx_elastic.restore_module.fault_rank_manager.fault_rank_manager import FaultRanksManager
from mindx_elastic.restore_module.restore_manager.restore_manager import \
    RestoreManager
from mindx_elastic.logger.log import run_log, srv_log


class RestoreStrategyGenerator:
    """
    Get restore strategy in exception occured situation.
    """

    def __init__(self):
        self.res_manager = RestoreManager()
        self.config_map_handler = FaultRanksManager()

    def gen_fault_tolerance_strategy(self):
        run_log.info("Start to generate fault tolerance strategy.")
        get_fault_ranks_flag, fault_ranks = \
            self.config_map_handler.get_fault_ranks()

        if not get_fault_ranks_flag:
            restore_ranks = '-1'
            restore_rank_dict = None
            os.environ["RESTORE_RANKS"] = restore_ranks
            srv_log.info(f"Fault ranks query failed, restore ranks is {restore_ranks}, "
                         f"restore ranks map is {restore_rank_dict}")
            return restore_ranks, restore_rank_dict

        if not fault_ranks:
            restore_ranks = '-1'
            restore_rank_dict = None
            os.environ["RESTORE_RANKS"] = restore_ranks
            srv_log.info(f"Fault ranks is empty, restore ranks is {restore_ranks}, "
                         f"restore ranks map is {restore_rank_dict}")
            return restore_ranks, restore_rank_dict

        restore_ranks_str, restore_ranks_json = \
            self.res_manager.generate_restore_strategy(
                strategy_input_file_path=None,
                fault_ranks=fault_ranks
            )
        srv_log.info(f"Fault ranks query success, restore ranks is {restore_ranks_str}, "
                     f"restore ranks map is {restore_ranks_json}")
        return restore_ranks_str, restore_ranks_json
