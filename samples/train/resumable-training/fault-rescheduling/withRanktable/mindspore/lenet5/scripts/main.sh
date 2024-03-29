#!/bin/bash

ulimit -u unlimited

# 单机单卡
if [ $# -eq 0 ]; then
    rm -rf train
    mkdir train
    cp ../train.py ./train
    cp -rf ../dataset_lenet ./train
    cp -rf ../src ./train
    cd ./train || exit
    export DEVICE_ID=0
    export RANK_ID=0
    export RANK_SIZE=1
    unset RANK_TABLE_FILE
    echo "start training for device $DEVICE_ID"
    env > env.log
    # 保持前台输出
    python train.py |& tee train.log
    ST=${PIPESTATUS[0]}
    if [[ ${ST} -ne 0 ]]; then
        echo "running job failed." | tee -a train.log
        chmod 440 train.log
        exit ${ST}
    fi

    echo "training completed"
    cd ..

# 单机多卡和分布式
else
    DEVICE_NUM=$1
    if [ ${DEVICE_NUM} -gt 8 ];then
        DEVICE_NUM=8
    fi
    export RANK_SIZE=$1
    export RANK_TABLE_FILE=$2
    export SERVER_ID=$3
    rank_start=$((DEVICE_NUM * SERVER_ID))

    # 先启动后台任务，最后留一个前台任务查看日志输出
    for((i=$(($DEVICE_NUM-1)); i>=0; i--))
    do
        rankid=$((rank_start + i))
        export DEVICE_ID=${i}
        export RANK_ID=${rankid}
        rm -rf train_parallel${rankid}
        mkdir train_parallel${rankid}
        cp ../train.py ./train_parallel${rankid}
        cp -rf ../dataset_lenet ./train_parallel${rankid}
        cp -rf ../src ./train_parallel${rankid}
        cd ./train_parallel${rankid} || exit
        echo "start training for rank $RANK_ID, device $DEVICE_ID"
        env > env.log

        if [ $i -eq 0 ];then
            python train.py |& tee train.log
            ST=${PIPESTATUS[0]}
            if [[ ${ST} -ne 0 ]]; then
                echo "running job failed." | tee -a train.log
                chmod 440 train.log
                exit ${ST}
            fi
        else
            python train.py > train.log 2>&1 &
        fi
        cd ..
    done

    echo "training completed"
fi

wait
