#!/bin/bash
# default start shell path
DLS_USER_HOME_DIR="$(
  cd "$(dirname "$0")" || exit 1
  if [[ $? -eq 1 ]]; then
    exit 1
  fi
  pwd -P
)"
cd "$DLS_USER_HOME_DIR" || exit 1

# set pythonpath(especially for tensorflow)
export PYTHONPATH="$DLS_USER_JOB_DIR:$PYTHONPATH"
export PYTHONUNBUFFERED=1

# use utils.sh env and functions
source utils.sh

# training job input parameters
app_url="$1"
log_url="$2"
boot_file="$3"
shift 3

function show_help() {
  echo "Usage train_start.sh /job/code/resnet50 /tmp/log/training.log train.py"
}

function param_check() {
  if [ -z "${app_url}" ]; then
    echo "please input code dir"
    show_help
    exit 1
  fi

  if [ -z "${boot_file}" ]; then
    echo "please input boot file"
    show_help
    exit 1
  fi

  if [ -z "${log_url}" ]; then
    echo "please input log url"
    show_help
    exit 1
  fi
}

param_check

boot_file_path=${app_url}
local_code_dir=${boot_file_path%/*}

logger "user: $(id)"
logger "pwd: ${PWD}"
logger "app_url: ${app_url}"
logger "boot_file: ${boot_file}"
logger "log_url: ${log_url}"
logger "command: ${boot_file} $@"
logger "local_code_dir: ${local_code_dir}"

params="$@"
train_param=${params%%need_freeze*}
logger "train_params:${train_param}"
if [[ $@ =~ need_freeze ]]; then
    freeze_cmd=${params##*need_freeze }
    logger "freeze_cmd:${freeze_cmd}"
fi

chmod 640 ${log_url}

start_time=$(date +%Y-%m-%d-%H:%M:%S)
logger "Training start at ${start_time}"

# hccl json process
source rank_table.sh

ret=$(check_hccl_status)
if [[ "${ret}" == "1" ]]; then
  echo "wait hccl status timeout, train job failed." | tee -a hccl.log
  chmod 440 ${log_url}
  exit 1
fi

sleep 1

# 获取hccl.json文件中的device_count字段
device_count=$(cat "${RANK_TABLE_FILE}" | grep -o device_id | wc -l)
if [[ "${device_count}" -eq 0 ]]; then
  echo "device count is 0, train job failed." | tee -a hccl.log
  chmod 440 ${log_url}
  exit 1
fi

# 获取hccl.json文件中的server_count字段
server_count=$(get_json_value ${RANK_TABLE_FILE} server_count)
if [[ "${server_count}" == "" ]]; then
  echo "server count is 0, train job failed." | tee -a hccl.log
  chmod 440 ${log_url}
  exit 1
fi

function get_env_for_1p_job() {
  export DEVICE_NUM=1
  export DEVICE_ID=0
  export ASCEND_DEVICE_ID=${DEVICE_ID}
  export RANK_ID=0
  export RANK_SIZE=1
  export DEVICE_INDEX=${RANK_ID}
  export JOB_ID=123456789
}

function get_env_for_multi_card_job() {
  export JOB_ID=123456789
  rankid=$((rank_start + i))
  export DEVICE_ID=${i}
  export ASCEND_DEVICE_ID=${DEVICE_ID}
  export RANK_ID=${rankid}
  export RANK_SIZE=${device_count}
  export RANK_TABLE_FILE=/user/serverid/devindex/config/hccl.json
}

function get_env_for_pytorch_multi_node_job() {
  export JOB_ID=123456789
  export RANK_TABLE_FILE=/user/serverid/devindex/config/hccl.json
  #将Host日志输出到串口,0-关闭/1-开启
  export ASCEND_SLOG_PRINT_TO_STDOUT=0
  #设置默认日志级别,0-debug/1-info/2-warning/3-error
  export ASCEND_GLOBAL_LOG_LEVEL=3
  #设置Event日志开启标志,0-关闭/1-开启
  export ASCEND_GLOBAL_EVENT_ENABLE=0
  #设置是否开启taskque,0-关闭/1-开启
  export TASK_QUEUE_ENABLE=1
  export HCCL_WHITELIST_DISABLE=1
  export HCCL_IF_IP=${XDL_IP}
  first_server_ip=$(get_server_id_0_ip)
  export MASTER_ADDR=${first_server_ip}
  export WORLD_SIZE=${server_count}
  export RANK=${server_id}
  set_env
}

DLS_PROGRAM_EXECUTOR="$(dls_get_executor "$boot_file")"

# 单节点训练场景
if [[ "${server_count}" -eq 1 ]]; then
  server_id=0
  if [ "${device_count}" -eq 1 ]; then
    get_env_for_1p_job
    ${DLS_PROGRAM_EXECUTOR} ${boot_file_path}${boot_file} ${train_param} 2>&1 | tee ${log_url}
    if [[ $@ =~ need_freeze ]]; then
      ${DLS_PROGRAM_EXECUTOR} ${boot_file_path}${freeze_cmd} 2>&1 | tee ${log_url}
    fi
    chmod 440 ${log_url}
    exit 0
  fi
fi

# 多节点场景
if [[ "${server_count}" -ge 1 ]]; then
  server_id=$(get_server_id)
  if [ -z "${framework}" ]; then
    echo "framework is null."
    chmod 440 ${log_url}
    exit 1
  fi

  logger "server id is: ""${server_id}"
  if [ "${framework}" == "PyTorch" ]; then
    get_env_for_pytorch_multi_node_job
    ${DLS_PROGRAM_EXECUTOR} ${boot_file_path}${boot_file} ${train_param} --addr=${MASTER_ADDR} --world-size=${WORLD_SIZE} --rank=${RANK}| tee ${log_url}
    if [[ $@ =~ need_freeze ]]; then
      ${DLS_PROGRAM_EXECUTOR} ${boot_file_path}${freeze_cmd} --addr=${MASTER_ADDR} --world-size=${WORLD_SIZE} --rank=${RANK}| tee ${log_url}
    fi
  elif [ "${framework}" == "Tensorflow" ]; then
    # CPU核心数
    core_num=`cat /proc/cpuinfo | grep "processor" | wc -l`
    device_each_server=$((device_count / server_count))
    rank_start=$((device_each_server * server_id))
    for ((i = $((device_each_server - 1)); i >= 0; i--)); do
      get_env_for_multi_card_job
      export DEVICE_INDEX=${RANK_ID}
      logger "start training for rank ${RANK_ID}, device ${DEVICE_ID}"
      # 设置绑定范围，如:0-11
      core_range="$((i*${core_num}/8))-$(((i+1)*${core_num}/8-1))"
      if [ "${i}" -eq 0 ]; then
          taskset -c ${core_range} ${DLS_PROGRAM_EXECUTOR} ${boot_file_path}${boot_file} ${train_param} | tee ${log_url}
          if [[ $@ =~ need_freeze ]]; then
            taskset -c ${core_range} ${DLS_PROGRAM_EXECUTOR} ${boot_file_path}${freeze_cmd} | tee ${log_url}
          fi
      else
          taskset -c ${core_range} ${DLS_PROGRAM_EXECUTOR} ${boot_file_path}${boot_file} ${train_param} &>> ${log_url} &
      fi
    done
  elif [ "${framework}" == "MindSpore" ]; then
    device_each_server=$((device_count / server_count))
    rank_start=$((device_each_server * server_id))
    for ((i = $((device_each_server - 1)); i >= 0; i--)); do
      get_env_for_multi_card_job
      echo "start training for rank ${RANK_ID}, device ${DEVICE_ID}"
      if [ "${i}" -eq 0 ]; then
          ${DLS_PROGRAM_EXECUTOR} ${boot_file_path}${boot_file} ${train_param} | tee ${log_url}
          if [[ $@ =~ need_freeze ]]; then
            ${DLS_PROGRAM_EXECUTOR} ${boot_file_path}${freeze_cmd} | tee ${log_url}
          fi
      else
          ${DLS_PROGRAM_EXECUTOR} ${boot_file_path}${boot_file} ${train_param} &>> ${log_url} &
      fi
    done
  else
    logger "framework error"
  fi
fi

chmod 440 ${log_url}