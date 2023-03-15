#!/bin/bash

ulimit -u unlimited

# checkpoint save path
OUTPUT_PATH="/job/code/output"

ROOT_PATH=$(cd "`dirname $0`" || exit; pwd)

# 单机单卡
if [ $# == 2 ]; then
    export DEVICE_NUM=1
    export DEVICE_ID=0
    export RANK_ID=0
    export RANK_SIZE=1
    unset RANK_TABLE_FILE

    DATA_PATH=$1
    CONFIG_PATH=$2
    if [ -d "train" ];
    then
        rm -rf ${ROOT_PATH}/train
    fi
    mkdir ${ROOT_PATH}/train
    cp ${ROOT_PATH}/../*.py ${ROOT_PATH}/train
    cp ${ROOT_PATH}/*.sh ${ROOT_PATH}/train
    cp -r ${ROOT_PATH}/../src ${ROOT_PATH}/train
    cd ${ROOT_PATH}/train || exit
    echo "start training for device $DEVICE_ID"
    env > env.log

    # 保持前台输出
    python ${ROOT_PATH}/../train.py --data_path=${DATA_PATH} --config_path=${CONFIG_PATH} --output_path=${OUTPUT_PATH} --pre_trained=${OUTPUT_PATH}
    if [ $? -eq 0 ]; then
      echo "run training job complete." | tee log
      exit 0
    else
      echo "run training job failed." | tee log
      exit 1
    fi
fi

# 单机多卡和分布式
if [ $# == 6 ]; then
    export DEVICE_NUM=$1
    export SERVER_NUM=$2
    export RANK_SIZE=$1
    export RANK_TABLE_FILE=$3

    export SERVER_ID=$4
    device_each_server=$((DEVICE_NUM / SERVER_NUM))
    rank_start=$((${device_each_server} * SERVER_ID))
	
    DATA_PATH=$5
    CONFIG_PATH=$6

    # 先启动后台任务，最后留一个前台任务查看日志输出
    for((i=$((${device_each_server}-1)); i>=0; i--))
    do
        rankid=$((rank_start + i))
        export DEVICE_ID=${i}
        export RANK_ID=${rankid}
        rm -rf ${ROOT_PATH}/train_parallel${rankid}
        mkdir ${ROOT_PATH}/train_parallel${rankid}
        cp ${ROOT_PATH}/../*.py ${ROOT_PATH}/train_parallel${rankid}
        cp ${ROOT_PATH}/*.sh ${ROOT_PATH}/train_parallel${rankid}
        cp -r ${ROOT_PATH}/../src ${ROOT_PATH}/train_parallel${rankid}
        cd ${ROOT_PATH}/train_parallel${rankid} || exit
        echo "start training for rank $RANK_ID, device $DEVICE_ID"
        env > env.log

        if [ $i -eq 0 ]; then
            python ${ROOT_PATH}/../train.py --run_distribute=True --device_num=${RANK_SIZE} --data_path=${DATA_PATH} --config_path=${CONFIG_PATH} --output_path=${OUTPUT_PATH} --pre_trained=${OUTPUT_PATH}
        else
            python ${ROOT_PATH}/../train.py --run_distribute=True --device_num=${RANK_SIZE} --data_path=${DATA_PATH} --config_path=${CONFIG_PATH} --output_path=${OUTPUT_PATH} --pre_trained=${OUTPUT_PATH} &> log &
        fi

    done
else
    echo "Invalid input parameter, usage: main.sh device_count server_count rank_table_file server_id dataset config_file_path" | tee log
    exit 1
fi

wait
