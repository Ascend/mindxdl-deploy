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
log_real_path=`readlink -f $2`
if [ -f "${log_real_path}" ]; then
    log_url="${log_real_path}"
else
    touch ${log_real_path}
    log_url="${log_real_path}"
fi
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

  if [ -z "${log_url}" ]; then
    echo "please input log url"
    show_help
    exit 1
  fi

  if [ -L ${log_url} ]; then
    echo "log url is a link!"
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
chmod 640 ${log_url}

start_time=$(date +%Y-%m-%d-%H:%M:%S)
logger "Training start at ${start_time}"

sleep 1

function check_return_code() {
    if [[ $? -ne 0 ]]; then
      logger "running job failed." | tee ${log_url}
      exit 1
    fi
}

DLS_PROGRAM_EXECUTOR="$(dls_get_executor "$boot_file")"
# set training env
set_env
export JOB_ID=123456789

# 单卡训练场景
if [[ "${MS_ROLE}" -eq "" ]]; then
  rm -rf ${boot_file_path}/scripts/worker
  mkdir ${boot_file_path}/scripts/worker
  cp ${boot_file_path}/config/*.yaml ${boot_file_path}/scripts/worker
  cp ${boot_file_path}/*.py ${boot_file_path}/scripts/worker
  cp ${boot_file_path}/scripts/*.sh ${boot_file_path}/scripts/worker
  cp -r ${boot_file_path}/src ${boot_file_path}/scripts/worker
  cd ${boot_file_path}/scripts/worker || exit
  ${DLS_PROGRAM_EXECUTOR} ${boot_file_path}${boot_file} ${train_param} 2>&1 && tee ${log_url}
  check_return_code
  if [[ $@ =~ need_freeze ]]; then
    ${DLS_PROGRAM_EXECUTOR} ${boot_file_path}${freeze_cmd} 2>&1 && tee ${log_url}
    check_return_code
  fi
  chmod 440 ${log_url}
  exit 0
fi

# 分布式场景Scheduler
if [[ "${MS_ROLE}" == "MS_SCHED" ]]; then
  rm -rf ${boot_file_path}/scripts/sched
  mkdir ${boot_file_path}/scripts/sched
  cp ${boot_file_path}/config/*.yaml ${boot_file_path}/scripts/sched
  cp ${boot_file_path}/*.py ${boot_file_path}/scripts/sched
  cp ${boot_file_path}/scripts/*.sh ${boot_file_path}/scripts/sched
  cp -r ${boot_file_path}/src ${boot_file_path}/scripts/sched
  cd ${boot_file_path}/scripts/sched || exit
  
  logger "server id is: ""${server_id}"
  ${DLS_PROGRAM_EXECUTOR} ${boot_file_path}${boot_file} ${train_param} --run_distribute=True --device_num=${MS_LOCAL_WORKER} --parameter_server=False --device_target=Ascend  && tee ${log_url}
  check_return_code
  if [[ $@ =~ need_freeze ]]; then
    ${DLS_PROGRAM_EXECUTOR} ${boot_file_path}${freeze_cmd} --addr=${MASTER_ADDR} --world-size=${WORLD_SIZE} --rank=${RANK} && tee ${log_url}
    check_return_code
  fi
fi

# 分布式场景Worker
if [[ "${MS_ROLE}" == "MS_WORKER" ]]; then
  echo "start worker"
  start_index=`expr ${MS_NODE_RANK} \* ${MS_LOCAL_WORKER}`
  end_index=`expr ${start_index} + ${MS_LOCAL_WORKER}`
  for((i=((${end_index}-1));i>=${start_index};i--));
  do
     rm -rf ${boot_file_path}/scripts/worker_$i
     mkdir ${boot_file_path}/scripts/worker_$i
     cp ${boot_file_path}/config/*.yaml ${boot_file_path}/scripts/worker_$i
     cp ${boot_file_path}/*.py ${boot_file_path}/scripts/worker_$i
     cp ${boot_file_path}/scripts/*.sh ${boot_file_path}/scripts/worker_$i
     cp -r ${boot_file_path}/src ${boot_file_path}/scripts/worker_$i
     cd ${boot_file_path}/scripts/worker_$i || exit
	 ${DLS_PROGRAM_EXECUTOR} ${boot_file_path}${boot_file} ${train_param} --run_distribute=True --device_num=${MS_LOCAL_WORKER} --parameter_server=False --device_target=Ascend  && tee ${log_url}
     check_return_code
     if [[ $@ =~ need_freeze ]]; then
       ${DLS_PROGRAM_EXECUTOR} ${boot_file_path}${freeze_cmd} --run_distribute=True --device_num=${MS_LOCAL_WORKER} --parameter_server=False --device_target=Ascend && tee ${log_url}
       check_return_code
     fi
	 cd ..
  done
fi

chmod 440 ${log_url}
