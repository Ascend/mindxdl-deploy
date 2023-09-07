#!/bin/bash

proc_num=`ls /dev/davinci*|grep -v manager | wc -l`

if [[ $LOCAL_WORLD_SIZE ]]; then
    proc_num=${LOCAL_WORLD_SIZE}
fi

PID=$(ps -eaf | grep python | grep -v grep | grep -v semaphore_tracker |head -n `expr $proc_num + 1` | tail -n $proc_num| awk '{print $2}')

if [[ "" != "$PID" ]]; then
  echo "killing $PID" | tee log
  kill -15 $PID
fi