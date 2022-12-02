#!/usr/bin/python3
# -*- coding: utf-8 -*-
# Copyright 2021 Huawei Technologies Co., Ltd
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
import enum

RANK_SIZE_PER_DEVICE = 8
MIN_RANK_SIZE = 0
MAX_RANK_SIZE = 4095
TOLERANCE_TIME = 5
MAX_CKPT_NUMS = 4096
MAX_RANK_STRING_LENGTH = 15274
MIN_RANK_STRING_LENGTH = 1

MAX_FILE_PATH_LENGTH = 4096
MAX_FILE_NAME_LENGTH = 255
MIN_FILE_NAME_LENGTH = 1
MAX_REPLICAS_NUM = 5
MIN_REPLICAS_NUM = 1
STANDARD_NPU_IN_NODE = 8
MIN_DEVICE_NUM = 1
MAX_DEVICE_NUM = 4096
MAX_SIZE = 1024 * 1024
MIN_SIZE = 0

FAULT_RANKS_SEP = "fault-config-"
FAULT_RANK_CONFIG = "/user/restore/fault/config"
FAULT_NPU_FILE = "fault-npus"
FAULT_CHECK_CODE = "checkCode"
DEFAULT_STRATEGY_INPUT_ENV = "GROUP_INFO_FILE"
DEFAULT_JOB_NAMESPACE = "vcjob"

NAMESPACE_PATTERN = "^[a-z0-9]([-a-z0-9]{0,48}[a-z0-9])?$"

LOG_PRIVILEGE = 0o640
LOG_DIR_PRIVILEGE = 0o750

MODELARTS_HOME_DIR = "/home/ma-user"


class FaultRanksPlatform(enum.Enum):
    """
    Platform use fault tolerance function.
    Only ModelArts and MindX DL supported.
    """
    MODELARTS = "ModelArts"
    MINDXDL = "MindX DL"
