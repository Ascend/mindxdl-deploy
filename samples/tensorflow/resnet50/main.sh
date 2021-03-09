#!/bin/sh

# 应用权限配置umask 007
umask 007
currentDir=$(cd "$(dirname "$0")"; pwd)
cd ${currentDir}

if [ -d /usr/local/Ascend/nnae/latest ];then
    export LD_LIBRARY_PATH=/usr/local/:/usr/local/lib/:/usr/lib/:/usr/local/Ascend/nnae/latest/fwkacllib/lib64:/usr/local/Ascend/driver/lib64/common/:/usr/local/Ascend/driver/lib64/driver/:/usr/local/Ascend/add-ons/:/usr/local/Ascend/driver/tools/hccn_tool/:/usr/local/mpirun4.0/lib
    export PYTHONPATH=$PYTHONPATH:/usr/local/Ascend/tfplugin/latest/tfplugin/python/site-packages:/usr/local/Ascend/nnae/latest/opp/op_impl/built-in/ai_core/tbe:/usr/local/Ascend/nnae/latest/fwkacllib/python/site-packages/:/usr/local/Ascend/tfplugin/latest/tfplugin/python/site-packages
    export PATH=$PATH:/usr/local/Ascend/nnae/latest/fwkacllib/ccec_compiler/bin:/usr/local/mpirun4.0/bin
    export ASCEND_OPP_PATH=/usr/local/Ascend/nnae/latest/opp
else
    export LD_LIBRARY_PATH=/usr/local/lib/:/usr/lib/:/usr/local/Ascend/ascend-toolkit/latest/fwkacllib/lib64:/usr/local/Ascend/driver/lib64/common/:/usr/local/Ascend/driver/lib64/driver/:/usr/local/Ascend/add-ons/:/usr/local/mpirun4.0/lib
    export PYTHONPATH=$PYTHONPATH:/usr/local/Ascend/tfplugin/latest/tfplugin/python/site-packages:/usr/local/Ascend/ascend-toolkit/latest/opp/op_impl/built-in/ai_core/tbe:/usr/local/Ascend/ascend-toolkit/latest//fwkacllib/python/site-packages/:/usr/local/Ascend/ascend-toolkit/latest/tfplugin/python/site-packages:$projectDir
    export PATH=$PATH:/usr/local/Ascend/ascend-toolkit/latest/fwkacllib/ccec_compiler/bin:/usr/local/mpirun4.0/bin
    export ASCEND_OPP_PATH=/usr/local/Ascend/ascend-toolkit/latest/opp/
fi

export SOC_VERSION=Ascend910
export HCCL_CONNECT_TIMEOUT=600
export JOB_ID=123456789
export RANK_TABLE_FILE=/user/serverid/devindex/config/hccl.json

# profiling env
export PROFILING_MODE=false
export AICPU_PROFILING_MODE=false
export PROFILING_OPTIONS=training_trace
export FP_POINT=resnet_model/conv2d/Conv2Dresnet_model/batch_normalization/FusedBatchNormV3_Reduce
export BP_POINT=gradients/AddN_70
# system env
ulimit -c unlimited


device_id=$1
export DEVICE_ID=${device_id}

device_count=$2
export RANK_SIZE=${device_count}

pod_name=$3
export RANK_ID=${pod_name}
export RANK_INDEX=${pod_name}
export PROFILING_DIR=/var/log/npu/profiling/container/${RANK_ID}

DEVICE_INDEX=${RANK_ID}
export DEVICE_INDEX=${DEVICE_INDEX}

log_id=$4
env > ${currentDir}/result/${log_id}/env_${device_id}.log


mkdir -p /var/log/npu/profiling/container/${RANK_ID} 1>/dev/null 2>&1

first_card=$5
pod_id=$6
model_dir="/job/output/logs/${pod_id}/ckpt${device_id}"
if [ "$first_card" = "true" ]; then
    model_dir="/job/output/logs/${pod_id}/ckpt_first"
fi

# CPU核心数
core_num=`cat /proc/cpuinfo | grep "processor" | wc -l`
# 设置绑定范围，如:0-11
core_range="$((device_id*${core_num}/8))-$(((device_id+1)*${core_num}/8-1))"
#--------------------------------------- 用户需要修改的部分 start --------------------------------------
# 核绑定
taskset -c ${core_range} \
python3.7 /job/code/ModelZoo_Resnet50_HC/code/resnet50_train/mains/res50.py \
    --config_file=res50_256bs_1p \
    --max_train_steps=1000 \
    --iterations_per_loop=100 \
    --debug=True \
    --eval=False \
    --model_dir=${model_dir} \
    | tee -a ${currentDir}/result/${log_id}/train_${device_id}.log 2>&1

# 参数说明：
# config_file: 使用的配置文件名称，对应文件在code/resnet50_train/configs下
# max_train_steps: 学习率相关，训练总步数，由样本数、batch_size和命令行参数num_train_epoches轮数计算所得
# iterations_per_loop：针对一次session.run调用（每个训练循环）运行的迭代次数
# debug：debug开关
# eval：训练完成后是否做评估
# model_dir：生成的模型保存目录

cd ${model_dir}
python3.7 /usr/local/lib/python3.7/dist-packages/tensorflow_core/python/tools/freeze_graph.py \
    --input_checkpoint=./model.ckpt-1000 \
    --output_graph=/job/output/model/resnet50_final.pb \
    --output_node_names=fp32_vars/final_dense \
    --input_graph=graph.pbtxt

# 参数说明：
# input_checkpoint：保存的checkpoint文件名称
# output_graph：保存的pb文件
# output_node_names：保存pb指定的输出节点名称
# input_graph：输入的pbtxt文件名称

#--------------------------------------- 用户需要修改的部分 end ----------------------------------------
