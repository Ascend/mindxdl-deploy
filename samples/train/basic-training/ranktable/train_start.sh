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
echo $@ |grep -q -E '^[ 0-9a-zA-Z,./:_=-]*$'
ret=$?
if [ "${ret}" -ne 0 ]; then
  echo "params error!"
  exit 1
fi

# training job input parameters
code_real_dir=`readlink -f $1`
if [ -d "${code_real_dir}" ]; then
    app_url="${code_real_dir}/"
fi
output_real_path=`readlink -f $2`
if [ -d "${output_real_path}" ]; then
    output_url="${output_real_path}"
else
    mkdir -p  ${output_real_path}
    output_url="${output_real_path}"
fi
boot_file="$3"
shift 3

function show_help() {
  echo "Usage train_start.sh /job/code/resnet50 /tmp/output train.py"
}

function param_check() {
  if [ -z "${app_url}" ]; then
    echo "please input code dir"
    show_help
    exit 1
  fi

  if [ -L ${app_url} ]; then
    echo "code dir is a link!"
    exit 1
  fi

  if [ -z "${boot_file}" ]; then
    echo "please input boot file"
    show_help
    exit 1
  fi

  if [ -L ${boot_file} ]; then
    echo "boot file is a link!"
    exit 1
  fi

  if [ -z "${output_url}" ]; then
    echo "please input output url"
    show_help
    exit 1
  fi

  if [ -L ${output_url} ]; then
    echo "output url is a link!"
    exit 1
  fi

}

boot_file_path=${app_url}
params="$@"
train_param=${params%%need_freeze*}
if [[ $@ =~ need_freeze ]]; then
    freeze_cmd=${params##*need_freeze }
fi

param_check
chmod 640 ${output_url}

start_time=$(date +%Y-%m-%d-%H:%M:%S)
logger "Training start at ${start_time}"

# hccl json process
source rank_table.sh

check_hccl_status
if [ $? -eq 1 ]; then
  echo "wait hccl status timeout, train job failed." | tee -a hccl.log
  chmod 440 ${output_url}
  exit 1
fi

sleep 1

# 获取hccl.json文件中的device_count字段
device_count=$(cat "${RANK_TABLE_FILE}" | grep -o device_id | wc -l)
if [[ "${device_count}" -eq 0 ]]; then
  echo "device count is 0, train job failed." | tee -a hccl.log
  chmod 440 ${output_url}
  exit 1
fi

# 获取hccl.json文件中的server_count字段
server_count=$(get_json_value ${RANK_TABLE_FILE} server_count)
if [[ "${server_count}" == "" ]]; then
  echo "server count is 0, train job failed." | tee -a hccl.log
  chmod 440 ${output_url}
  exit 1
fi

# 获取device_list
device_list=""
device_list_len=${device_count}

if [[ "${server_count}" -gt 1 ]]; then
  device_list_len=$((device_count / server_count))
fi
for ((i = 1; i <= ${device_list_len}; i++)); do
  dev_id=$(get_json_value ${RANK_TABLE_FILE} rank_id ${i})
  if [[ "${i}" -eq 1 ]]; then
    device_list="${dev_id}"
  else
    device_list="${device_list},${dev_id}"
  fi
done

echo "device_list: ${device_list}"

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
  rankid=$((rank_start + i))
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
  export RANK_ID=${rankid}
  export RANK_SIZE=$((device_count / server_count))
}

function check_return_code() {
    ret_code=$?
    if [[ ${ret_code} -ne 0 ]]; then
      logger "running job failed. exit code: ${ret_code}" | tee -a ${output_url}/log
      exit ${ret_code}
    fi
}

DLS_PROGRAM_EXECUTOR="$(dls_get_executor "$boot_file")"
# set training env
set_env

# 单节点训练场景
if [[ "${server_count}" -eq 1 ]]; then
  device_id=0
  if [ "${device_count}" -eq 1 ]; then
    get_env_for_1p_job
    if [ "${framework}" == "PyTorch" ]; then
      ${DLS_PROGRAM_EXECUTOR} ${boot_file_path}${boot_file} --gpu=${device_id} ${train_param} 2>&1 && tee ${output_url}/log
      check_return_code
    else
      ${DLS_PROGRAM_EXECUTOR} ${boot_file_path}${boot_file} ${train_param} 2>&1 && tee ${output_url}/log
      check_return_code
    fi
    chmod 440 ${output_url}
    exit ${ret_code}
  fi
fi

# 多节点场景
if [[ "${server_count}" -ge 1 ]]; then
  server_id=$(get_server_id)
  if [ -z "${framework}" ]; then
    echo "framework is null."
    chmod 440 ${output_url}
    exit 1
  fi

  logger "server id is: ""${server_id}"
  if [ "${framework}" == "PyTorch" ]; then
    # CPU core number
    core_num=`cat /proc/cpuinfo | grep "processor" | wc -l`
    device_each_server=$((device_count / server_count))
    rank_start=$((device_each_server * server_id))
    for ((i = $((device_each_server - 1)); i >= 0; i--)); do
      get_env_for_pytorch_multi_node_job
      logger "start training for rank ${RANK_ID}"
      # set bing range, like:0-11
      core_range="$((i*${core_num}/${device_each_server}))-$(((i+1)*${core_num}/${device_each_server}-1))"
      if [ "${i}" -eq 0 ]; then
          taskset -c ${core_range} ${DLS_PROGRAM_EXECUTOR} ${boot_file_path}${boot_file} ${train_param} --gpu=${i} --addr=${MASTER_ADDR} --world-size=${WORLD_SIZE} --rank=${RANK} && tee ${output_url}/device_${RANK_ID}.log
          check_return_code
      else
          taskset -c ${core_range} ${DLS_PROGRAM_EXECUTOR} ${boot_file_path}${boot_file} ${train_param} --gpu=${i} --addr=${MASTER_ADDR} --world-size=${WORLD_SIZE} --rank=${RANK} &>> ${output_url}/device_${RANK_ID}.log &
          check_return_code
      fi
    done
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
      core_range="$((i*${core_num}/${device_each_server}))-$(((i+1)*${core_num}/${device_each_server}-1))"
      if [ "${i}" -eq 0 ]; then
          taskset -c ${core_range} ${DLS_PROGRAM_EXECUTOR} ${boot_file_path}${boot_file} ${train_param} --model_dir=${output_url}/models/device_${DEVICE_INDEX}/ && tee ${output_url}/device_${RANK_ID}.log
          check_return_code
          if [[ $@ =~ need_freeze ]]; then
            taskset -c ${core_range} ${DLS_PROGRAM_EXECUTOR} ${boot_file_path}${freeze_cmd} --model_dir=${output_url}/models/device_${DEVICE_INDEX}/ && ${output_url}/device_${RANK_ID}.log
            check_return_code
          fi
      else
          taskset -c ${core_range} ${DLS_PROGRAM_EXECUTOR} ${boot_file_path}${boot_file} ${train_param} --model_dir=${output_url}/models/device_${DEVICE_INDEX}/ &>> ${output_url}/device_${RANK_ID}.log &
      fi
    done
  elif [ "${framework}" == "MindSpore" ]; then
    device_each_server=$((device_count / server_count))
    rank_start=$((device_each_server * server_id))
    for ((i = $((device_each_server - 1)); i >= 0; i--)); do
      get_env_for_multi_card_job
      echo "start training for rank ${RANK_ID}, device ${DEVICE_ID}"
      if [ "${i}" -eq 0 ]; then
          ${DLS_PROGRAM_EXECUTOR} ${boot_file_path}${boot_file} ${train_param} && tee ${output_url}/device_${RANK_ID}.log
          check_return_code
          if [[ $@ =~ need_freeze ]]; then
            ${DLS_PROGRAM_EXECUTOR} ${boot_file_path}${freeze_cmd} && tee ${output_url}/device_${RANK_ID}.log
            check_return_code
          fi
      else
          ${DLS_PROGRAM_EXECUTOR} ${boot_file_path}${boot_file} ${train_param} &>> ${output_url}/device_${RANK_ID}.log &
      fi
    done
  else
    logger "framework error"
  fi
fi

chmod 440 ${output_url}

wait