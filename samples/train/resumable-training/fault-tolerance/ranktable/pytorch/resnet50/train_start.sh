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

# env for breakpoint ckpt
export RESUME_MODE_ENABLE=1

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

function check_npu_availability {
    i=0
    while [ $i -lt 10 ]; do
        npu_info=$(npu-smi info)
        if [[ $npu_info == *"command not found"* ]]; then
          echo "the container doesn't mount 'npu-smi' cmd, skip it now. you could mount 'npu-smi' cmd by yaml or
          ascend docker runtime"
          break
        elif [[ $npu_info == *"8020"* ]]; then
          echo "npu is busy, check again"
        else
          # npu maybe free
          break
        fi
        sleep 5
        let i++
    done

    if [ $i -eq 10 ]; then
      echo "npu is occupied by others too long, please release it"
      exit 1
    fi
}

function show_help() {
  echo "Usage train_start.sh /job/code/resnet50 /tmp/output/"
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

  if [ -z "${output_url}" ]; then
    echo "please input output url"
    show_help
    exit 1
  fi

  if [ -L ${output_url} ]; then
    echo "output url is a link!"
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

DLS_PROGRAM_EXECUTOR="$(dls_get_executor "$boot_file")"
# set training env
set_env

# check npu status and wait some time if it is used by others
check_npu_availability

train_pid=0
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
      export DEVICE_ID=${i}
      logger "start training for device ${DEVICE_ID}"
      # set bing range, like:0-11
      core_range="$((i*${core_num}/${device_each_server}))-$(((i+1)*${core_num}/${device_each_server}-1))"
      taskset -c ${core_range} ${DLS_PROGRAM_EXECUTOR} ${boot_file_path}${boot_file} ${train_param} --gpu=${DEVICE_ID} --multiprocessing-distributed --addr=${MASTER_ADDR} --world-size=${WORLD_SIZE} --rank=${RANK} &> ${output_url}/device_${RANK_ID}.log &
      train_pids[$i]=$!
    done
  else
    logger "framework error"
  fi
fi

chmod 440 "${output_url}"
tail -f "${output_url}"/device_${RANK_ID}.log &
old_log_pid=$!
python -u "${DLS_USER_HOME_DIR}"/reset_process.py -p "${train_pids[@]}" &
reset_pid=$!
wait ${train_pids[0]}
exit_code=$?
if [ ${exit_code} -eq 0 ]; then
  kill -15 ${reset_pid}
  echo "training finished."
  exit ${exit_code}
else
  if [ -d "${DLS_USER_HOME_DIR}"/ ]; then
    touch "${DLS_USER_HOME_DIR}"/newlog
    tail -f "${DLS_USER_HOME_DIR}"/newlog &
  fi
  kill -9 ${old_log_pid}
  wait ${reset_pid}
fi
