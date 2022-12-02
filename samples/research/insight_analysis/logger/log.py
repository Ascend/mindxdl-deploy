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
import logging.config
import os
import yaml

from config import path
from constants.constants import LOG_PRIVILEGE
from constants.constants import LOG_DIR_PRIVILEGE
from constants.constants import MODELARTS_HOME_DIR
from constants.constants import MAX_SIZE
from validator.validators import FileValidator
from validator.validators import DirectoryValidator


def init_sys_log():
    is_modelarts = is_running_over_modelarts_platform()
    config_path = path.LOG_CFG_FILE_FOR_MODELARTS if is_modelarts else path.LOG_CFG_FILE
    real_config_path = os.path.realpath(config_path)
    if real_config_path != config_path:
        raise ValueError("Config path not correct.")

    if not FileValidator(real_config_path).check_file_size().check().is_valid():
        raise ValueError("Config file size is not valid.")

    with open(real_config_path, 'r', encoding='UTF-8') as fp:
        data = fp.read(MAX_SIZE)
        log_cfg = yaml.safe_load(data)

    if not is_modelarts:
        init_log_dir_for_dt(log_cfg)

    logging.config.dictConfig(log_cfg)


def is_running_over_modelarts_platform() -> bool:
    """Check whether running over modelarts.

    """
    return os.path.exists(os.path.realpath(MODELARTS_HOME_DIR))


def init_log_dir_for_dt(log_cfg):
    """Create log directory.

    :param log_cfg: log configuration dictionary from yml file.
    :return: None
    """
    handlers = log_cfg.get('handlers')
    if not handlers:
        return

    for handler_name in handlers:
        handler_dict = handlers.get(handler_name)
        log_file = handler_dict.get('filename')

        if not log_file:
            continue

        log_file_standard = os.path.realpath(log_file)
        if log_file_standard != log_file:
            continue

        log_dir = os.path.dirname(log_file_standard)
        if not DirectoryValidator(log_dir) \
                .check_is_not_none() \
                .check_dir_name() \
                .should_not_contains_sensitive_words() \
                .with_blacklist() \
                .check() \
                .is_valid():
            continue

        _process_log(log_dir)


def _process_log(log_dir: str) -> None:
    """
    Create or check run log and service log file
    :param log_dir: log directory
    :return: None
    """
    os.makedirs(log_dir, mode=LOG_DIR_PRIVILEGE, exist_ok=True)
    run_log_path = os.path.join(log_dir, "run.log")
    if run_log_path != "/var/log/mindx-dl/elastic/run.log":
        raise ValueError("Run log file path is not correct.")
    if not os.path.exists(run_log_path):
        os.mknod(os.path.join(log_dir, "run.log"), mode=LOG_PRIVILEGE)
    else:
        _exist_file_process(run_log_path)
    service_log_path = os.path.join(log_dir, "service.log")
    if service_log_path != "/var/log/mindx-dl/elastic/service.log":
        raise ValueError("Service log file path is not correct.")
    if not os.path.exists(service_log_path):
        os.mknod(os.path.join(log_dir, "service.log"), mode=LOG_PRIVILEGE)
    else:
        _exist_file_process(service_log_path)
    os.chmod(log_dir, LOG_DIR_PRIVILEGE)


def _exist_file_process(log_path: str) -> None:
    """
    Handle log file when file is already existed.
    :param log_path: log file path
    :return: None
    """
    # check is soft link or not
    if not FileValidator(log_path).check_not_soft_link().check().is_valid():
        raise ValueError("Run log file path is a soft link.")

    # check process user and group with log file
    if not FileValidator(log_path).check_user_group().check().is_valid():
        raise ValueError("Invalid run log file permissions.")

    # check log file permission
    os.chmod(log_path, LOG_PRIVILEGE)


init_sys_log()

srv_log = logging.getLogger("logService")
run_log = logging.getLogger("logRun")
