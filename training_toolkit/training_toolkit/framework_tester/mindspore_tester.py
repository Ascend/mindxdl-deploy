#!/usr/bin/python3
# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2022. All rights reserved.

import os
import signal

import mindspore as ms
import numpy as np
from mindspore import nn
from mindspore.dataset import GeneratorDataset
from mindspore import Model
from mindspore.common.initializer import Normal
from mindspore.train.callback import LossMonitor
from mindspore.communication import init, get_rank, get_group_size

from training_toolkit.framework_tester.pseudo_data import gen_linear_regression_data
from training_toolkit.config.config import DEVICE_ID_ENV_KEY, MAX_CHIP_ONE_NODE


def receive_signal(signum, stack):
    print(f"It's mindspore {os.getpid()}, received signal {signum}")
    exit(signum)


class MindSporeDataset:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __getitem__(self, item):
        return np.asarray([self.x[item]], dtype=np.float32), np.asarray([self.y[item]], dtype=np.float32)

    def __len__(self):
        return len(self.x)


class LinearNet(nn.Cell):
    def __init__(self):
        super(LinearNet, self).__init__()
        self.fc = nn.Dense(1, 1, Normal(0.02), Normal(0.02))

    def construct(self, x):
        return self.fc(x)


def mindspore_train():
    signal.signal(signal.SIGTERM, receive_signal)
    signal.signal(signal.SIGINT, receive_signal)
    device_id = os.environ[DEVICE_ID_ENV_KEY]
    ms.set_context(mode=ms.GRAPH_MODE, device_target="Ascend", device_id=int(device_id))
    init()
    ms.set_auto_parallel_context(parallel_mode=ms.ParallelMode.DATA_PARALLEL, parameter_broadcast=True)

    rank_id = get_rank()
    group_size = get_group_size()

    node_num = group_size // MAX_CHIP_ONE_NODE

    data_num = 10000 * node_num
    k = 2
    b = 3
    derivation = 1

    train, label = gen_linear_regression_data(data_num, k, b, derivation)

    dataset = GeneratorDataset(source=MindSporeDataset(train, label),
                               column_names=["data", "label"],
                               num_shards=group_size, shard_id=rank_id)

    dataset = dataset.batch(32 * node_num)
    model = LinearNet()
    loss_fn = nn.MSELoss()
    optimizer = nn.Adam(model.trainable_params())

    epoch_num = 120 * node_num
    print(f"pid: {os.getpid()}, rank id: {rank_id}, device id: {device_id}, group size: {group_size}, "
          f"data num: {data_num}, epoch: {epoch_num}")

    trainer = Model(network=model, loss_fn=loss_fn, optimizer=optimizer)
    trainer.train(epoch=epoch_num, train_dataset=dataset, callbacks=[LossMonitor(per_print_times=100)])


if __name__ == "__main__":
    mindspore_train()
