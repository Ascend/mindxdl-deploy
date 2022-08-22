#!/usr/bin/python3
# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2022. All rights reserved.
from ast import literal_eval
import glob
import json
import os
from argparse import Namespace

import mindspore.communication.management as D
from mindspore.train.serialization import load_checkpoint, load_param_into_net

from mindx_elastic.constants.constants import MAX_RANK_STRING_LENGTH
from mindx_elastic.restore_module.gen_restore_ranks import RestoreStrategyGenerator
from mindx_elastic.logger.log import run_log, srv_log
from mindx_elastic.validator.validators import StringValidator, DirectoryValidator
from mindspore.nn.cell import Cell
from mindspore.dataset import Dataset
from mindspore.train import Model


class RestoreCheckpoint:
    """
    Get restore checkpoint for Hybrid Parallel training.
    """

    @staticmethod
    def get_exception_checkpoints(params: Namespace):
        r"""
        Load checkpoint process.
        """
        run_log.info("======start exception checkpoint")
        ckpt_file_list = []
        restore_ranks = os.getenv("RESTORE_RANKS")
        if not StringValidator(restore_ranks, min_len=1, max_len=MAX_RANK_STRING_LENGTH).is_valid():
            return ckpt_file_list

        restore_ranks_list = restore_ranks.split(",")
        for ele in restore_ranks_list:
            if not isinstance(literal_eval(ele), int):
                return ckpt_file_list

        restore_rank_list = list(map(int, restore_ranks.split(",")))
        ckpt_name = params.ckpt_name_prefix
        if not StringValidator(ckpt_name, min_len=1).is_valid():
            return ckpt_file_list

        if not DirectoryValidator(params.save_checkpoint_path).is_valid():
            return ckpt_file_list

        for ckpt_rank in restore_rank_list:
            ckpt_pattern = os.path.join(params.save_checkpoint_path,
                                        f"rank_{ckpt_rank}",
                                        f"{ckpt_name}*_breakpoint.ckpt")
            ckpt_files = glob.glob(ckpt_pattern)
            if not ckpt_files:
                run_log.info(
                    f"There is no ckpt file in {params.save_checkpoint_path}, "
                    f"current ckpt_files found is {ckpt_files} "
                    f"with pattern {ckpt_pattern}, so skip the loading.")
                return []
            ckpt_files.sort(key=os.path.getmtime, reverse=True)
            ckpt_file_list.append(ckpt_files[0])
        srv_log.debug(f"checkpoint file {ckpt_file_list}")
        return ckpt_file_list

    @staticmethod
    def check_exception_checkpoints(ckpt_file_list):
        """
        Checkpoint exception checkpoints size.
        Args:
            ckpt_file_list: exception checkpoints

        Returns: result of exception checkpoints size check.

        """
        ckpt_size_list = []
        for ckpt_file in ckpt_file_list:
            if not os.path.exists(ckpt_file):
                return False

            ckpt_size_list.append(os.path.getsize(ckpt_file))

        return len(set(ckpt_size_list)) == 1

    @staticmethod
    def _strategy_prepare():
        restore_strategy_generator = RestoreStrategyGenerator()
        res_query = restore_strategy_generator.gen_fault_tolerance_strategy()
        if not res_query:
            return False

        restore_ranks, restore_dict = res_query
        srv_log.debug(f"restore ranks: {restore_ranks}, restore dict: {restore_dict}")
        if not restore_ranks:
            return False

        if not restore_dict:
            return False

        os.environ["RESTORE_RANKS"] = restore_ranks
        os.environ["RESTORE_RANKS_MAP"] = str(restore_dict)
        return True

    def restore_exception_checkpoint(self, args_param: Namespace, sink_size: int, dataset: Dataset,
                                     model: Model, network: Cell, epoch: int):
        """
        Restore exception checkpoint.
        Args:
            args_param: training job params
            sink_size: training job sink size
            dataset: dataset for training
            model: model
            network: pangu_alpha network
            epoch: training epoch

        Returns: load exception checkpoint success or not.

        """
        if not self._strategy_prepare():
            return False

        if os.getenv("RESTORE_RANKS") == "-1":
            return False

        input_data_and_models_type_check = \
            isinstance(dataset, Dataset) and isinstance(model, Model) and isinstance(network, Cell)
        argument_type_check = isinstance(args_param, Namespace)
        if not argument_type_check or not isinstance(sink_size, int) or not input_data_and_models_type_check or \
                not isinstance(epoch, int):
            return False

        ckpt_file_list = self.get_exception_checkpoints(args_param)

        restore_flag = False
        if ckpt_file_list:
            restore_flag = self.check_exception_checkpoints(ckpt_file_list)

        if not restore_flag:
            return False

        ckpt_name = args_param.ckpt_name_prefix
        if not StringValidator(ckpt_name, min_len=1).is_valid():
            return False

        restore_ranks_map = os.getenv("RESTORE_RANKS_MAP")
        if not restore_ranks_map or not StringValidator(restore_ranks_map, min_len=1).is_valid():
            return False

        try:
            run_log.info("whether run into load process")
            restore_ranks_map_json = json.loads(restore_ranks_map)
            map_rank_id = D.get_rank()
            for key in restore_ranks_map_json.keys():
                if str(D.get_rank()) in key:
                    map_rank_id = restore_ranks_map_json.get(key)

            srv_log.debug(f"loading map rank id {map_rank_id}")
            ckpt_pattern = os.path.join(os.path.realpath(args_param.save_checkpoint_path),
                                        f"rank_{map_rank_id}",
                                        f"{ckpt_name}*breakpoint.ckpt")
            ckpt_files = glob.glob(ckpt_pattern)
            ckpt_files.sort(key=os.path.getmtime, reverse=True)
            run_log.info(f" checkpoint files {ckpt_files[0]}")
            param_dict = load_checkpoint(ckpt_files[0])
            srv_log.debug(f" checkpoint param dict epoch num {param_dict.get('epoch_num')}")
            if param_dict.get("epoch_num") and param_dict.get("step_num"):
                args_param.has_trained_epoches = int(param_dict["epoch_num"].data.asnumpy())
                args_param.has_trained_steps = int(param_dict["step_num"].data.asnumpy())

            # Load checkpoint files
            model.build(train_dataset=dataset, sink_size=sink_size, epoch=epoch)
            load_param_into_net(network, param_dict)
        except TypeError:
            return False
        else:
            return True
