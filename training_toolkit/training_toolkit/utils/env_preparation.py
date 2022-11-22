import os
import sys
import re

from training_toolkit.utils.ranktable import RankTable
from training_toolkit.config import config
from training_toolkit.logger.log import run_log
from training_toolkit.utils.common import add_extra_env, parse_export_and_add_env, add_one_env_path, get_host_ip
from training_toolkit.utils.validator import IPValidator, RangeValidator, IntValidator, MultiplicationValidator


def set_dependence_env():
    """
    load environment variables of Ascend related software like NNAE, Toolkit, TFPlugin.
    Returns:
    """
    set_training_env_done = False
    if os.path.exists(config.ASCEND_TOOLKIT_DEFAULT_SET_ENV_PATH):
        add_extra_env(config.ASCEND_TOOLKIT_DEFAULT_SET_ENV_PATH)
        parse_export_and_add_env(config.ASCEND_TOOLKIT_DEFAULT_SET_ENV_PATH)
        set_training_env_done = True
        run_log.info(f"set env succuss with file: {config.ASCEND_TOOLKIT_DEFAULT_SET_ENV_PATH}")
    elif os.path.exists(config.ASCEND_NNAE_DEFAULT_SET_ENV_PATH):
        add_extra_env(config.ASCEND_NNAE_DEFAULT_SET_ENV_PATH)
        parse_export_and_add_env(config.ASCEND_NNAE_DEFAULT_SET_ENV_PATH)
        set_training_env_done = True
        run_log.info(f"set env succuss with file: {config.ASCEND_NNAE_DEFAULT_SET_ENV_PATH}")

    if not set_training_env_done:
        run_log.warning(f"not set env in file: {config.ASCEND_NNAE_DEFAULT_SET_ENV_PATH} or "
                        f"{config.ASCEND_TOOLKIT_DEFAULT_SET_ENV_PATH}, please check the env has been already manually"
                        f"set properly")

    if os.path.exists(config.ASCEND_TF_PLUGIN_DEFAULT_SET_ENV_PATH):
        parse_export_and_add_env(config.ASCEND_TF_PLUGIN_DEFAULT_SET_ENV_PATH)
        run_log.info(f"set env success with file: {config.ASCEND_TF_PLUGIN_DEFAULT_SET_ENV_PATH}")


def is_tf_env_correctly_configured() -> bool:
    """
    check tf required env whether configured or not at mode without ranktable
    Returns:
    """

    needed_env = [config.CM_CHIEF_IP_ENV_KEY, config.CM_CHIEF_PORT_ENV_KEY, config.CM_CHIEF_DEVICE_ENV_KEY,
                  config.CM_WORKER_IP_ENV_KEY, config.CM_WORKER_SIZE_ENV_KEY]
    for e in needed_env:
        if e not in os.environ:
            run_log.error(f"env: {e} not set. Can't fun TF training task. Required env: {','.join(needed_env)}")
            return False

    if not IPValidator().validate(os.environ[config.CM_CHIEF_IP_ENV_KEY]):
        return False

    if not IPValidator().validate(os.environ[config.CM_WORKER_IP_ENV_KEY]):
        return False

    port_validate_chain = IntValidator()
    port_validate_chain.set_next(RangeValidator(0, 65536))
    if not port_validate_chain.validate(os.environ[config.CM_CHIEF_PORT_ENV_KEY]):
        return False

    device_validate_chain = IntValidator()
    device_validate_chain.set_next(RangeValidator(0, 7))
    if not device_validate_chain.validate(os.environ[config.CM_CHIEF_DEVICE_ENV_KEY]):
        return False

    size_validate_chain = IntValidator()
    size_validate_chain. \
        set_next(RangeValidator(1, config.MAX_RANK_SIZE)). \
        set_next(MultiplicationValidator(config.MAX_CHIP_ONE_NODE))
    if not size_validate_chain.validate(os.environ[config.CM_WORKER_SIZE_ENV_KEY]):
        return False


def get_cluster_info_from_tf_env():
    device_num = int(os.environ[config.CM_WORKER_SIZE_ENV_KEY])
    master_ip = os.environ[config.CM_CHIEF_IP_ENV_KEY]
    node_num = 1 if device_num <= config.MAX_CHIP_ONE_NODE else device_num // config.MAX_CHIP_ONE_NODE
    return master_ip, device_num, node_num


def is_pt_env_correctly_configured() -> bool:
    """
    check pt required env if configured or not at mode without rantable
    Returns:

    """
    needed_env = [
        config.PYTORCH_MASTER_IP_ENV_KEY,
        config.PYTORCH_RANK_ENV_KEY,
        config.PYTORCH_WORLD_SIZE_ENV_KEY
    ]

    for e in needed_env:
        if e not in os.environ:
            run_log.error(f"env: {e} not set. Can't fun PT training task. Required env: {','.join(needed_env)}")

    if not IPValidator().validate(os.environ[config.PYTORCH_MASTER_IP_ENV_KEY]):
        return False

    rank_validate_chain = IntValidator()
    rank_validate_chain. \
        set_next(RangeValidator(0, config.MAX_RANK_SIZE // config.MAX_CHIP_ONE_NODE - 1))
    if not rank_validate_chain.validate(os.environ[config.PYTORCH_RANK_ENV_KEY]):
        return False

    size_validate_chain = IntValidator()
    size_validate_chain. \
        set_next(RangeValidator(1, config.MAX_RANK_SIZE)). \
        set_next(MultiplicationValidator(config.MAX_CHIP_ONE_NODE))
    if not size_validate_chain.validate(os.environ[config.PYTORCH_WORLD_SIZE_ENV_KEY]):
        return False

    return True


def get_cluster_info_from_pt_env():
    device_num = int(os.environ[config.PYTORCH_WORLD_SIZE_ENV_KEY])
    master_ip = os.environ[config.PYTORCH_MASTER_IP_ENV_KEY]
    node_num = 1 if device_num <= config.MAX_CHIP_ONE_NODE else device_num // config.MAX_CHIP_ONE_NODE
    return master_ip, device_num, node_num


def preparation_for_scenario_without_ranktable(args) -> tuple:
    run_log.info("run without ranktable: only support TensorFlow and Pytorch for now")
    allowed_platforms = [config.PlatformType.TensorFlow.value, config.PlatformType.Pytorch.vaue]
    if args.platform not in allowed_platforms:
        run_log.error(f"{args.platform} is selected, exit")

    master_ip = ""
    device_num = -1
    node_num = -1
    if args.platform == config.PlatformType.TensorFlow.value:
        if not is_tf_env_correctly_configured():
            run_log.error("please check env setting")
            return False, "", -1, -1
        master_ip, device_num, node_num = get_cluster_info_from_tf_env()

    if args.platform == config.PlatformType.Pytorch.value:
        if not is_pt_env_correctly_configured():
            run_log.error("please check env setting")
            return False, "", -1, -1
        master_ip, device_num, node_num = get_cluster_info_from_pt_env()

    return True, master_ip, device_num, node_num


def preparation_for_scenario_with_ranktable() -> tuple:
    rank_table = RankTable()
    rank_table.wait_for_complete()
    device_num = rank_table.get_total_device_num()
    server_info = rank_table.get_current_server_info()
    node_num = rank_table.get_server_count()
    master_ip = rank_table.get_master_ip()
    if server_info is None:
        return False, "", -1, -1, None
    run_log.info(f"current server info -> {server_info}")
    return True, master_ip, device_num, node_num, server_info


def get_device_rank_str(device_num) -> str:
    if device_num >= 8 and device_num % 8 == 0:
        return "0,1,2,3,4,5,6,7"
    elif device_num == 4:
        return "0,1,2,3"
    elif device_num == 2:
        return "0,1"
    elif device_num == 1:
        return "0"
    else:
        msg = f"device num is: {device_num}, only 1,2,4,8 or n*8 are supported"
        run_log.error(msg)
        raise ValueError(msg)


def set_tensorflow_env():
    os.environ[config.JOB_ID_ENV_KEY] = os.environ.get(config.JOB_ID_ENV_KEY, "123456789")


def set_pytorch_env(master_ip, server_index, device_num):
    os.environ[config.TASK_QUEUE_ENABLE_ENV_KEY] = os.environ.get(config.TASK_QUEUE_ENABLE_ENV_KEY, "1")
    os.environ[config.PYTORCH_MASTER_IP_ENV_KEY] = os.environ.get(config.PYTORCH_MASTER_IP_ENV_KEY, master_ip)
    os.environ[config.PYTORCH_MASTER_PORT_ENV_KEY] = os.environ.get(config.PYTORCH_MASTER_PORT_ENV_KEY,
                                                                    config.PYTORCH_MASTER_PORT_ENV_VALUE)

    os.environ[config.PYTORCH_RANK_ENV_KEY] = os.environ.get(config.PYTORCH_RANK_ENV_KEY, str(server_index))
    os.environ[config.PYTORCH_WORLD_SIZE_ENV_KEY] = os.environ.get(config.PYTORCH_WORLD_SIZE_ENV_KEY,
                                                                   str(device_num))

    os.environ[config.HCCL_WHITELIST_DISABLE_ENV_KEY] = os.environ.get(config.HCCL_WHITELIST_DISABLE_ENV_KEY, "1")
    os.environ[config.HCCL_IF_IP_ENV_KEY] = os.environ.get(config.HCCL_IF_IP_ENV_KEY, get_host_ip())
    os.environ[config.COMBINED_ENBALE_ENV_KEY] = os.environ.get(config.COMBINED_ENBALE_ENV_KEY, "1")
    os.environ[config.DEVICE_RANK_LIST_ENV_KEY] = get_device_rank_str(device_num)
    result = ''
    for index in range(len(sys.path)):
        match_sit = re.search('-packages', sys.path[index])
        if match_sit is not None:
            match_lib = re.search('lib', sys.path[index])
            if match_lib is not None:
                end = match_lib.span()[1]
                result += sys.path[index][0:end] + ':'
            result += os.path.join(sys.path[index], "torch", "lib") + ":"

    for p in result.split(":"):
        add_one_env_path(config.LD_LIBRARY_PATH_ENV_KEY, p, insert_head=True)


def set_task_env(args) -> tuple:
    """
    set general and platform-specific environment variables for training task
    Args:
        args:

    Returns:

    """
    without_rank_table = args.wo_ranktable
    server_info = None
    if without_rank_table:
        ok, master_ip, device_num, node_num = preparation_for_scenario_without_ranktable(args)
    else:
        ok, master_ip, device_num, node_num, server_info = preparation_for_scenario_with_ranktable()

    if not ok:
        return ok, server_info

    os.environ[config.RANK_SIZE_ENV_KEY] = os.environ.get(config.RANK_SIZE_ENV_KEY, str(device_num))
    os.environ[config.NODE_NUM_ENV_KEY] = os.environ.get(config.NODE_NUM_ENV_KEY, str(node_num))
    os.environ[config.PYTHONUNBUFFERED_EN_KEY] = os.environ.get(config.PYTHONUNBUFFERED_EN_KEY, "1")
    os.environ[config.ASCEND_SLOG_PRINT_TO_STDOUT_ENV_KEY] = os.environ.get(config.ASCEND_SLOG_PRINT_TO_STDOUT_ENV_KEY,
                                                                            "0")
    os.environ[config.HCCL_CONNECT_TIMEOUT_ENV_KEY] = os.environ.get(config.HCCL_CONNECT_TIMEOUT_ENV_KEY,
                                                                     config.HCCL_CONNECT_TIMEOUT_ENV_VALUE)
    os.environ[config.HCCL_EXEC_TIMEOUT_ENV_KEY] = os.environ.get(config.HCCL_EXEC_TIMEOUT_ENV_KEY,
                                                                  config.HCCL_EXEC_TIMEOUT_ENV_VALUE)
    add_one_env_path(config.PYTHONPATH_ENV_KEY, os.getcwd(), insert_head=True)

    if args.platform == config.PlatformType.TensorFlow.value:
        set_tensorflow_env()

    if args.platform == config.PlatformType.Pytorch.value:
        server_index = server_info.server_index if server_info is not None else 0
        set_pytorch_env(master_ip, server_index, device_num)

    return ok, server_info
