#!/bin/bash

umask 007
currentDir=$(dirname "$0")
cd "${currentDir}" || exit

#--------------------------------------- 用户需要修改的部分 start --------------------------------------
EPOCHS=1
BATCH_SIZE=256
LEARNING_RATE=2.048
#--------------------------------------- 用户需要修改的部分 end ----------------------------------------

# Parse parameters
device_id=$1
device_list=$2
rank_size=$3
rank_index=$4
log_id=$5
cluster=$6

model_name="resnet50"

output_dir="/job/output/pytorch"
log_dir="${output_dir}"/logs
model_dir="${output_dir}"/model
train_job_dir=${log_dir}/result/"${model_name}"/training_job_${log_id}
data_url='/job/data'


function set_environment_variables()
{
    export LD_LIBRARY_PATH="/usr/local/bin:/usr/local/lib/python3.7/dist-packages/torch/lib:\
/usr/local/Ascend/nnae/latest/fwkacllib/lib64:/usr/local/Ascend/driver/lib64/common/:\
/usr/local/Ascend/driver/lib64/driver/:/usr/local/Ascend/add-ons/"
    export PYTHONPATH="$PYTHONPATH:/usr/local/Ascend/nnae/latest/fwkacllib/python/site-packages:\
/usr/local/Ascend/tfplugin/latest/tfplugin/python/site-packages:/code:{CURRENT_PATH}/code:\
/usr/local/Ascend/nnae/latest/fwkacllib/python/site-packages/auto_tune.egg:\
/usr/local/Ascend/nnae/latest/fwkacllib/python/site-packages/schedule_search.egg"
    export PATH=$PATH:/usr/local/Ascend/nnae/latest/fwkacllib/ccec_compiler/bin
    export ASCEND_OPP_PATH=/usr/local/Ascend/nnae/latest/opp
    export ASCEND_AICPU_PATH=/usr/local/Ascend/nnae/latest

    export ASCEND_SLOG_PRINT_TO_STDOUT=0
    export TASK_QUEUE_ENABLE=1

    export DEVICE_ID=$device_id
    export DEVICE_LIST=$device_list
    export RANK_SIZE=${rank_size}
    export RANK_INDEX=${rank_index}
    export DEVICE_INDEX=$(( DEVICE_ID + RANK_INDEX * 8 ))

    if [ x"${RANK_SIZE}" != x"1" ]; then
      export WHICH_OP=GEOP
      export NEW_GE_FE_ID=1
      export GE_AICPU_FLAG=1
    fi
}

function pre_process()
{
    mkdir -p "${train_job_dir}"
    mkdir -p "${model_dir}"
    chmod -R 750 "${output_dir}"

    device_count=$(( rank_size / WORLD_SIZE ))
    env > ${log_dir}/"${log_id}"/env_${device_count}.log
}

function train()
{
    if [ x"${cluster}" = x"True" ];then
        python3.7 "${currentDir}"/DistributedResnet50/main_apex_d76_npu.py \
            --data=${data_url} \
            --addr="${MASTER_ADDR}" \
            --seed=49 \
            --workers=128 \
            --learning-rate=${LEARNING_RATE} \
            --warmup=8 \
            --label-smoothing=0.1 \
            --mom=0.9 \
            --weight-decay=1.0e-04 \
            --static-loss-scale=128 \
            --print-freq=1 \
            --dist-url='tcp://127.0.0.1:50000' \
            --dist-backend='hccl' \
            --multiprocessing-distributed \
            --world-size="${WORLD_SIZE}" \
            --rank="${rank_index}" \
            --benchmark=0 \
            --device-list="${device_list}" \
            --device='npu' \
            --epochs=${EPOCHS} \
            --batch-size=${BATCH_SIZE} > "${train_job_dir}"/train_"${rank_size}"p.log 2>&1
    elif [ x"${rank_size}" = x"1" ];then
        python3.7 "${currentDir}"/pytorch_resnet50_apex.py \
            "--data=${data_url}" \
            --workers=64 \
            --epochs=${EPOCHS} \
            --batch-size=${BATCH_SIZE} \
            --learning-rate=${LEARNING_RATE} \
            --warmup=5 \
            --label-smoothing=0.1 \
            --optimizer-batch-size=1024 \
            --npu="${device_id}" > "${train_job_dir}"/train_1p.log 2>&1
    else
        python3.7 "${currentDir}"/DistributedResnet50/main_apex_d76_npu.py \
            --data=${data_url} \
            --addr="${MASTER_ADDR}" \
            --seed=49 \
            --workers=128 \
            --learning-rate=${LEARNING_RATE} \
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
            --rank="${rank_index}" \
            --benchmark=0 \
            --device='npu' \
            --epochs=${EPOCHS} \
            --device-list="${device_list}" \
            --batch-size=${BATCH_SIZE} > "${train_job_dir}"/train_"${rank_size}"p.log 2>&1
    fi
}

function post_process()
{
    mv ./*.pth.tar "${model_dir}"
    chmod -R 440 "${model_dir}" "${log_dir}"
}

function main()
{
    set_environment_variables
    pre_process
    train
    post_process
}

main
