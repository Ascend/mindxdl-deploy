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

import argparse
import os

from mindspore import context
from mindspore.communication.management import get_rank
from mindspore.communication.management import init
from mindspore.context import ParallelMode
from mindspore.nn.optim.momentum import Momentum
from mindspore.train import Model
from mindspore.train.callback import CheckpointConfig
from mindspore.train.callback import LossMonitor
from mindspore.train.callback import ModelCheckpoint

from src.config import mnist_cfg as config
from src.dataset import create_dataset
from src.network import LeNet5
from src.network import PerformanceCallback
from src.network import SoftmaxCrossEntropyExpand

parser = argparse.ArgumentParser(description="Mnist")
parser.add_argument('--ckpt_save_path', type=str, default='./ckpt',
                    help='Save the checkpoint path')
parser.add_argument('--dataset_path', type=str, default='./MNIST_Data',
                    help='Dataset path')
args_opt = parser.parse_args()


def train_and_eval_net():
    print("================ Starting Training ================")
    device_id = int(os.getenv('DEVICE_ID'))
    device_num = int(os.getenv('RANK_SIZE'))
    context.set_context(mode=context.GRAPH_MODE, device_target="Ascend")
    context.set_context(device_id=device_id)
    print(f"device_num: {device_num}")
    if device_num > 1:
        context.set_auto_parallel_context(
            device_num=device_num,
            parallel_mode=ParallelMode.DATA_PARALLEL,
            gradients_mean=True)
        init()

    # create dataset
    print("Create train and evaluate dataset.")
    ds_train = create_dataset(os.path.join(args_opt.dataset_path, "train"),
                              device_num, config.batch_size,
                              config.repeat_size)
    ds_eval = create_dataset(os.path.join(args_opt.dataset_path, "test"),
                             device_num, is_training=False)
    train_step_size = ds_train.get_dataset_size()
    print("Create dataset success.")

    if device_num > 1:
        ckpt_save_dir = "{}{}/".format(args_opt.ckpt_save_path,
                                       str(get_rank()))
        prefix = "data_parallel"
    else:
        ckpt_save_dir = "{}/".format(args_opt.ckpt_save_path)
        prefix = "single"

    # create model
    network = LeNet5()
    loss = SoftmaxCrossEntropyExpand(sparse=True)
    # optimizer
    opt = Momentum(filter(lambda x: x.requires_grad, network.get_parameters()),
                   config.lr, config.momentum)
    model = Model(network, loss_fn=loss, optimizer=opt, metrics={'acc'})
    performance_cb = PerformanceCallback(config.batch_size, device_num)
    loss_cb = LossMonitor()
    # set parameter of checkpoint
    ckpt_config = CheckpointConfig(
        save_checkpoint_steps=config.save_checkpoint_epochs * train_step_size,
        keep_checkpoint_max=config.keep_checkpoint_max)

    # apply parameter of checkpoint
    ckpt_callback = ModelCheckpoint(prefix=prefix, directory=ckpt_save_dir,
                                    config=ckpt_config)
    cb = [loss_cb, performance_cb, ckpt_callback]
    print(f"Start run training, total epoch: {config.epoch_size}.")
    model.train(config.epoch_size, ds_train, callbacks=cb,
                dataset_sink_mode=True)
    if device_num == 1 or device_id == 0:
        print("================ Starting Testing ================")
        acc = model.eval(ds_eval)
        print(f"================ Accuracy: {acc} ================")


if __name__ == "__main__":
    # train and eval
    train_and_eval_net()
