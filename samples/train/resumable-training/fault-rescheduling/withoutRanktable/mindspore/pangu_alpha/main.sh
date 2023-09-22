#!/bin/bash


ulimit -u unlimited
ROOT_PATH=$(cd "`dirname $0`" || exit; pwd)
export REPEAT_TUNE=false
export TE_PARALLEL_COMPILER=10
export ENABLE_TUNE_BANK=True
export MS_COMM_COMPILER_OPT=5000
export MS_COMPILER_CACHE_PATH=/job/code


if [[ "${MS_ROLE}" == "MS_SCHED" ]]; then
  if [ $# == 4 ]; then
      RANK_SIZE=$1
      device_each_server=$2
      SERVER_ID=$3
      rank_start=$((${device_each_server} * SERVER_ID))
      data_path=$4
      export DEVICE_ID=0
      group_info_dir=./group_info.pb
      group_info_file_tmp=$(realpath $group_info_dir)
      export GROUP_INFO_FILE=${group_info_file_tmp}
      echo "start training for scheduler"
      env > env.log
      python ${ROOT_PATH}/../train.py --distribute=true --device_num=${device_each_server} --data_url=${data_path} --run_type=train --param_init_type=fp16 --mode=2.6B | tee log
      done
  else
      echo "Invalid input parameter, usage: main.sh device_count server_count RANK_TABLE_FILE server_id dataset" | tee log
      exit 1
  fi
fi

if [[ "${MS_ROLE}" == "MS_WORKER" ]]; then
  # 单机多卡和分布式
  if [ $# == 4 ]; then
      RANK_SIZE=$1
      device_each_server=$2
      SERVER_ID=$3
      rank_start=$((${device_each_server} * SERVER_ID))
      data_path=$4
      # 先启动后台任务，最后留一个前台任务查看日志输出
      for((i=$((${device_each_server}-1)); i>=0; i--))
      do
          rankid=$((rank_start + i))
          export DEVICE_ID=${i}
          export RANK_ID=${rankid}
          export MS_NODE_ID=${rankid}
          mkdir -p ${ROOT_PATH}/../device$rankid
          cd ${ROOT_PATH}/../device$rankid || exit
          group_info_dir=./group_info.pb
          group_info_file_tmp=$(realpath $group_info_dir)
          export GROUP_INFO_FILE=${group_info_file_tmp}
          echo "start training for rank ${RANK_ID}, device ${DEVICE_ID}"
          env > env.log
          if [ $i -eq 0 ]; then
            python ${ROOT_PATH}/../train.py --distribute=true --device_num=${device_each_server} --data_url=${data_path} --run_type=train --param_init_type=fp16 --mode=2.6B |& tee log
            ST=${PIPESTATUS[0]}
            if [[ ${ST} -ne 0 ]]; then
                echo "running job failed." | tee -a log
                chmod 440 log
                exit ${ST}
            fi
          else
            python ${ROOT_PATH}/../train.py --distribute=true --device_num=${device_each_server} --data_url=${data_path} --run_type=train --param_init_type=fp16 --mode=2.6B &> log &
          fi
      done
  else
      echo "Invalid input parameter, usage: main.sh device_count server_count RANK_TABLE_FILE server_id dataset" | tee log
      exit 1
  fi
fi
wait
