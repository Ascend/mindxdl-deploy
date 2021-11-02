files="
kubelet_1.19.6-00_amd64_5b57b709b0bf19ce60743a2e6544e008465f41cb0ced3c7fa41461d32ca95c09.deb
kubelet_1.19.6-00_arm64_ec30957905d4f3c17010d146ded26dfaff2b2f393ba883bcf41610c11bd8429f.deb
kubeadm_1.19.6-00_amd64_90b35c42c58456d3f279e39de53d396fadfc58b8d1b5d61199b7e6d667aec98e.deb
kubeadm_1.19.6-00_arm64_bf97d2f98043cb7da835dba119b8f50b240a0f36a2c16bd3f0214a2ead76c727.deb
kubectl_1.19.6-00_amd64_fd72cd41a4a63616382f808b089ecd0e94b5df38a9c8a2026ef94ceaae177d08.deb
kubectl_1.19.6-00_arm64_fab76a61bfb487cada54a785020e4b92cd9a86f0f5b13478288e2c722ea14a59.deb
"
REPO="https://mirrors.tuna.tsinghua.edu.cn/kubernetes/apt/pool"

if [ ! -d docker/x86_64 ];then
    mkdir -p docker/x86_64
fi

if [ ! -d docker/aarch64 ];then
    mkdir -p docker/aarch64
fi

for f in $files
do
    if [ $f == "*amd64*" ];then
        curl ${REPO}/$f -o docker/x86_64/$f
    else
        curl ${REPO}/$f -o docker/aarch64/$f
    fi
done
