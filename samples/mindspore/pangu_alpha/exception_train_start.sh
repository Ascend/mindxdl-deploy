ROOT_PATH=$(cd "`dirname $0`" || exit; pwd)

python /job/get_fault_ranks_timestamp.py

if [ $? -eq 0 ]; then
    source /job/code/restore_ranks.sh
#    rm -f /job/code/restore_ranks.sh
    if [ $? -eq 0 ]; then
      export RESTORE_RANKS=""
      export RESTORE_RANKS_MAP=""
      cd ${ROOT_PATH} || exit
      bash train_start.sh
    else
      cd ${ROOT_PATH} || exit
      bash train_start.sh
    fi
else
  cd ${ROOT_PATH} || exit
  bash train_start.sh
fi
