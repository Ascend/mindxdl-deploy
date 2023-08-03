#!/bin/bash

# hccl-controller组件生成的rank_table_file
export RANK_TABLE_FILE=/user/serverid/devindex/config/hccl.json

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
            echo 0
            return
        fi
    }
    done
    echo 1
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

# 根据实际情况进行修改，全局配置参数：数据集路径，配置参数文件路径
dataset_path=/job/data/imagenet_full/train
config_yaml_path=/job/code/resnet/resnet50_imagenet2012_config.yaml

# 设置训练环境变量
set_env

# 单节点训练场景
if [[ "$server_count" == "1" ]]; then
    server_id=0
    if [ ${device_count} -eq 1 ]; then
        bash main.sh ${dataset_path} ${config_yaml_path}
        if [[ $? -eq 1 ]]; then
            echo "running job failed." | tee log
            exit 1
        fi
    fi
    if [ ${device_count} -gt 1 ]; then
        bash main.sh ${device_count} ${server_count} ${RANK_TABLE_FILE} ${server_id} ${dataset_path} ${config_yaml_path}
        if [[ $? -eq 1 ]]; then
            echo "running job failed." | tee log
            exit 1
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
    bash main.sh ${device_count} ${server_count} ${RANK_TABLE_FILE} ${server_id} ${dataset_path} ${config_yaml_path}
    if [[ $? -eq 1 ]]; then
        echo "running job failed." | tee log
        exit 1
    fi
fi