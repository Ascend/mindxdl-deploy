#!/bin/bash
# default start shell path

CURPATH="$(dirname "$0")"
. ${CURPATH}/cache_util.sh
if [ $# != 3 ] && [ $# != 4] && [ $# != 5 ]
then
    echo "Usage: bash train_start.sh [DATASET_PATH] [CONFIG_PATH] [DEVICE_TARGET] [PRETRAINED_CKPT_PATH](optional)"
    echo "       bash train_start.sh [DATASET_PATH] [CONFIG_PATH] [DEVICE_TARGET] [RUN_EVAL](optional) [EVAL_DATASET_PATH](optional)"
    exit 1
fi

get_real_path(){
  if [ "${1:0:1}" == "/" ]; then
    echo "$1"
  else
    echo "$(realpath -m $PWD/$1)"
  fi
}

PATH1=$(get_real_path $1)
CONFIG_PATH=$(get_real_path $2)
DEVICE_TARGET=$3

if [ $# == 4 ]
then 
    PATH2=$(get_real_path $4)
fi

if [ $# == 5 ]
then
  RUN_EVAL=$4
  EVAL_DATASET_PATH=$(get_real_path $5)
fi

if [ ! -d $PATH1 ]
then
    echo "error: DATASET_PATH=$PATH1 is not a directory"
    exit 1
fi

if [ $# == 4 ] && [ ! -f $PATH2 ]
then
    echo "error: PRETRAINED_CKPT_PATH=$PATH2 is not a file"
    exit 1
fi

if [ "x${RUN_EVAL}" == "xTrue" ] && [ ! -d $EVAL_DATASET_PATH ]
then
    echo "error: EVAL_DATASET_PATH=$EVAL_DATASET_PATH is not a directory"
    exit 1
fi

if [ "x${RUN_EVAL}" == "xTrue" ]
then
  bootup_cache_server
  CACHE_SESSION_ID=$(generate_cache_session)
fi

if [ ${MS_ROLE} == "MS_SCHED" ]
then
    rm -rf ./sched
    mkdir ./sched
    cp ../config/*.yaml ./sched
    cp ../*.py ./sched
    cp ./*.sh ./sched
    cp -r ../src ./sched
    cd ./sched || exit
    echo "start scheduler"
    export DEVICE_ID=0
    if [ $# == 3 ]
    then 
        python train.py --run_distribute=True --device_num=8 --data_path=$PATH1 --parameter_server=False --device_target=$DEVICE_TARGET --config=$CONFIG_PATH --output_path './output'	&& tee ./sched.log 
    fi
    if [ $# == 4 ]
    then
        python train.py --run_distribute=True --device_num=8 --data_path=$PATH1 --parameter_server=False --device_target=$DEVICE_TARGET --config=$CONFIG_PATH --pre_trained=$PATH2 --output_path './output'	&& tee sched.log 
    fi
fi

if [ ${MS_ROLE} == "MS_WORKER" ]
then
    echo "start worker"
    start_index=`expr ${MS_NODE_RANK} \* ${MS_LOCAL_WORKER}`
    end_index=`expr ${start_index} + ${MS_LOCAL_WORKER}`
    for((i=${start_index};i<${end_index};i++));
    do
       rm -rf ./worker_$i
       mkdir ./worker_$i
       cp ../config/*.yaml ./worker_$i
       cp ../*.py ./worker_$i
       cp ./*.sh ./worker_$i
       cp -r ../src ./worker_$i
       cd ./worker_$i || exit
       if [ $# == 3 ]
       then 
         if [[ "${i}" -eq 0 ]]
           python train.py --run_distribute=True --device_num=8 --data_path=$PATH1 --parameter_server=False --device_target=$DEVICE_TARGET --config=$CONFIG_PATH --output_path './output'	&& tee worker_$i.log 
         else 
           python train.py --run_distribute=True --device_num=8 --data_path=$PATH1 --parameter_server=False --device_target=$DEVICE_TARGET --config=$CONFIG_PATH --output_path './output'	&> worker_$i.log &		  
         fi
       fi
       if [ $# == 4 ]
       then
         if [[ "${i}" -eq 0 ]]
           python train.py --run_distribute=True --device_num=8 --data_path=$PATH1 --parameter_server=False --device_target=$DEVICE_TARGET --config=$CONFIG_PATH --pre_trained=$PATH2 --output_path './output'	&& tee worker_$i.log 
         else
           python train.py --run_distribute=True --device_num=8 --data_path=$PATH1 --parameter_server=False --device_target=$DEVICE_TARGET --config=$CONFIG_PATH --pre_trained=$PATH2 --output_path './output'	&> worker_$i.log & 
         fi
       fi
       cd ..
    done
fi