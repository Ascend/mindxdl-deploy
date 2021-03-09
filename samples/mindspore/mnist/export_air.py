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
import sys

import numpy as np
from mindspore import Tensor
from mindspore import export
from mindspore import load_checkpoint

from src.network import LeNet5

parser = argparse.ArgumentParser(description='MNIST Export Model Example')
parser.add_argument("--ckpt_path", type=str, default=None,
                    help="The checkpoint path.")
parser.add_argument("--file_name", type=str, default="mnist",
                    help="output file name.")
parser.add_argument("--file_format", type=str,
                    choices=["AIR", "ONNX", "MINDIR"],
                    default="AIR", help="file format")
args = parser.parse_args()


def main():
    network = LeNet5()
    # load the parameter into net
    load_checkpoint(args.ckpt_path, net=network)
    input_x = np.random.uniform(0.0, 1.0,
                                size=[1, 1, 32, 32]).astype(np.float32)
    export(network, Tensor(input_x), file_name=args.file_name,
           file_format=args.file_format)


if __name__ == "__main__":
    if not args.ckpt_path:
        print("The checkpoint file path is none.")
        sys.exit(1)
    main()
