#!/bin/bash
readonly arch=$(uname -m)

function get_os_name()
{
    local os_name=$(grep -oP "^ID=\"?\K\w+" /etc/os-release)
    echo ${os_name}
}

function get_os_version()
{
    local os_version=$(grep -oP "^VERSION_ID=\"?\K\w+\.?\w*" /etc/os-release)
    echo ${os_version}
}

function install_ansible()
{
    local is_ansible_installed=$(checkAnsible)
    if [[ ${is_ansible_installed} != 0 ]];then
        RESOURCE_DIR=~/resources
        if [ ! -d $RESOURCE_DIR ];then
            echo "error: no resource dir $RESOURCE_DIR"
	        return 1
        fi
        echo "resource dir=$RESOURCE_DIR"

        case ${os_name} in
        ubuntu)
            dpkg -i --force-all ~/resources/ansible/Ubuntu_18.04/${arch}/*.deb
            ;;
        openEuler)
            rpm -i --nodeps --force ~/resources/ansible/OpenEuler_${os_version}_LTS/${arch}/*.rpm
            rpm -i ~/resources/basic/OpenEuler_${os_version}_LTS/${arch}/libselinux/*.rpm --nodeps --force
            ;;
        esac
    else
        echo "ansible is already installed"
    fi
    sed -i "s?#gathering = implicit?gathering = smart?" /etc/ansible/ansible.cfg
    sed -i "s?#fact_caching = memory?fact_caching = jsonfile?" /etc/ansible/ansible.cfg
    sed -i "s?#fact_caching_connection=/tmp?fact_caching_connection=/etc/ansible/facts-cache?" /etc/ansible/ansible.cfg

}

function checkAnsible() {
    ansible --version >/dev/null 2>&1
    echo $?
}

function main()
{
    local os_name=$(get_os_name)
    local os_version=$(get_os_version)
    echo "OS NAME=${os_name}"
    echo "OS VERSION=${os_version}"
    install_ansible
}

main $*

