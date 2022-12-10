#!/bin/bash
set -e

current_dir=$(cd $(dirname $0); pwd)
inventory_file_dir=$(cd $current_dir/..; pwd)
inventory_file_path="$inventory_file_dir/inventory_file"
inventory_content="$(cat $inventory_file_path)"

# 检查项1
# 获取harbor server提供的服务类型HTTP还是HTTPS
# 如果没有Harbor服务，playbook会跳过对应逻辑，这里变量不影响playbook执行
harbor_server="$(echo "$inventory_content" | grep -E "^HARBOR_SERVER" | awk -F'=' '{print $2}' | sed "s/\"//g")"
harbor_server_resp=$(curl http://$harbor_server/c/login 2>/dev/null | grep "The plain HTTP request was sent to HTTPS port" | wc -l)
harbor_server_http="true"
if [[ $harbor_server_resp != 0  ]]
then
    harbor_server_http="false"
fi

# 检查项2
scene_num="$(echo "$inventory_content" | grep -E '^SCENE_NUM' | awk -F'=' '{print $2}')"
extra_cpt="$(echo "$inventory_content" | grep -E '^EXTRA_COMPONENT' | awk -F'=' '{print $2}' | sed 's/"//g')"
extra_array=(`echo $extra_cpt | tr ',' ' ' | tr '\"' ' '` )
forbidden_cpt_2=("docker" "k8s")
forbidden_cpt_3=("docker" "k8s" "hccl-controller" "volcano" "noded")
master_num=$(grep -A 100 '\[master\]' inventory_file  | grep -B 200 '\[worker\]' | grep -vE "^#|^\[" | grep -E "^[0-9]" | wc -l)

# 安装K8s时，如果master数量为偶数，报错
if [[ $scene_num == "1" ]] && [[ $(($master_num % 2)) == 0 ]]
then
    echo "[ERROR]\t$(date +"%Y-%m-%d %H:%M:%S")\t in inventory_file, the number of nodes configured under [master] must be odd, such as 1,3,5,7"
    exit 1
fi
# 检查inventory_file中场景（SCENE_NUM）和额外组件（EXTRA_COMPONENT）的配套关系
if [[ $scene_num == "1" ]]
then
    if [[ $extra_cpt != "" ]]
    then
        echo -e "[ERROR] EXTRA_COMPONENT in inventory_file must be empty string when SCENE_NUM=1"
        exit 1
    fi
elif [[ $scene_num == "2" ]] || [[ $scene_num == "3" ]]
then
    for var in ${extra_array[@]}
    do
        if [[ $scene_num == "2" ]] && [[ "${forbidden_cpt_2[@]}" =~ $var ]]
        then
                echo -e "[ERROR]\t$(date +"%Y-%m-%d %H:%M:%S")\t EXTRA_COMPONENT in inventory_file can only be one or more of npu-exporter, noded or hccl-controller when SCENE_NUM=2"
                exit 1
        fi
        if [[ $scene_num == "3" ]] && [[ "${forbidden_cpt_3[@]}" =~ $var ]]
        then
                echo -e "[ERROR]\t$(date +"%Y-%m-%d %H:%M:%S")\t EXTRA_COMPONENT in inventory_file can only be npu-exporter when SCENE_NUM=3"
                exit 1
        fi
    done
fi

# 校验DL包下面的架构对不对
valide_path=("/root/resources/mindxdl/dlPackage/aarch64/" "/root/resources/mindxdl/dlPackage/x86_64/" "/root/resources/mindxdl/baseImages/aarch64" "/root/resources/mindxdl/baseImages/x86_64")
for path in ${valide_path[@]}
do
    arch_str="aarch64"
    if [[ "$(echo $path | grep "aarch64")" != "" ]]
    then
        arch_str="x86_64"
    fi
    arch_err_pkg="$(ls $path | grep "$arch_str" | wc -l)"
    if [[ $arch_err_pkg != 0 ]]
    then
        echo -e "[ERROR]\t$(date +"%Y-%m-%d %H:%M:%S")\t in $path directory, there are some different architecture($arch_str) packages"
        exit 1
    fi

done