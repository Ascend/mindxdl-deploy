files="
kubectl_1.22.1-00_amd64_2a00cd912bfa610fe4932bc0a557b2dd7b95b2c8bff9d001dc6b3d34323edf7d.deb
kubectl_1.22.1-00_arm64_299daf26b0c64b8688f7de4e5a2dcf87d318eb8754f86a1939752a26cbc92cb5.deb
kubelet_1.22.1-00_amd64_240cc59b5f8e44719af21b90161d32297679376f5a4d45ffd4795685ef305538.deb
kubelet_1.22.1-00_arm64_e0314893123e6467c7d8b8e97928c817a2aec9382566e06659617ff279b6cbe9.deb
kubeadm_1.22.1-00_amd64_2e8580f3165ea2f19ba84ac4237dad873cc9915214b3f8f5ca2e98c7a8ecd3e1.deb
kubeadm_1.22.1-00_arm64_03dfc7865355cbdb0fbfa83e74a0fafd41b57455086942ede4e5d1ef9186d9dc.deb
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
