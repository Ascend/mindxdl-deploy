import os
import re
import platform
import socket

from training_toolkit.config import config
from training_toolkit.logger.log import run_log

path_pattern = re.compile(r"\${(.+)}/(.+)")
wrap_pattern = re.compile(r"\${(.+)}")


def get_host_ip(use_env=True) -> str:
    """
    get host ip from k8s yaml environment variables setting. Env key is "XDL_IP" by default.
    Or from socket function
    Args:
        use_env:

    Returns:

    """
    if use_env:
        host_ip = os.environ.get(config.HOST_UP_ENV_KEY, "")
        if host_ip == "":
            msg = f"get host ip for current node failed, please check k8s yaml env ocnfig ({config.HOST_UP_ENV_KEY})."
            run_log.error(msg)
            raise ValueError(msg)
    else:
        host_ip = socket.gethostbyname(socket.gethostname())
    return host_ip


def parse_env_path(env_path: str) -> list:
    """
    parse env path of export command
    Args:
        env_path:

    Returns:

    """
    path_list = []
    for p in env_path.split(":"):
        if not p:
            continue

        re_result = path_pattern.search(p)
        if re_result is not None:
            env_value = os.environ.get(re_result.group(1), "")
            if not env_value:
                continue
            sub = re_result.group(2)
            path_list.append(os.path.join(env_value, sub))
            continue

        if p.startswith("$"):
            wrap_result = wrap_pattern.search(p)
            if wrap_result is not None:
                old_env_path = os.environ.get(wrap_result.group(1), "")
            else:
                old_env_path = os.environ.get(p[1:], "")
            path_list.extend(parse_env_path(old_env_path))
            continue

        path_list.append(p)

    return path_list


def parse_export_and_add_env(export_script_path: str):
    """

    Args:
        export_script_path: bash script to set environment variables

    Returns:

    """
    with open(export_script_path, "r", encoding="utf-8") as f:
        for line in f:
            content = line.strip()
            if not content or not content.startswith("export"):
                continue
            _, env_text = content.split()
            env_key, env_path = env_text.split("=", maxsplit=1)

            deduplicate_path_set = set(parse_env_path(env_path))
            os.environ[env_key] = ":".join(deduplicate_path_set)


def add_one_env_path(env_key, path, env=None, insert_head=False):
    tmp_env = env if env is not None else os.environ
    raw = tmp_env.get(env_key, "").split(":")
    if path in raw:
        return
    if insert_head:
        new = ":".join([path] + raw)
    else:
        new = ":".join(raw + [path])
    tmp_env[env_key] = new


def add_extra_env(env_path: str):
    add_one_env_path(config.LD_LIBRARY_PATH_ENV_KEY, "/usr/local/")
    add_one_env_path(config.LD_LIBRARY_PATH_ENV_KEY, "/usr/local/python3.7.5/lib/")
    add_one_env_path(config.LD_LIBRARY_PATH_ENV_KEY, "/usr/local/openblas/lib/")
    add_one_env_path(config.LD_LIBRARY_PATH_ENV_KEY, "/usr/local/lib/")
    add_one_env_path(config.LD_LIBRARY_PATH_ENV_KEY, "/usr/lib64/")
    add_one_env_path(config.LD_LIBRARY_PATH_ENV_KEY, "/usr/lib/")

    if env_path == config.ASCEND_NNAE_DEFAULT_SET_ENV_PATH:
        target_path = config.ASCEND_NNAE_DEFAULT_INSTALL_PATH
        add_one_env_path(config.LD_LIBRARY_PATH_ENV_KEY, "/usr/lib/aarch64_64-linux-gnu")
    else:
        target_path = config.ASCEND_TOOLKIT_DEFAULT_INSTALL_PATH
        cpu_type = platform.uname().processor
        type_name = ""
        if cpu_type == "aarch64":
            type_name = "arm64-linux"
        if cpu_type == "x86_64":
            type_name = "x86_64-linux"

        if not type_name:
            run_log.warning(f"not support cpu arch (x86_64 and aarch64): {cpu_type}, maybe not work.")

        add_one_env_path(config.LD_LIBRARY_PATH_ENV_KEY, "/usr/local/Ascend/add-ons")
        add_one_env_path(config.LD_LIBRARY_PATH_ENV_KEY, "/usr/lib/aarch64-linux-gnu")
        add_one_env_path(config.ASCEND_AICPU_PATH_ENV_KEY,
                         f"{config.ASCEND_TOOLKIT_DEFAULT_INSTALL_PATH}/latest/{type_name}")

    # Pytorch
    add_one_env_path(config.LD_LIBRARY_PATH_ENV_KEY, f"{target_path}/latest/fwkacllib/lib64/")
    add_one_env_path(config.PATH_ENV_KEY, f"{target_path}/latest/fwkacllib/ccec_compiler/bin/")
    add_one_env_path(config.PATH_ENV_KEY, f"{target_path}/latest/toolkit/tools/ide_daemon/bin/")
    add_one_env_path(config.OPTION_EXEC_EXTERN_PLUGIN_PATH_ENV_KEY,
                     f"{target_path}/latest/fwkacllib/lib64/plugin/opskernel/libfe.so")
    add_one_env_path(config.OPTION_EXEC_EXTERN_PLUGIN_PATH_ENV_KEY,
                     f"{target_path}/latest/fwkacllib/lib64/plugin/opskernel/libaicpu_engine.so")
    add_one_env_path(config.OPTION_EXEC_EXTERN_PLUGIN_PATH_ENV_KEY,
                     f"{target_path}/latest/fwkacllib/lib64/plugin/opskernel/libge_local_engine.so")
    add_one_env_path(config.PYTHONPATH_ENV_KEY, f"{target_path}/latest/fwkacllib/python/site-packages/")
    add_one_env_path(config.PYTHONPATH_ENV_KEY,
                     f"{target_path}/latest/fwkacllib/python/site-packages/auto_tune.egg/auto_tune")
    add_one_env_path(config.PYTHONPATH_ENV_KEY,
                     f"{target_path}/latest/fwkacllib/python/site-packages/schedule_search.egg")


def substitute_arg_with_env(args: str, envs: dict):
    for k, v in envs.items():
        args = args.replace(f"%{k}%", v)
    return args
