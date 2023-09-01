#!/bin/bash

source rank_table.sh

proc_num=`ls /dev/davinci*|grep -v manager | wc -l`

if [[ $LOCAL_WORLD_SIZE ]]; then
    proc_num=${LOCAL_WORLD_SIZE}
else
    # 获取hccl.json中的device_count字段
    device_count=$(cat "${RANK_TABLE_FILE}" | grep -o device_id | wc -l)
    if [[ "${device_count}" -eq 0 ]]; then
      echo "device count is 0, prestop job failed." | tee hccl.log
      exit 1
    fi
    # 获取hccl.json中的server_count字段
    server_count=$(get_json_value ${RANK_TABLE_FILE} server_count)
    if [[ "${server_count}" == "" ]]; then
      echo "server count is 0, prestop job failed." | tee hccl.log
      exit 1
    fi
    proc_num=$((device_count / server_count))
fi


PID=$(ps -eaf | grep python | grep -v grep | grep -v semaphore_tracker |head -n `expr $proc_num + 1` | tail -n $proc_num| awk '{print $2}')

if [[ "" != "$PID" ]]; then
  echo "killing $PID" | tee log
  kill -15 $PID
fi