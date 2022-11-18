#!/usr/bin/python
# -*- coding: utf-8 -*-

#  Copyright (C)  2022. Huawei Technologies Co., Ltd. All rights reserved.
import logging.config
import os
import platform

from training_toolkit.config.config import LOG_PRIVILEGE, LOG_DIR_PRIVILEGE

LOG_CONFIG_DICT = {
    "version": 1,
    "formatters": {
        "simpleFmt": {
            "format": "[%(asctime)s][%(levelname)s][%(message)s]"
        },
        "wholeFmt": {
            "format": "[%(asctime)s][%(levelname)s][%(message)s][%(filename)s, %(funcName)s:%(lineno)d][%(process)d, %(thread)d]"
        }
    },
    "handlers": {
        "srvHandler": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "INFO",
            "formatter": "wholeFmt",
            "filename": "/var/log/mindx-dl/training_toolkit/service.log",
            "maxBytes": 20971520,
            "backupCount": 8,
            "encoding": "utf-8",
        },
        "runHandler": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "INFO",
            "formatter": "simpleFmt",
            "filename": "/var/log/mindx-dl/training_toolkit/run.log",
            "maxBytes": 20971520,
            "backupCount": 8,
            "encoding": "utf-8",
        },
        "streamHandler": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "simpleFmt",
            "stream": "ext://sys.stdout"
        }
    },
    "loggers": {
        "logService": {
            "handlers": ["srvHandler"],
            "level": "INFO",
            "propagate": False,
        },
        "logRun": {
            "handlers": ["runHandler", "srvHandler", "streamHandler"],
            "level": "INFO",
            "propagate": False,
        },
    }
}


def init_sys_log():
    init_log_dir_for_dt(LOG_CONFIG_DICT)
    logging.config.dictConfig(LOG_CONFIG_DICT)


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
                os.chmod(win_log_dir, LOG_PRIVILEGE)
        else:
            os.makedirs(log_dir, mode=LOG_DIR_PRIVILEGE, exist_ok=True)
            run_log_path = os.path.join(log_dir, "run.log")
            if not os.path.exists(run_log_path):
                os.mknod(os.path.join(log_dir, "run.log"), mode=LOG_PRIVILEGE)
            else:
                os.chmod(run_log_path, LOG_PRIVILEGE)

            service_log_path = os.path.join(log_dir, "service.log")
            if not os.path.exists(service_log_path):
                os.mknod(os.path.join(log_dir, "service.log"), mode=LOG_PRIVILEGE)
            else:
                os.chmod(service_log_path, LOG_PRIVILEGE)
        os.chmod(log_dir, LOG_DIR_PRIVILEGE)


init_sys_log()

srv_log = logging.getLogger("logService")
run_log = logging.getLogger("logRun")
