#!/bin/bash
# hccl-controller组件生成的rank_table_file
export RANK_TABLE_FILE=/user/serverid/devindex/config/hccl.json

# 解析rank_table_file
function get_json_value()
{
  local json=$1
  local key=$2

  if [[ -z "$3" ]]; then
    local num=1
  else
    local num=$3
  fi

  local value=$(cat "${json}" | awk -F"[,:}]" '{for(i=1;i<=NF;i++){if($i~/'${key}'\042/){print $(i+1)}}}' |
                tr -d '"' | sed -n ${num}p)
  echo "${value}"
}

# 检查rank_table_file文件状态
function check_hccl_status()
{
    local retry_times=60
    local retry_interval=5
    for (( n=1;n<=$retry_times;n++ ));do
    {
        local status=$(get_json_value ${RANK_TABLE_FILE} status)
        if [[ "$status" != "completed" ]]; then
            echo "hccl status is not completed, wait 5s and retry." | tee -a hccl.log
            sleep ${retry_interval}
            continue
        else
            return 0
        fi
    }
    done
    return 1
}

function get_server_id()
{
    local key="server_id"
    local srv_id=$(cat ${RANK_TABLE_FILE} | awk -F"[,:}]" '{for(i=1;i<=NF;i++){if($i~/'${key}'\042/){print $(i+1)}}}' |
                   awk '{print FNR ":" $1}' | grep -w ${XDL_IP} | awk -F ":" '{print $1}')
    if [[ -z $srv_id || $srv_id -lt 1 ]];then
        return 1
    fi
    srv_id=$(($srv_id-1))
    echo ${srv_id}
}

function get_server_id_0_ip()
{
    local key="server_id"
    local first_server_ip=$(cat ${RANK_TABLE_FILE} |awk -F ',' {for(i=1;i<NF;i++){print $i} | grep -w "server_id"|
    head -1 | cut -d ":" -f2 | sed 's/"//g'| sed 's/}//g' 
    echo ${first_server_ip}
}