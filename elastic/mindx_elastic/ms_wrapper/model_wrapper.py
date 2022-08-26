#!/usr/bin/python3
# -*- coding: utf-8 -*-
#   Copyright (C)  2022. Huawei Technologies Co., Ltd. All rights reserved.
import os
import glob
import re
from typing import Optional, List
import inspect

from mindspore import Model
from mindspore import load_param_into_net, load_checkpoint
from mindspore import restore_group_info_list
from mindspore.train.callback import Callback, ModelCheckpoint

from mindx_elastic.logger.log import run_log, srv_log, is_running_over_modelarts_platform
from mindx_elastic.utils.utils import get_device_id
from mindx_elastic.terminating_message import ExceptionCheckpoint
from mindx_elastic.ms_wrapper.wrapper_function import _save_final_ckpt
from mindx_elastic.restore_module import RestoreManager


class ElasticModel:
    def __init__(self, ms_model: Model):
        if not isinstance(ms_model, Model):
            raise ValueError("The instance should be mindspore.Model")
        self._ms_model = ms_model

        self._ckpt_save_path = ""
        self._ckpt_config = None
        self._ckpt_prefix = ""
        self._append_epoch = 0
        self._append_step = 0

        # check training platform is ModelArts Or MindXDL
        self._is_ma_platform = is_running_over_modelarts_platform()

        self._device_id = get_device_id()

    def __hack(self, callbacks=Optional[List[Callback]]) -> None:
        """
        1. Fetch parameters passed by user
        2. Find available checkpoint for loading.
        3. Read append_dict from checkpoint.
        4. Load checkpoint into network.
        5. Inject info into callbacks
        6. Replace decorator of Model._train

        Args:
            callbacks: callback func list

        Returns:

        """
        success = self.__fetch_args_from_model(callbacks)
        if not success:
            return

        ckpt_path = self.__get_available_checkpoint()
        if ckpt_path:
            run_log.info(f"{ckpt_path} will be loaded to model.")
            param_dict = load_checkpoint(ckpt_path)

            self.__fetch_epoch_info(param_dict)

            self.__load_checkpoint_info_net(param_dict)

            run_log.info(f"{ckpt_path} loaded.")

        self.__inject_info_info_callbacks(callbacks)

        self.__replace_decorator()

    def __fetch_args_from_model(self, callbacks=Optional[List[Callback]]) -> bool:
        """
        Fetch parameters passed by user
        Args:
            callbacks: List of callback objects, which should be executed while training

        Returns:

        """
        success = False
        for callback in callbacks:
            if isinstance(callback, ModelCheckpoint):
                self._ckpt_save_path = callback._directory
                self._ckpt_config = callback._config
                self._ckpt_prefix = callback._prefix
                success = True
                break

        if not success:
            run_log.log("Elastic is disable for the absence of ModelCheckpoint Callback in callbacks parameter.")

        return success

    def __get_available_checkpoint(self) -> str:
        """
        Find valid checkpoint for resuming training process.
        1. If running over MinXDL, RestoreStrategy will be used to find  appropriate piece of checkpoint file for
        loading. It means that the piece of checkpoint file on other device saving path will be used to instantiate
        the model on current device. For example, according to the group_file_info (please refer to official
        documentation of MindSpore for details), device 0 and 8 share the same model parameters. Then, we can load
        model parameters for device 8 from checkpoint file saving on device 0 or 8 and vice versa.
        2. Otherwise, current device load available checkpoint from its own local saving path.
        Returns:

        """
        ckpt_path_from_strategy = self.__get_available_checkpoint_according_to_restore_strategy()
        if ckpt_path_from_strategy:
            return ckpt_path_from_strategy

        local_ckpt_path = self.__get_available_checkpoint_locally(self._ckpt_save_path)
        return local_ckpt_path

    def __get_available_checkpoint_according_to_restore_strategy(self) -> str:
        """
        If some nodes fail when training, there is a possibility that the training procedure can be resumed with
        redundant checkpoint file saved on other normal nodes.
        The redundancy information is stored in GROUP_INFO_FILE managed by MindSpore. Refer to the documentation of
        MindSpore for details.
        Returns:

        """
        restore_manager = RestoreManager()
        strategy_input_file_path, strategy_name = restore_manager._handle_input_strategy_file("")
        sub_strategy_input_file_path = os.path.join(strategy_input_file_path, f"device{self._device_id}")
        sub_strategy_input_file_name = os.path.join(sub_strategy_input_file_path, strategy_name)
        if not os.path.exists(sub_strategy_input_file_name):
            return ""
        res = restore_group_info_list(sub_strategy_input_file_name)
        run_log.info(f"group info list for device-{self._device_id} is : {res}")
        if len(res) <= 1:
            return ""

        pattern_list = []
        for device_id in res:
            pattern_list.append(re.compile(f"[^0-9]*{device_id}[^0-9]*"))

        ckpt_root_path, _ = os.path.split(self._ckpt_save_path)
        all_device_ckpt_path = glob.glob(os.path.join(ckpt_root_path, "*"))
        # there are subdirectories like xxxdeviceIDxxx in root ckpt path
        ckpt_share_path_list = list(filter(lambda x: any([p.match(x) for p in pattern_list]), all_device_ckpt_path))
        for ckpt_path in ckpt_share_path_list:
            tmp_path = self.__get_available_checkpoint_locally(ckpt_path)
            if not tmp_path or not tmp_path.endswith("breakpoint.ckpt"):
                continue
            return tmp_path

        return ""

    def __get_available_checkpoint_locally(self, ckpt_dir: str) -> str:
        """
        Check whether there is a valid checkpoint file at specified saving path.
        If exists, the path is returned
        Args:
            ckpt_dir:

        Returns:

        """
        ckpt_path = ""
        ckpt_file = ""

        ckpt_pattern = os.path.join(ckpt_dir, f"*.ckpt")
        ckpt_all_files = glob.glob(ckpt_pattern)

        if not ckpt_all_files:
            run_log.info(f"There if no ckpt file in {ckpt_dir}, so skip the loading.")
            return ckpt_path

        is_valid = self.__exists_valid_breakpoint_file(ckpt_dir)
        ckpt_all_files.sort(key=self.__sort_key)
        for ckpt in ckpt_all_files:
            if is_valid and ckpt.endswith("breakpoint.ckpt"):
                ckpt_file = ckpt
                break
            if not is_valid and "breakpoint" not in ckpt:
                ckpt_file = ckpt
                break

        run_log.info(f"{ckpt_file} will be loaded")
        ckpt_path = os.path.join(ckpt_dir, ckpt_file)
        return ckpt_path

    def __exists_valid_breakpoint_file(self, ckpt_dir: str) -> bool:
        """
        Check the integrity of each piece of breakpoint checkpoint file
        Args:
            ckpt_dir:

        Returns:

        """
        is_valid = True
        latest_exp_ckpt_size_list = []
        ckpt_root_path, sub_dir = os.path.split(ckpt_dir)
        for p in os.listdir(ckpt_root_path):
            if not os.path.isdir(os.path.join(ckpt_root_path, p)):
                continue

            if not is_valid:
                break

            ckpt_exp_pattern = os.path.join(ckpt_root_path, p, f"*_breakpoint.ckpt")
            ckpt_pattern = os.path.join(ckpt_root_path, p, f"*.ckpt")
            ckpt_all_files = glob.glob(ckpt_pattern)
            ckpt_exp_files = glob.glob(ckpt_exp_pattern)

            if not ckpt_exp_files:
                is_valid = False
                break

            ckpt_exp_files.sort(key=self.__sort_key)
            latest_exp_ckpt = ckpt_exp_files[0]
            latest_exp_ckpt_size = os.path.getsize(latest_exp_ckpt)
            latest_exp_ckpt_size_list.append(latest_exp_ckpt_size)

            if ckpt_all_files and ckpt_exp_files:
                ckpt_all_files.sort(key=self.__sort_key)
                oldest_ckpt = ckpt_all_files[0]
                if latest_exp_ckpt != oldest_ckpt and latest_exp_ckpt_size != os.path.getsize(oldest_ckpt):
                    is_valid = False

        if is_valid and len(set(latest_exp_ckpt_size_list)) != 1:
            is_valid = False

        return is_valid

    def __sort_key(self, ckpt_file_path: str):
        """
        The key function of builtin sort method. Sorting the checkpoint file by descending order by default.
        When using OBS as model saving backends, the "modify time" of file cannot be used as the sort key. Instead,
        epoch and step info in the file name can be used to identify the creation time.
        Args:
            ckpt_file_path: checkpoint file path

        Returns:

        """

        if not self._is_ma_platform:
            return -os.path.getmtime(ckpt_file_path)

        try:
            # extract epoch and step info from file name
            pattern = re.compile("([0-9]+)_([0-9]+)")
            _, file_name = os.path.split(ckpt_file_path)
            epoch_step_suffix = file_name.split("-")[-1]
            result = pattern.search(epoch_step_suffix)
            if result is None:
                run_log.error(f"Cannot parse epoch and step info from ckpt file path: {ckpt_file_path}")
                return -os.path.getmtime(ckpt_file_path)

        except ValueError as exp:
            run_log.error(f"Cannot parse epoch and step info from ckpt file path: {ckpt_file_path}, msg: {exp}")
            return -os.path.getmtime(ckpt_file_path)

        epoch, step = result.groups()
        return -int(epoch), -int(step)

    def __fetch_epoch_info(self, param_dict: dict):
        """
        Get epoch info from checkpoint file
        Args:
            param_dict:

        Returns:

        """
        if param_dict.get("epoch_num") and param_dict.get("step_num"):
            self._append_epoch = int(param_dict["epoch_num"].data.asnumpy())
            self._append_step = int(param_dict["epoch_step"].data.asnumpy())
            run_log.info(f"Epoch num: {self._append_epoch}, Step num: {self._append_step}")

    def __load_checkpoint_info_net(self, para_dict: dict) -> None:
        load_param_into_net(self._ms_model._network, para_dict)

    def __inject_info_info_callbacks(self, callbacks=Optional[List[Callback]]):
        """
        1. Replace epoch and step of Callbacks.
        2. Add Elastic ExceptionCheckpoint callback to Callbacks
        Args:
            callbacks:

        Returns:

        """
        for callback in callbacks:
            if hasattr(callback, "has_trained_epoch"):
                callback.has_trained_epoch = self._append_epoch
                run_log.info(f"Set has_trained_epoch of {callback.__class__.__name__} to {self._append_epoch}")

            if hasattr(callback, "has_trained_step"):
                callback.has_trained_step = self._append_step
                run_log.info(f"Set has_trained_step of {callback.__class__.__name__} to {self._append_step}")

            if isinstance(callback, ModelCheckpoint):
                callback._config.append_dict["epoch_num"] = self._append_epoch
                callback._config.append_dict["step_num"] = self._append_step

                # When running over ModelArts platform, need to turn on exception_save of ModelCheckpoint
                if not callback._config.exception_save and self._is_ma_platform:
                    callback._config.exception_save = True
                    run_log.info("Turn on exception_save of ModelCheckpoint")

        # Add Elastic ExceptionCheckpoint callback to user passed callbacks.
        ckpoint_exp = ExceptionCheckpoint(prefix=self._ckpt_prefix,
                                          directory=self._ckpt_save_path,
                                          config=self._ckpt_config)
        callbacks.append(ckpoint_exp)
        run_log.info("Elastic ExceptionCheckpoint callback has been added to callbacks")

    def __replace_decorator(self):
        """
        Replace the decorator of mindspore.model._train with Elastic decorator
        Returns:

        """
        try:
            self._ms_model._train = _save_final_ckpt(instance=self._ms_model,
                                                     func=inspect.unwrap(self._ms_model._train))
            run_log.info("Decorator of mindspore.model._train has benn replaced.")
        except ValueError as exp:
            run_log.error(f"Failed to replace the decorator of mindspore.model._train, msg: {exp}")

    def train(self, epoch, train_dateset, callbacks=None, dataset_sink_mode=True, sink_size=-1):
        """
        Parameters inherited from mindspore.model.train().
        Args:
            epoch:
            train_dateset:
            callbacks:
            dataset_sink_mode:
            sink_size:

        Returns:

        """

        if isinstance(callbacks, (list, Callback)):
            if isinstance(callbacks, Callback):
                callbacks = [callbacks]

            srv_log.info("Elastic preparation starts.")
            self.__hack(callbacks)
            # subtract the trained period
            epoch -= self._append_epoch
            srv_log.info("Elastic preparation done.")
        else:
            srv_log.info("callbacks not passed to model.train(). Elastic is disabled.")

        self._ms_model.train(epoch,
                             train_dateset,
                             callbacks=callbacks,
                             dataset_sink_mode=dataset_sink_mode,
                             sink_size=sink_size)
