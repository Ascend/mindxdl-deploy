#!/usr/bin/python
# -*- coding: utf-8 -*-

#  Copyright (C)  2022. Huawei Technologies Co., Ltd. All rights reserved.
import logging.config
import os
import platform
import yaml

from mindx_elastic.config import path
from mindx_elastic.constants.constants import LOG_PRIVILEGE, LOG_DIR_PRIVILEGE, MODELARTS_HOME_DIR


def init_sys_log():
    is_modelarts = is_running_over_modelarts_platform()
    config_path = path.LOG_CFG_FILE_FOR_MODELARTS if is_modelarts else path.LOG_CFG_FILE
    real_config_path = os.path.realpath(config_path)
    if not is_modelarts and real_config_path != config_path:
        raise ValueError("Invalid log config file path!")

    with open(real_config_path, 'r', encoding='UTF-8') as fp:
        data = fp.read()
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
        if "windows" in platform.system().lower():
            cur_drive = f'{os.getcwd().split(":")[0]} + ":\\"'
            win_log_dir = os.path.join(cur_drive, *log_dir.split('/'))
            if not os.path.exists(win_log_dir):
                os.makedirs(win_log_dir)
        else:
            os.makedirs(log_dir, mode=LOG_DIR_PRIVILEGE, exist_ok=True)
            run_log_path = os.path.join(log_dir, "run.log")
            if not os.path.exists(run_log_path):
                os.mknod(os.path.join(log_dir, "run.log"), mode=LOG_PRIVILEGE)

            service_log_path = os.path.join(log_dir, "service.log")
            if not os.path.exists(service_log_path):
                os.mknod(os.path.join(log_dir, "service.log"), mode=LOG_PRIVILEGE)


init_sys_log()

srv_log = logging.getLogger("logService")
run_log = logging.getLogger("logRun")
