#!/bin/bash

set -e
current_dir=$(cd $(dirname $0); pwd)
. $current_dir/utils.sh

ansible-playbook -i $inventory_file_path $inventory_file_dir/renew_k8s_certs/renew_k8s_certs.yaml -vv