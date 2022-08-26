#!/usr/bin/python3
# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2022. All rights reserved.
"""Exception checkpoint related classes and functions."""

import os
import signal

from mindspore.train.callback import Callback, CheckpointConfig, RunContext
from mindspore.train.serialization import save_checkpoint
from mindspore.train._utils import _make_directory

from mindx_elastic.constants.constants import MAX_CKPT_NUMS
from mindx_elastic.logger.log import srv_log, run_log

from mindx_elastic.validator.validators import DirectoryValidator
_cur_dir = os.getcwd()


def _index_check(suffix_num, filename, pre_len):
    """
    Set suffix_num according to checkpoint directory existed files
    :param suffix_num: suffix value of checkpoint
    :return: suffix num
    """
    index = filename[pre_len:].find("-")
    if index == 0:
        suffix_num = max(suffix_num, 1)
    elif index != -1:
        num = filename[pre_len + 1:pre_len + index]
        if num.isdigit():
            suffix_num = max(suffix_num, int(num) + 1)
    return suffix_num


def _check_bpckpt_file_name_if_same_exist(directory, prefix):
    """Check if there is a file with the same name."""
    if not DirectoryValidator(directory).is_valid():
        return prefix
    realpath = DirectoryValidator(directory).get_value()
    files = os.listdir(realpath)
    if len(files) > MAX_CKPT_NUMS:
        raise ValueError(f"Too many files in checkpoint directory. The file number exceeds {MAX_CKPT_NUMS}")

    suffix_num = 0
    pre_len = len(prefix)
    for filename in files:
        if not filename.endswith('_breakpoint.ckpt'):
            continue
        # find same prefix file
        if filename.find(prefix) == 0 and not filename[pre_len].isalpha():
            # add the max suffix + 1
            suffix_num = _index_check(suffix_num, filename, pre_len)
    if suffix_num != 0:
        prefix = prefix + "_" + str(suffix_num)
    return prefix


class ExceptionCheckpoint(Callback):
    """
    The exception checkpoint callback class.

    It is called to combine with train process and save the model
    and network parameters after training.

    Note:
        In the distributed training scenario, please specify different
        directories for each training process
        to save the exception checkpoint file. Otherwise, the training may fail.

    Args:
        prefix (str): The prefix name of exception checkpoint files.
        Default: "Exception".
        directory (str): The path of the folder which will be saved in the
        checkpoint file. By default, the file is saved in the current
        directory. Default: None.
        config (CheckpointConfig): Checkpoint strategy configuration.
        Default: None.

    Raises:
        ValueError: If the prefix is invalid.
        TypeError: If the config is not CheckpointConfig type.
    """

    def __init__(self, prefix='Exception', directory=None, config=None):
        super(ExceptionCheckpoint, self).__init__()
        signal.signal(signal.SIGTERM, self.save)
        signal.signal(signal.SIGINT, self.save)
        self.cb_params = None

        if not isinstance(prefix, str) or prefix.find('/') >= 0:
            raise ValueError(
                f"For 'ExceptionCheckpoint', the argument 'prefix' "
                f"must be string and the first letter "
                f"of it can't be \"/\", but got 'prefix' type: {type(prefix)}, "
                f"'prefix': {prefix}.")

        if directory is not None:
            if os.path.normpath(directory) != os.path.abspath(directory):
                raise ValueError("Something wrong with directory. Directory can not be soft link.")

            self._directory = _make_directory(directory)
        else:
            self._directory = _cur_dir
        self._prefix = _check_bpckpt_file_name_if_same_exist(self._directory,
                                                             prefix)

        if config is None:
            self._config = CheckpointConfig()
        else:
            if not isinstance(config, CheckpointConfig):
                raise TypeError(
                    f"For 'ExceptionCheckpoint', the argument 'config' "
                    "should be CheckpointConfig type, "
                    "but got {type(config)}.")
            self._config = config

        self._append_dict = self._config.append_dict or {}
        self._append_epoch_num = self._append_dict[
            "epoch_num"] if "epoch_num" in self._append_dict else 0
        self._append_step_num = self._append_dict[
            "step_num"] if "step_num" in self._append_dict else 0

    def __exit__(self, *err):
        pass

    def begin(self, run_context):
        """
        Called once before the network executing.

        Args:
            run_context (RunContext): Include some information of the model.
        """
        if not isinstance(run_context, RunContext):
            raise ValueError("the input type is not RunContext for callback")
        self.cb_params = run_context.original_args()

    def save(self, signum, frame):
        """
        Save current checkpoint when an error is occur.
        """
        if not isinstance(signum, int):
            raise ValueError("the input signum is not an integer")
        run_log.info(f"Exception has been catched, signal {signum} context {frame}, save is running.")
        if self.cb_params is None:
            srv_log.debug(f"Runcontext {self.cb_params} in current task is empty.")
            raise ValueError("Context parameters are empty, save exception "
                             "checkpoint failed.")

        prefix = _check_bpckpt_file_name_if_same_exist(self._directory,
                                                       self._prefix)
        step_num_in_epoch = int(
            (self.cb_params.cur_step_num - 1) % self.cb_params.batch_num + 1)

        cur_ckpt_file = f"{prefix}-{self.cb_params.cur_epoch_num}_" \
                        f"{step_num_in_epoch}_breakpoint.ckpt"
        cur_file = os.path.join(self._directory, cur_ckpt_file)

        if "epoch_num" in self._append_dict:
            self._append_dict["epoch_num"] = self._append_epoch_num + \
                                             self.cb_params.cur_epoch_num
        if "step_num" in self._append_dict:
            self._append_dict["step_num"] = self._append_step_num + \
                              self.cb_params.cur_step_num
        network = self._config.saved_network \
            if self._config.saved_network is not None \
            else self.cb_params.train_network

        try:
            run_log.info("Start to save exception checkpoint.")
            save_checkpoint(network,
                            cur_file,
                            self._config.integrated_save,
                            self._config.async_save,
                            self._append_dict,
                            self._config.enc_key,
                            self._config.enc_mode)
            run_log.info("Save exception checkpoint success.")
        except RuntimeError as exp:
            run_log.error(f"Save checkpoint failed, reason is {exp}.")
        else:
            raise RuntimeError("Term exception happened.")
