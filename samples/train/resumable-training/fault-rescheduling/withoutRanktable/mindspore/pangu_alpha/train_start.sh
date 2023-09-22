#!/bin/bash

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

# 训练数据集路径，根据实际情况修改
dataset="/job/data/train_data"

# 设置训练环境变量
set_env

# check npu status and wait some time if it is used by others
check_npu_availability

#配置训练信息
device_count=${MS_WORKER_NUM}
device_each_server=${MS_LOCAL_WORKER}
server_id=${MS_NODE_RANK}
server_count=$((device_count / device_each_server))

# 单节点训练场景
if [[ "$server_count" == "1" ]]; then
    server_id=0
    if [ ${device_count} -lt 8 ]; then
        echo "Less than 8 card training is not supported for pangu alpha model." | tee log
        exit 1
    fi
    if [ ${device_count} -eq 8 ]; then
        bash main.sh ${device_count} ${device_each_server} ${server_id} ${dataset}
        ET=$?
        if [[ ${ET} -ne 0 ]]; then
            echo "running job failed." | tee -a log
            exit ${ET}
        fi
    fi

# 分布式训练场景
else
    echo "server id is: "${server_id}
    bash main.sh ${device_count} ${device_each_server} ${server_id} ${dataset}
    ET=$?
    if [[ ${ET} -ne 0 ]]; then
        echo "running job failed." | tee -a log
        exit ${ET}
    fi
fi
