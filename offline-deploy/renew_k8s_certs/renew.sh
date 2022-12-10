#!/bin/bash

set -e
node_type=$1

if [[ $node_type != "master" ]] && [[ $node_type != "worker" ]]
then
    exit 1
fi

unset http_proxy https_proxy

cd /root/

kubeadm config view > kubeadm.yaml
mkdir /etc/kubernetes.bak || true
cp -rf /etc/kubernetes/pki/ /etc/kubernetes.bak/
cp -f /etc/kubernetes/*.conf /etc/kubernetes.bak/

if [[ $node_type == "master" ]]
then
    cp -rf /var/lib/etcd /var/lib/etcd.bak/
    kubeadm alpha certs renew all --config=kubeadm.yaml
    kubeadm init phase kubeconfig all --config kubeadm.yaml
    cp -f /etc/kubernetes/admin.conf /root/.kube/config
    mv /etc/kubernetes/manifests/ /etc/kubernetes/manifests.bak
    echo "sleep 25s"
    sleep 25
    mv /etc/kubernetes/manifests.bak/ /etc/kubernetes/manifests
    systemctl restart kubelet

else
    kubeadm init phase kubeconfig kubelet --config kubeadm.yaml
fi

echo "renew finished"