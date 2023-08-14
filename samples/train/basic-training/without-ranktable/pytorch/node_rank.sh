#!/bin/bash
# volcano组件生成的serverList
export NODE_RANK_FILE=/user/serverid/devindex/config/serverList

# 解析serverList
function get_json_value()
{
  local json=$1
  local key=$2
  local num=1

  local value=$(cat "${json}" | awk -F"[,:}]" '{for(i=1;i<=NF;i++){if($i~/'${key}'\042/){print $(i+1)}}}' |
                tr -d '"' | sed -n ${num}p)
  echo "${value}"
}

# 解析rank_table_file
function get_node_rank()
{
  local json=$1
  local server_list=$(cat "${json}")
  if [[ ${server_list} =~ ${XDL_IP} ]]
  then
    local part_server_list=${server_list%${XDL_IP}*}
    local index=$(echo "${part_server_list}" | grep -o "server_ip" | wc -l)
    echo `expr ${index} - 1`
    return
  fi
  echo 0
}

# 设置NODE_RANK环境变量
function set_node_rank_env()
{
    local retry_times=60
    local retry_interval=5
    for (( n=1;n<=$retry_times;n++ ));do
    {
        local status=$(get_json_value ${NODE_RANK_FILE} status)
        if [[ "$status" == "initializing" ]]; then
            echo "node rank status is not completed, wait 5s and retry." | tee -a node_rank.log
            sleep ${retry_interval}
            continue
        else
            local node_rank=$(get_node_rank ${NODE_RANK_FILE})
            export NODE_RANK=${node_rank}
            export MASTER_ADDR=$(get_json_value ${NODE_RANK_FILE} server_ip)
            return 0
        fi
    }
    done
    return 1
}