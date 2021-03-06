#!/bin/sh

# 应用权限配置umask 007
umask 007
currentDir=$(cd "$(dirname "$0")"; pwd)
cd ${currentDir}

export LD_LIBRARY_PATH=/usr/local/bin:/usr/local/lib/python3.7/dist-packages/torch/lib:/usr/local/Ascend/nnae/latest/fwkacllib/lib64:/usr/local/Ascend/driver/lib64/common/:/usr/local/Ascend/driver/lib64/driver/:/usr/local/Ascend/add-ons/
export PYTHONPATH=$PYTHONPATH:/usr/local/Ascend/nnae/latest/fwkacllib/python/site-packages:/usr/local/Ascend/tfplugin/latest/tfplugin/python/site-packages:/code:{CURRENT_PATH}/code:/usr/local/Ascend/nnae/latest/fwkacllib/python/site-packages/auto_tune.egg:/usr/local/Ascend/nnae/latest/fwkacllib/python/site-packages/schedule_search.egg
export PATH=$PATH:/usr/local/Ascend/nnae/latest/fwkacllib/ccec_compiler/bin
export ASCEND_OPP_PATH=/usr/local/Ascend/nnae/latest/opp
export ASCEND_AICPU_PATH=/usr/local/Ascend/nnae/latest

export ASCEND_SLOG_PRINT_TO_STDOUT=0
export TASK_QUEUE_ENABLE=1

#--------------------------------------- 用户需要修改的部分 start --------------------------------------
epochs=90
batch_size=256
learning_rate=2.048
#--------------------------------------- 用户需要修改的部分 end ----------------------------------------

device_id=$1
export DEVICE_ID=$device_id

device_list=$2
export DEVICE_LIST=$device_list

rank_size=$3
export RANK_SIZE=${rank_size}

if [ x"${RANK_SIZE}" != x"1" ]; then
  export WHICH_OP=GEOP
  export NEW_GE_FE_ID=1
  export GE_AICPU_FLAG=1
fi

rank_index=$4
export RANK_INDEX=${rank_index}

DEVICE_INDEX=$(( DEVICE_ID + RANK_INDEX * 8 ))
export DEVICE_INDEX=${DEVICE_INDEX}

log_id=$5
logDir="/job/output/pytorch/logs"
train_job_dir=${logDir}/result/pt_resnet50/training_job_${log_id}
mkdir -p ${train_job_dir}
data_url='/job/data'

device_count=$(( rank_size / WORLD_SIZE ))
env > ${logDir}/${log_id}/env_${device_count}.log

cluster=$6

if [ x"${cluster}" == x"True" ];then
    python3.7 ${currentDir}/DistributedResnet50/main-apex-d76-npu.py \
        --data=${data_url} \
        --addr=${MASTER_ADDR} \
        --seed=49 \
        --workers=128 \
        --learning-rate=${learning_rate} \
        --warmup=8 \
        --label-smoothing=0.1 \
        --mom=0.9 \
        --weight-decay=1.0e-04 \
        --static-loss-scale=128 \
        --print-freq=1 \
        --dist-url='tcp://127.0.0.1:50000' \
        --dist-backend='hccl' \
        --multiprocessing-distributed \
        --world-size=${WORLD_SIZE} \
        --rank=${RANK_INDEX} \
        --benchmark=0 \
        --device-list=${DEVICE_LIST} \
        --device='npu' \
        --epochs=${epochs} \
        --batch-size=${batch_size} > ${train_job_dir}/train_${rank_size}p.log 2>&1
elif [ x"${rank_size}" == x"1" ];then
    python3.7 ${currentDir}/pytorch-resnet50-apex.py \
        "--data=${data_url}" \
        --workers=64 \
        --epochs=${epochs} \
        --batch-size=${batch_size} \
        --learning-rate=${learning_rate} \
        --warmup=5 \
        --label-smoothing=0.1 \
        --optimizer-batch-size=1024 \
        --npu=${device_id} > ${train_job_dir}/train_1p.log 2>&1
else
    python3.7 ${currentDir}/DistributedResnet50/main-apex-d76-npu.py \
        --data=${data_url} \
        --addr=${MASTER_ADDR} \
        --seed=49 \
        --workers=128 \
        --learning-rate=${learning_rate} \
        --warmup=8 \
        --label-smoothing=0.1 \
        --mom=0.9 \
        --weight-decay=1.0e-04 \
        --static-loss-scale=128 \
        --print-freq=1 \
        --dist-url='tcp://127.0.0.1:50000' \
        --dist-backend='hccl' \
        --multiprocessing-distributed \
        --world-size=1 \
        --rank=${RANK_INDEX} \
        --benchmark=0 \
        --device='npu' \
        --epochs=${epochs} \
        --device-list=${DEVICE_LIST} \
        --batch-size=${batch_size} > ${train_job_dir}/train_${rank_size}p.log 2>&1
fi


outputDir=$(dirname ${logDir})
modelDir=${outputDir}/model/
mkdir -p ${outputDir}/model/
mv ./*.pth.tar ${modelDir}
