#!/bin/bash
readonly TRUE=1
readonly FALSE=0
readonly kernel_version=$(uname -r)
readonly arch=$(uname -m)
readonly BASE_DIR=$(cd "$(dirname $0)" > /dev/null 2>&1; pwd -P)
readonly PYLIB_PATH=${BASE_DIR}/resources/pylibs

function get_os_name()
{
    local os_name=$(grep -oP "^ID=\"?\K\w+" /etc/os-release)
    echo ${os_name}
}

readonly g_os_name=$(get_os_name)

function get_os_version()
{
    local os_version=$(grep -oP "^VERSION_ID=\"?\K\w+\.?\w*" /etc/os-release)
    echo ${os_version}
    return
}
function install_ansible()
{
    local have_ansible_cmd=$(command -v ansible | wc -l)
    if [[ ${have_ansible_cmd} == 0 ]];then
        export DEBIAN_FRONTEND=noninteractive
        export DEBIAN_PRIORITY=critical
        echo "dpkg -i --force-all resources/${os_name}_${os_version}_${arch}/python/*.deb"
        dpkg -i --force-all resources/${os_name}_${os_version}_${arch}/python/*.deb
        python3 -m pip install --upgrade pip --no-index --find-links resources/pylibs
        python3 -m pip install ansible --no-index --find-links resources/pylibs
    fi
}

function main()
{
    local os_name=$(get_os_name)
    local os_version=$(get_os_version)
    echo "OS=${os_name}"
    echo "OS=${os_version}"
    if [ ! -d ~/.ansible/roles ];then
        mkdir -p ~/.ansible/roles
    fi
    cp -rf playbooks/roles/* ~/.ansible/roles/
}

main $*
