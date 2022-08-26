#!/usr/bin/python3
# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2022. All rights reserved.
RANK_SIZE_PER_DEVICE = 8
MIN_RANK_SIZE = 0
MAX_RANK_SIZE = 4095
TOLERANCE_TIME = 5
MAX_CKPT_NUMS = 10000
MAX_RANK_STRING_LENGTH = 15274

FAULT_RANKS_SEP = "fault-config-"
JOB_ID_ENV = "mindx-dls-test"
FAULT_RANK_CONFIG = "/user/restore/fault/config"
FAULT_NPU_FILE = "fault-npus"
DEFAULT_STRATEGY_INPUT_ENV = "GROUP_INFO_FILE"
DEFAULT_JOB_NAMESPACE = "vcjob"

NAMESPACE_PATTERN = "^[a-z0-9]([-a-z0-9]{0,48}[a-z0-9])?$"
JOB_ID_PATTERN = "^[a-z0-9][-a-z0-9]{0,61}[a-z0-9]$"

LOG_PRIVILEGE = 0o640
LOG_DIR_PRIVILEGE = 0o750

MODELARTS_HOME_DIR = "/home/ma-user"


