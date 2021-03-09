# coding: utf-8

# Copyright(C) 2021. Huawei Technologies Co.,Ltd. All rights reserved.
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
"""
Produce the dataset
"""

import mindspore.dataset as ds
import mindspore.dataset.transforms.c_transforms as C
import mindspore.dataset.vision.c_transforms as CV
from mindspore.common import dtype as mstype
from mindspore.communication.management import get_group_size
from mindspore.communication.management import get_rank
from mindspore.dataset.vision import Inter


def create_dataset(data_path, device_num, batch_size=32, repeat_size=1,
                   is_training=True):
    """ create dataset for train or test
    Args:
        data_path: Data path
        device_num: Device number
        batch_size: The number of data records in each group
        repeat_size: The number of replicated data records
        is_training: The flag of train dataset
    """
    # get rank_id and rank_size
    if device_num == 1 or not is_training:
        mnist_ds = ds.MnistDataset(data_path)
    else:
        rank_id = get_rank()
        rank_size = get_group_size()
        mnist_ds = ds.MnistDataset(data_path, num_shards=rank_size,
                                   shard_id=rank_id)

    # define operation parameter
    resize_height, resize_width = 32, 32
    rescale = 1.0 / 255.0
    shift = 0.0
    rescale_nml = 1 / 0.3081
    shift_nml = -1 * 0.1307 / 0.3081

    # define map operations
    resize_op = CV.Resize((resize_height, resize_width),
                          interpolation=Inter.LINEAR)
    # normalize images
    rescale_nml_op = CV.Rescale(rescale_nml, shift_nml)
    # rescale images
    rescale_op = CV.Rescale(rescale, shift)
    # change shape from (h, w, c) to (c, h, w) to fit network.
    hwc2chw_op = CV.HWC2CHW()
    # change data type of label to int32 to fit network
    type_cast_op = C.TypeCast(mstype.int32)
    c_trans = [resize_op, rescale_op, rescale_nml_op, hwc2chw_op]

    # apply map operations on images
    mnist_ds = mnist_ds.map(operations=type_cast_op, input_columns="label")
    mnist_ds = mnist_ds.map(operations=c_trans, input_columns="image")

    # apply DatasetOps
    if is_training:
        buffer_size = 10000
        # 10000 as in LeNet train script
        mnist_ds = mnist_ds.shuffle(buffer_size=buffer_size)
    mnist_ds = mnist_ds.batch(batch_size, drop_remainder=True)
    mnist_ds = mnist_ds.repeat(repeat_size)

    return mnist_ds
