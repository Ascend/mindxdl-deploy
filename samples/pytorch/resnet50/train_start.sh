#!/bin/bash
#set -x

umask 007
currentDir=$(cd "$(dirname "$0")"; pwd)
cd ${currentDir}

export RANK_TABLE_FILE=/user/serverid/devindex/config/hccl.json

logDir="/job/output/pytorch/logs"
mkdir -p ${logDir}

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

function check_hccl_status()
{
    local retry_times=60
    local retry_interval=5
    for (( n=1;n<=$retry_times;n++ ));do
    {
        local status=$(get_json_value ${RANK_TABLE_FILE} status)
        if [[ "$status" != "completed" ]]; then
            echo "hccl status is not completed, wait 5s and retry." | tee -a ${logDir}/hccl.log
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

function check_device_list()
{
    local device_per_server=$1
    local is_valid=0
    local valid_dev_list=("0" "1" "2" "3" "4" "5" "6" "7" "0,1" "2,3" "4,5" "6,7" "0,1,2,3" "4,5,6,7" "0,1,2,3,4,5,6,7")
    # Generate device list for training job
    for (( i=1;i<=${device_per_server};i++ ));do
    {
        dev_id=$(get_json_value ${RANK_TABLE_FILE} device_id ${i})
        device_list=$device_list$dev_id','
    }
    done
    dev_list=${device_list%?}
    for i in ${valid_dev_list[*]}; do
        if [ "$i" == "$dev_list" ]; then
            device_list=$dev_list
            echo "The devices id ${device_list} are valid." | tee -a ${logDir}/${log_id}/training_${device_count}.log 2>&1
            is_valid=1
            break
        else
            is_valid=0
        fi
    done
    if [ $is_valid -eq 0 ];then
        echo "The devices id ${dev_list} are invalid, current job will be stopped." | tee -a ${logDir}/${log_id}/training_${device_count}.log 2>&1
        exit 1
    fi
}

function get_server_id()
{
    local key="server_id"
    local srv_id=$(cat ${RANK_TABLE_FILE} | awk -F"[,:}]" '{for(i=1;i<=NF;i++){if($i~/'${key}'\042/){print $(i+1)}}}' |
                   awk '{print FNR ":" $1}' | grep ${XDL_IP} | awk -F ":" '{print $1}')
    if [ -z ${srv_id} ];then
        echo "Fail to get server id, current job will be stopped." | tee -a ${logDir}/${log_id}/training_${device_count}.log 2>&1
        exit 1
    fi
    srv_id=$(($srv_id-1))
    echo ${srv_id}
}


ret=$(check_hccl_status)
if [[ "${ret}" == "1" ]]; then
    echo "wait hccl status timeout, train job failed." | tee -a ${logDir}/hccl.log
    exit 1
fi


device_count=$(cat "${RANK_TABLE_FILE}" | grep -o device_id | wc -l)
if [[ "$device_count" -eq 0 ]]; then
    echo "device count is 0, train job failed." | tee -a ${logDir}/hccl.log
    exit 1
fi

server_count=$(get_json_value ${RANK_TABLE_FILE} server_count)
if [[ "$server_count" == "" ]]; then
    echo "server count is 0, train job failed." | tee -a ${logDir}/hccl.log
    exit 1
fi
export WORLD_SIZE=${server_count}


master_ip=$(get_json_value ${RANK_TABLE_FILE} server_id)
if [[ "$master_ip" == "" ]]; then
    echo "fail to get ip, train job failed." | tee -a ${logDir}/hccl.log
    exit 1
fi
echo "master ip:${master_ip} as master"
export MASTER_ADDR=${master_ip}

train_start_time=`date +%Y_%m%d_%H%M`

log_id=${train_start_time}
mkdir -p ${logDir}/${log_id}
chmod 777 -R ${logDir}
cluster=False
device_count_per_server=`expr $device_count / $server_count`
rank_size=${device_count}
device_list=''
# single node training job
if [[ "$server_count" == "1" ]]; then
    echo "This is a single node training job." | tee -a ${logDir}/${log_id}/training_${device_count}.log 2>&1
    device_id=0
    rank_index=0
    check_device_list ${device_count_per_server}
    bash main.sh ${device_id} ${device_list} ${rank_size} ${rank_index} ${log_id} ${cluster} &
# multiple node training job
else
    echo "This is a cluster distribution training job." | tee -a ${logDir}/${log_id}/training_${device_count}.log 2>&1
    cluster=True
    # Generate hccl bridge device file
    config_path=/usr/serverid/devindex/config
    if [ ! -d ${config_path} ]; then
        mkdir -p ${config_path}
    fi
    hccl_bridge_device_path=${config_path}/hccl_bridge_device_file
    if [ -f ${hccl_bridge_device_path} ];then
        rm -f ${hccl_bridge_device_path}
    fi
    touch ${hccl_bridge_device_path}
    chmod 755 ${hccl_bridge_device_path}
    # Getting cluster node devices' ips for each first device.
    for (( i=1;i<=${device_count};i+=${device_count_per_server} )); do
    {
        dev_ip=$(get_json_value ${RANK_TABLE_FILE} device_ip ${i})
        echo "${dev_ip}:0" >> ${hccl_bridge_device_path}
    }
    done
    export HCCL_BRIDGE_DEVICE_FILE=${hccl_bridge_device_path}
    echo "hccl bridge device file: ${HCCL_BRIDGE_DEVICE_FILE}" | tee -a ${logDir}/${log_id}/training_${device_count}.log 2>&1

    device_id=0
    check_device_list ${device_count_per_server}
    rank_index=$(get_server_id)
    log_id=${train_start_time}${rank_index}
    mkdir -p ${logDir}/${log_id}
    chmod 777 -R ${logDir}
    bash main.sh ${device_id} ${device_list} ${rank_size} ${rank_index} ${log_id} ${cluster} &
fi

wait
