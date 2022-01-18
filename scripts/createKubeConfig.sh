#! /bin/bash
#  Copyright (C)  2021. Huawei Technologies Co., Ltd. All rights reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

# run this shell like this : bash createKubeConfig.sh https://masterip:port
if [ $# = 0 ]; then
  echo "please input the kube-apiserver ip, like https://127.0.0.1:6443"
  exit 0
fi

function createCRT() {
  cd /etc/kubernetes/mindxdl
  openssl genrsa -out $1.key 2048
  openssl req -new -key $1.key -out $1.csr -subj "/CN=$1/O=k8s"
  openssl x509 -req -in $1.csr -CA /etc/kubernetes/pki/ca.crt -CAkey /etc/kubernetes/pki/ca.key -CAcreateserial -out $1.crt -days 1000

}

function createKubeConfig() {
  createCRT $2
  kubectl config set-cluster kubernetes \
  --certificate-authority=/etc/kubernetes/pki/ca.crt \
  --embed-certs=true \
  --server=$1 \
  --kubeconfig=$2-cfg.conf

  kubectl config set-credentials $2 \
  --client-certificate=/etc/kubernetes/mindxdl/$2.crt \
  --client-key=/etc/kubernetes/mindxdl/$2.key \
  --embed-certs=true \
  --kubeconfig=$2-cfg.conf

  kubectl config set-context $2-context \
  --cluster=kubernetes \
  --user=$2 \
  --kubeconfig=$2-cfg.conf

  kubectl config use-context $2-context --kubeconfig=$2-cfg.conf

}

function createRoleBinding() {
  #task-manager
  kubectl delete clusterrolebinding task-manager-clusterrolebinding || true
  kubectl create clusterrolebinding task-manager-clusterrolebinding --clusterrole=task-manager-role \
  --user=task-manager
  #hccl-controller
  kubectl delete clusterrolebinding hccl-controller-clusterrolebinding || true
  kubectl create clusterrolebinding hccl-controller-clusterrolebinding --clusterrole=hccl-controller-role \
  --user=hccl-controller
  #device-plugin
  kubectl delete clusterrolebinding device-plugin-clusterrolebinding || true
  kubectl create clusterrolebinding device-plugin-clusterrolebinding --clusterrole=device-plugin-role \
  --user=device-plugin
  #noded
  kubectl delete clusterrolebinding noded-clusterrolebinding || true
  kubectl create clusterrolebinding noded-clusterrolebinding --clusterrole=noded-role \
  --user=noded

}

function createRole() {
  #task-manager
  kubectl delete clusterrole task-manager-role || true
  kubectl create clusterrole task-manager-role --verb=* --resource=pods,pods/log,services,networkpolicies.networking.k8s.io,podgroups.scheduling.volcano.sh,deployments.apps,horizontalpodautoscalers.autoscaling
  #hccl-controller
  kubectl delete clusterrole hccl-controller-role || true
  kubectl create clusterrole hccl-controller-role --verb=get,list,update,watch --resource=jobs.batch.volcano.sh,pods,deployments.apps,configmaps
  #device-plugin
  kubectl delete clusterrole device-plugin-role || true
  kubectl create clusterrole device-plugin-role --verb=get,list,update,patch --resource=pods,nodes,nodes/status
  #noded
  kubectl delete clusterrole noded-role || true
  kubectl create clusterrole noded-role --verb=patch --resource=nodes/status
}

function init() {
  cd /etc/kubernetes/
  rm -rf /etc/kubernetes/mindxdl
  mkdir /etc/kubernetes/mindxdl
  cd mindxdl
}

function  clean() {
    cd /etc/kubernetes/mindxdl
    rm -rf *.key
    rm -rf *.crt
    rm -rf *.csr

}

echo "start to create kubeconfig files for MindXDL"
init
createKubeConfig $1 task-manager
createKubeConfig $1 hccl-controller
createKubeConfig $1 device-plugin
createKubeConfig $1 noded
clean
echo "kubeconfig files create successfully"
createRole
echo "clusterrole create successfully"
createRoleBinding
echo "createRoleBinding create successfully"
echo "finish! config file is in $(pwd)"
ls -al $(pwd)
