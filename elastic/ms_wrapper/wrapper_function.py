# coding: utf-8

# Copyright(C) 2022. Huawei Technologies Co.,Ltd. All rights reserved.
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


from functools import wraps
import os

from mindspore.train.callback import ModelCheckpoint
from mindspore.train.callback._checkpoint import _chg_ckpt_file_name_if_same_exist
from mindspore import save_checkpoint


def _save_final_ckpt(instance, func):
    """
    Decorator function, which saves the current checkpoint when an exception occurs during training.
    Implement by mindspore, custom feature can be added here.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        obj = None
        if kwargs.get('callbacks') and isinstance(kwargs.get('callbacks'), ModelCheckpoint):
            obj = kwargs.get('callbacks')
        if kwargs.get('callbacks') and isinstance(kwargs.get('callbacks'), list):
            for item in kwargs.get('callbacks'):
                if isinstance(item, ModelCheckpoint):
                    obj = item
        if obj and obj._config and obj._config.exception_save:
            try:
                func(instance, *args, **kwargs)
            except BaseException as e:
                prefix = _chg_ckpt_file_name_if_same_exist(obj._directory, obj._exception_prefix, True)
                cur_ckpoint_file = prefix + "-" + str(instance._current_epoch_num) + "_" \
                                   + str(instance._current_step_num) + "_breakpoint.ckpt"
                cur_file = os.path.join(obj._directory, cur_ckpoint_file)
                if "epoch_num" in obj._append_dict:
                    obj._append_dict["epoch_num"] = obj._append_epoch_num + instance._current_epoch_num
                if "step_num" in obj._append_dict:
                    obj._append_dict["step_num"] = obj._append_step_num + instance._current_step_num
                save_checkpoint(instance._train_network, cur_file, obj._config.integrated_save, obj._config.async_save,
                                obj._append_dict, obj._config.enc_key, obj._config.enc_mode)
                raise e
        else:
            func(instance, *args, **kwargs)

    return wrapper
