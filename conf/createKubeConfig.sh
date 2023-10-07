#! /bin/bash
#  Copyright (C)  2021-2023. Huawei Technologies Co., Ltd. All rights reserved.
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
set -e
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
  #noded
  kubectl delete clusterrolebinding noded-clusterrolebinding || true
  kubectl create clusterrolebinding noded-clusterrolebinding --clusterrole=noded-role \
  --user=noded
  #resilience-controller
  kubectl delete clusterrolebinding resilience-controller-clusterrolebinding || true
  kubectl create clusterrolebinding resilience-controller-clusterrolebinding --clusterrole=resilience-controller-role \
  --user=resilience-controller
}

function createRole() {
  #noded
  kubectl delete clusterrole noded-role || true
  kubectl create clusterrole noded-role --verb=patch --resource=nodes/status
  #resilience-controller
  kubectl delete clusterrole resilience-controller-role || true
  creatRCRole
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

function creatRCRole() {
    cat <<EOF | kubectl apply -f -
kind: ClusterRole
apiVersion: rbac.authorization.k8s.io/v1
metadata:
  name: resilience-controller-role
rules:
  - apiGroups: [""]
    resources: ["pods"]
    verbs: ["get", "list"]
  - apiGroups: [""]
    resources: ["nodes"]
    verbs: ["list"]
  - apiGroups: ["batch.volcano.sh"]
    resources: ["jobs"]
    verbs: ["get", "list", "create", "watch", "delete"]
  - apiGroups: [""]
    resources: ["configmaps"]
    verbs: ["get"]
EOF
}

echo "start to create kubeconfig files for MindXDL"
init
createKubeConfig $1 noded
createKubeConfig $1 resilience-controller
clean
echo "kubeconfig files create successfully"
createRole
echo "clusterrole create successfully"
createRoleBinding
echo "createRoleBinding create successfully"
echo "finish! config file is in $(pwd)"
ls -al $(pwd)
