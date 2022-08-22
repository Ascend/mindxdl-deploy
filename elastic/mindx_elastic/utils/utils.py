#!/usr/bin/python3
# -*- coding: utf-8 -*-
#   Copyright (C)  2022. Huawei Technologies Co., Ltd. All rights reserved.
import os

import mindspore.communication.management as D
import mindspore.context as context

from mindx_elastic.logger.log import run_log


def get_device_num() -> int:
    """
    Get device num used for current training task
    """
    D.init()
    return D.get_group_size()


def get_device_id() -> int:
    """
    Get device id used for current training task
    """
    D.init()
    return D.get_rank()