#!/bin/bash


# hccl-controller组件生成的rank_table_file
export RANK_TABLE_FILE=/user/serverid/devindex/config/hccl.json

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

# 设置环境变量
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

# 解析rank_table_file
function get_json_value()
{
  local json=$1
  local key=$2

  if [[ -z "$3" ]]; then
    local num=1
  else
    local num=$3
  fi

  local value=$(cat "${json}" | awk -F"[,:}]" '{for(i=1;i<=NF;i++){if($i~/'${key}'\042/){print $(i+1)}}}' |
                tr -d '"' | sed -n ${num}p)
  echo ${value}
}

# 检查rank_table_file文件状态
function check_hccl_status()
{
    local retry_times=60
    local retry_interval=5
    for (( n=1;n<=$retry_times;n++ ));do
    {
        local status=$(get_json_value ${RANK_TABLE_FILE} status)
        if [[ "$status" != "completed" ]]; then
            echo "hccl status is not completed, wait 5s and retry." | tee -a hccl.log
            sleep $retry_interval
            continue
        else
            return 0
        fi
    }
    done
    return 1
}

function get_server_id()
{
    local key="server_id"
    local srv_id=$(cat ${RANK_TABLE_FILE} | awk -F"[,:}]" '{for(i=1;i<=NF;i++){if($i~/'${key}'\042/){print $(i+1)}}}' |
                   awk '{print FNR ":" $1}' | grep ${XDL_IP} | awk -F ":" '{print $1}')
    if [[ -z $srv_id || $srv_id -lt 1 ]];then
        return 1
    fi
    srv_id=$(($srv_id-1))
    echo ${srv_id}
}

check_hccl_status
if [[ $? -eq 1 ]]; then
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

# 训练数据集路径，根据实际情况修改
dataset="/job/data/train_data"

# 设置训练环境变量
set_env

# check npu status and wait some time if it is used by others
check_npu_availability

# 单节点训练场景
if [[ "$server_count" == "1" ]]; then
    server_id=0
    if [ ${device_count} -lt 8 ]; then
        echo "Less than 8 card training is not supported for pangu alpha model." | tee log
        exit 1
    fi
    if [ ${device_count} -eq 8 ]; then
        bash main.sh ${device_count} ${server_count} ${RANK_TABLE_FILE} ${server_id} ${dataset}
        ET=$?
        if [[ ${ET} -ne 0 ]]; then
            echo "running job failed." | tee -a log
            exit ${ET}
        fi
    fi

# 分布式训练场景
else
    server_id=$(get_server_id)
    if [ $? -eq 1 ];then
        echo "get server id failed."
        exit 1
    fi
    echo "server id is: "${server_id}
    bash main.sh ${device_count} ${server_count} ${RANK_TABLE_FILE} ${server_id} ${dataset}
    ET=$?
    if [[ ${ET} -ne 0 ]]; then
        echo "running job failed." | tee -a log
        exit ${ET}
    fi
fi
