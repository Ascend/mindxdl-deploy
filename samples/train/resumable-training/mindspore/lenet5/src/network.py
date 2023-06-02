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
"""LeNet."""

import time

import mindspore.nn as nn
import mindspore.ops as ops
from mindspore import Tensor
from mindspore.common import dtype as mstype
from mindspore.common.initializer import Normal
from mindspore.train.callback import Callback


class LeNet5(nn.Cell):
    """
    LeNet network structure
    """

    def __init__(self, num_class=10, num_channel=1):
        super(LeNet5, self).__init__()
        self.conv1 = nn.Conv2d(num_channel, 6, 5, pad_mode='valid')
        self.conv2 = nn.Conv2d(6, 16, 5, pad_mode='valid')
        self.fc1 = nn.Dense(16 * 5 * 5, 120, weight_init=Normal(0.02))
        self.fc2 = nn.Dense(120, 84, weight_init=Normal(0.02))
        self.fc3 = nn.Dense(84, num_class, weight_init=Normal(0.02))
        self.relu = nn.ReLU()
        self.max_pool2d = nn.MaxPool2d(kernel_size=2, stride=2)
        self.flatten = nn.Flatten()

    def construct(self, x):
        x = self.max_pool2d(self.relu(self.conv1(x)))
        x = self.max_pool2d(self.relu(self.conv2(x)))
        x = self.flatten(x)
        x = self.relu(self.fc1(x))
        x = self.relu(self.fc2(x))
        x = self.fc3(x)
        return x


class PerformanceCallback(Callback):
    """
    Training performance callback.

    Args:
        batch_size (int): Batch number for one step.
        device_num (int): Device number.
    """

    def __init__(self, batch_size, device_num):
        super(PerformanceCallback, self).__init__()
        self.batch_size = batch_size
        self.device_num = device_num
        self.last_step = 0
        self.epoch_begin_time = 0

    def step_begin(self, run_context):
        self.epoch_begin_time = time.time()

    def step_end(self, run_context):
        params = run_context.original_args()
        cost_time = time.time() - self.epoch_begin_time
        train_steps = params.cur_step_num - self.last_step
        one_step_time = 1000 * cost_time / train_steps
        clu_speed = self.device_num * train_steps * self.batch_size / cost_time
        print(f'epoch {params.cur_epoch_num} cost time = {cost_time}, '
              f'train step num: {train_steps}, one step time: {one_step_time} '
              f'ms, train samples per second of cluster: {clu_speed:.1f}\n')
        self.last_step = run_context.original_args().cur_step_num


class SoftmaxCrossEntropyExpand(nn.Cell):
    """
    Define loss function
    """

    def __init__(self, sparse=False):
        super(SoftmaxCrossEntropyExpand, self).__init__()
        self.exp = ops.Exp()
        self.sum = ops.ReduceSum(keep_dims=True)
        self.onehot = ops.OneHot()
        self.on_value = Tensor(1.0, mstype.float32)
        self.off_value = Tensor(0.0, mstype.float32)
        self.div = ops.RealDiv()
        self.log = ops.Log()
        self.sum_cross_entropy = ops.ReduceSum(keep_dims=False)
        self.mul = ops.Mul()
        self.mul2 = ops.Mul()
        self.mean = ops.ReduceMean(keep_dims=False)
        self.sparse = sparse
        self.max = ops.ReduceMax(keep_dims=True)
        self.sub = ops.Sub()

    def construct(self, logit, label):
        logit_max = self.max(logit, -1)
        exp = self.exp(self.sub(logit, logit_max))
        exp_sum = self.sum(exp, -1)
        softmax_result = self.div(exp, exp_sum)
        if self.sparse:
            label = self.onehot(label, ops.shape(logit)[1], self.on_value,
                                self.off_value)
        softmax_result_log = self.log(softmax_result)
        loss = self.sum_cross_entropy((self.mul(softmax_result_log, label)),
                                      -1)
        loss = self.mul2(ops.scalar_to_array(-1.0), loss)
        loss = self.mean(loss, -1)

        return loss
