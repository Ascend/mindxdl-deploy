#!/bin/bash


ulimit -u unlimited
ROOT_PATH=$(cd "`dirname $0`" || exit; pwd)
export REPEAT_TUNE=false
export TE_PARALLEL_COMPILER=10
export ENABLE_TUNE_BANK=True
export MS_COMM_COMPILER_OPT=5000
export MS_COMPILER_CACHE_PATH=/job/code

# 单机多卡和分布式
if [ $# == 5 ]; then
    SERVER_NUM=$2
    RANK_SIZE=$1
    export RANK_TABLE_FILE=$3

    SERVER_ID=$4
    device_each_server=$((RANK_SIZE / SERVER_NUM))
    rank_start=$((${device_each_server} * SERVER_ID))

    data_path=$5
    # 先启动后台任务，最后留一个前台任务查看日志输出
    for((i=$((${device_each_server}-1)); i>=0; i--))
    do
        rankid=$((rank_start + i))
        export DEVICE_ID=${i}
        export RANK_ID=${rankid}
        mkdir -p ${ROOT_PATH}/../device$rankid
        cd ${ROOT_PATH}/../device$rankid || exit
        group_info_dir=./group_info.pb
        group_info_file_tmp=$(realpath $group_info_dir)
        export GROUP_INFO_FILE=${group_info_file_tmp}
        echo "start training for rank ${RANK_ID}, device ${DEVICE_ID}"
        env > env.log
        python ${ROOT_PATH}/../train.py --distribute=true --device_num=${device_each_server} --data_url=${data_path} --run_type=train --param_init_type=fp16 --mode=2.6B &> log &

    done
else
    echo "Invalid input parameter, usage: main.sh device_count server_count RANK_TABLE_FILE server_id dataset" | tee log
    exit 1
fi
python -u ${ROOT_PATH}/reset_process.py
wait
