#!/bin/bash


PID=$(ps -eaf | grep python | grep -v grep | awk '{print $2}')

if [[ "" != "$PID" ]]; then
  echo "killing $PID" | tee log
  kill -15 $PID
fi