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

function dls_get_executor {
    local filename="$(basename -- "$1")"
    local extension="${filename##*.}"
    extension="$(echo "$extension" | tr '[:upper:]' '[:lower:]')"
    case "$extension" in
    py|pyc|pyw|pyo|pyd)
        which python
        ;;
    sh)
        which bash
        ;;
    *)
        ;;
    esac
}

function set_env {
    local install_path=/usr/local/Ascend
    if [ -d ${install_path}/ascend-toolkit/latest ]; then
      # use toolkit env
      source ${install_path}/ascend-toolkit/set_env.sh
    elif [ -d ${install_path}/nnae/latest ]; then
      # use nnae env
      source ${install_path}/nnae/set_env.sh
    fi

    # use tfplugin env
    if [ -d ${install_path}/tfplugin/latest ]; then
      source ${install_path}/tfplugin/set_env.sh
    fi
}

function logger {
    echo "[$(date +%Y%m%d-%H:%M:%S)] [MindXDL Service Log]$*"
}

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
    mkdir -p ${output_real_path}
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

sleep 1

if [[ "${LOCAL_WORLD_SIZE}" == "" ]]; then
    device_count=1
    server_count=1
else 
    # 获取环境变量中的device_count字段
    device_count=${LOCAL_WORLD_SIZE}
    if [[ "${device_count}" -eq 0 ]]; then
      echo "device count is 0, train job failed." | tee -a hccl.log
      chmod 440 ${output_url}
      exit 1
    fi
    # 获取环境变量中的server_count字段
    server_count=`expr ${WORLD_SIZE} / ${LOCAL_WORLD_SIZE}`
    if [[ "${server_count}" == "" ]]; then
      echo "server count is 0, train job failed." | tee -a hccl.log
      chmod 440 ${output_url}
      exit 1
    fi
fi

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
export JOB_ID=123456789
export RANK_SIZE=${device_count}


# 单卡训练场景
if [ "${device_count}" -eq 1 ] && [ "${server_count}" -eq 1 ]; then
  device_id=0
  ${DLS_PROGRAM_EXECUTOR} ${boot_file_path}${boot_file} --gpu=${device_id} ${train_param} 2>&1 && tee ${output_url}/log
  check_return_code
  chmod 440 ${output_url}/log
  exit ${ret_code}
fi

# 分布式场景
if [[ "${device_count}" -ge 1 ]]; then
  server_id=${RANK}
  logger "server id is: ""${server_id}"
  rank_start=`expr ${RANK} \* ${LOCAL_WORLD_SIZE}`
  for ((i = $((${LOCAL_WORLD_SIZE} - 1)); i >= 0; i--)); do
    export DEVICE_INDEX=`expr ${rank_start} + ${i}`
    export ASCEND_DEVICE_ID=${i}
    if [[ "${i}" -eq 0 ]]; then
      ${DLS_PROGRAM_EXECUTOR} ${boot_file_path}${boot_file} ${train_param} --gpu=${ASCEND_DEVICE_ID} --multiprocessing-distributed --addr=${MASTER_ADDR} --world-size=${server_count} --rank=${RANK} 2>&1 && tee ${output_url}/device_${DEVICE_INDEX}.log
      check_return_code
    else
      ${DLS_PROGRAM_EXECUTOR} ${boot_file_path}${boot_file} ${train_param} --gpu=${ASCEND_DEVICE_ID} --multiprocessing-distributed --addr=${MASTER_ADDR} --world-size=${server_count} --rank=${RANK} &> ${output_url}/device_${DEVICE_INDEX}.log &
      check_return_code
    fi
  done
fi

chmod 440 ${output_url}
