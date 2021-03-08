#!/bin/bash
# set -x
# 应用权限配置umask 007
umask 007
currentDir=$(cd "$(dirname "$0")"; pwd)
cd ${currentDir}

# ------------------------- 用户需要修改的部分 ------------------------------------------------
chgrp HwHiAiUser -R /job

# /job/code/*表示上传代码的位置，/job/code/*中的/code对应界面填写的code栏
chmod 770 -R /job/code/*

# /job/output/*表示训练任务输出日志、模型的位置，/job/output/*中的/output对应界面填写的output栏
chmod 770 -R /job/output/*

# /job/data表示上传数据集的位置，/job/data中的/data对应界面填写的data栏
chmod 750 -R /job/data
# -------------------------------------------------------------------------------------------

export ENV LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu/hdf5/serial:\
/usr/local/Ascend/add-ons:\
/usr/local/Ascend/driver/lib64/common:\
/usr/local/Ascend/driver/lib64/driver:$LD_LIBRARY_PATH

# hccl-controller组件生成的rank_table_file
export RANK_TABLE_FILE=/user/serverid/devindex/config/hccl.json
export NEW_RANK_INFO_FILE=/hccl_config/rank_id_info.txt

# 清理临时日志
rm -rf train*.log
rm -rf env*.log
rm -rf ${currentDir}/config/* /hccl_config

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

ret=$(check_hccl_status)
if [[ "${ret}" == "1" ]]; then
    echo "wait hccl status timeout, train job failed." | tee -a hccl.log
    exit 1
fi

mkdir -p /hccl_config
python3.7 ${currentDir}/trans_hccl_json_file.py
if [ ! $? -eq 0 ]
then
    exit 1
fi
chown -R HwHiAiUser:HwHiAiUser /hccl_config
cp ${NEW_RANK_INFO_FILE} ${currentDir}/config/rank_id_info.txt

# 备份每次训练生成的hccl.json文件
cp ${RANK_TABLE_FILE} ${currentDir}/config/hccl.json

# 获取hccl.json文件中的device_count字段
device_count=$(cat "${RANK_TABLE_FILE}" | grep -o device_id | wc -l)
if [[ "$device_count" -eq 0 ]]; then
    echo "device count is 0, train job failed." | tee -a hccl.log
    exit 1
fi

# 获取hccl.json文件中的instance_count字段
server_count=$(get_json_value ${RANK_TABLE_FILE} server_count)
if [[ "$server_count" == "" ]]; then
    echo "server count is 0, train job failed." | tee -a hccl.log
    exit 1
fi

train_start_time=`date +%Y_%m%d_%H%M`

# profiling
mkdir -p /var/log/npu/profiling/data/
chown -R HwHiAiUser:HwHiAiUser /var/log/npu/profiling/data/

# 单节点训练场景
device_count=$(( $(cat ${NEW_RANK_INFO_FILE} | grep "single_pod_npu_count" | awk -F ':' '{print $2}') ))
rank_size=$(cat ${NEW_RANK_INFO_FILE} | grep "rank_size" | awk -F ':' '{print $2}')
# 由K8s创建Pod时传入的一个环境变量，节点的ip
node_ip="${XDL_IP}"
# 当前pod里面所有的rank信息
pod_rank_info=$(cat ${NEW_RANK_INFO_FILE} | grep "${node_ip}")
pod_rank_info=${pod_rank_info#*:}

log_id=${train_start_time}${rank_index}

mkdir -p ${currentDir}/result/${log_id}
chmod 770 -R ${currentDir}/result
chgrp HwHiAiUser -R ${currentDir}/result

for (( i=0;i<$device_count;i++ ));do
{
    first_card=false
    if [[ "$i" == "0" ]]; then
        first_card=true
    fi
    rank_info=$(echo "${pod_rank_info}" | awk -F ':' '{print $1}')
    dev_id=$(echo ${rank_info} | awk -F ' ' '{print $1}')
    rank_id=$(echo ${rank_info} | awk -F ' ' '{print $2}')
    su - HwHiAiUser -c "bash ${currentDir}/main.sh ${dev_id} ${rank_size} ${rank_id} ${log_id} ${first_card} ${node_ip}" &
    pod_rank_info=${pod_rank_info#*:}
}
done

wait

# ------------------------- 用户需要修改的部分 ------------------------------------------------
# /job/code/*表示上传代码的位置，/job/code/*中的/code对应界面填写的code栏
chmod 770 -R /job/code/*

# /job/output/model/*表示训练任务输出模型的位置，/job/output/model/*中的/output对应界面填写的output栏
chmod 660 -R /job/output/model/*

# /job/output/logs/表示训练任务输出ckpt文件、event文件的位置，/job/output/logs/中的/output对应界面填写的output栏
chmod 770 -R /job/output/logs/
# -------------------------------------------------------------------------------------------

