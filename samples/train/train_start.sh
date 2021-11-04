#!/bin/bash
# default start shell path
DLS_USER_HOME_DIR="$(
  cd "$(dirname "$0")"
  pwd -P
)"
cd "$DLS_USER_HOME_DIR"

# set pythonpath(especially for tensorflow)
export PYTHONPATH="$DLS_USER_JOB_DIR:$PYTHONPATH"
export PYTHONUNBUFFERED=1

# use utils.sh env and functions
source utils.sh

# training job input parameters
app_url="$1"
boot_file="$2"
log_url="$3"
data_url="$4"
output_url="$5"

boot_file_path="$app_url/$boot_file"
local_code_dir=${boot_file_path%/*}

logger "user: $(id)"
logger "pwd: $PWD"
logger "app_url: ${app_url}"
logger "boot_file: ${boot_file}"
logger "log_url: $log_url"
logger "command: ${boot_file} $@"
logger "local_code_dir: ${local_dir_dir}"

start_time=$(date +%Y-%m-%d-%H:%M:%S)
logger "Training start at ${start_time}"

# install dependency
install_dependency "${local_code_dir}" 2>&1 | dls_logger "$log_url"

# hccl json process
source rank_table.sh

ret=$(check_hccl_status)
if [[ "${ret}" == "1" ]]; then
  echo "wait hccl status timeout, train job failed." | tee -a hccl.log
  exit 1
fi

sleep 1

# 获取hccl.json文件中的device_count字段
device_count=$(cat "${RANK_TABLE_FILE}" | grep -o device_id | wc -l)
if [[ "$device_count" -eq 0 ]]; then
  echo "device count is 0, train job failed." | tee -a hccl.log
  exit 1
fi

# 获取hccl.json文件中的server_count字段
server_count=$(get_json_value ${RANK_TABLE_FILE} server_count)
if [[ "$server_count" == "" ]]; then
  echo "server count is 0, train job failed." | tee -a hccl.log
  exit 1
fi

function get_env_for_1p_job() {
  export DEVICE_NUM=1
  export DEVICE_ID=0
  export ASCEND_DEVICE_ID=${DEVICE_ID}
  export RANK_ID=0
  export RANK_SIZE=1
  export JOB_ID=123456789
  unset RANK_TABLE_FILE
  env >env.log
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
  rankid=$((rank_start + i))
  export DEVICE_ID=${i}
  export ASCEND_DEVICE_ID=${DEVICE_ID}
  export RANK_ID=${rankid}
  export RANK_SIZE=${device_count}
  export RANK_TABLE_FILE=/user/serverid/devindex/config/hccl.json
  export HCCL_WHITELIST_DISABLE=1
  export HCCL_IF_IP=${XDL_IP}
  first_server_ip=get_server_id_0_ip
  export MASTER_ADDR=${first_server_ip}
  export MASTER_PORT=29561
}

DLS_PROGRAM_EXECUTOR="$(dls_get_executor "$boot_file")"

function run_single_card_job() {
  server_id=0
  if [ ${device_count} -eq 1 ]; then
    get_env_for_1p_job
    ${DLS_PROGRAM_EXECUTOR} ${boot_file_path} "$@" 2>&1 | dls_logger "$log_url" append
  fi
}

function run_multi_card_job() {
  if [ ${device_count} -gt 1 ]; then
    rank_start=0
    for ((i = $(($device_count - 1)); i >= 0; i--)); do
      get_env_for_multi_card_job
      ${DLS_PROGRAM_EXECUTOR} ${boot_file_path} "$@" | dls_logger "$log_url" append
    done
  fi
}

function run_multi_node_job() {
  if ${framework} == "PyTorch"; then
    device_each_server=${device_count} / ${server_count}
    rank_start=$((${device_each_server} * ${server_id}))
    for ((i = $(($device_each_server - 1)); i >= 0; i--)); do
      get_env_for_pytorch_multi_node_job
      ${DLS_PROGRAM_EXECUTOR} ${boot_file_path} "$@" | dls_logger "$log_url" append
    done
  else
    device_each_server=${device_count} / ${server_count}
    rank_start=$((${device_each_server} * ${server_id}))
    for ((i = $(($device_each_server - 1)); i >= 0; i--)); do
      get_env_for_multi_card_job
      ${DLS_PROGRAM_EXECUTOR} ${boot_file_path} "$@" | dls_logger "$log_url" append
    done
  fi
}

# 单节点训练场景
if [[ $server_count -eq 1 ]]; then
  run_single_card_job
fi

# 单节点多卡场景
if [[ $server_count -eq 1 ]]; then
  server_id=0
  run_multi_card_job
fi

# 多节点场景
if [[ $server_count -gt 1 ]]; then
  server_id=$(get_server_id)
  if [ $? -eq 1 ]; then
    echo "get server id failed."
    exit 1
  fi
  logger "server id is: "${server_id}
  run_multi_node_job
fi
