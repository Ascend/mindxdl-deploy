REPO="registry.aliyuncs.com/google_containers"
NEW="k8s.gcr.io"
PLAT="linux/amd64"

docker pull --platform ${PLAT} ${REPO}/kube-apiserver:v1.19.16
docker pull --platform ${PLAT} ${REPO}/kube-controller-manager:v1.19.16
docker pull --platform ${PLAT} ${REPO}/kube-scheduler:v1.19.16
docker pull --platform ${PLAT} ${REPO}/kube-proxy:v1.19.16
docker pull --platform ${PLAT} ${REPO}/pause:3.2
docker pull --platform ${PLAT} ${REPO}/etcd:3.4.13-0
docker pull --platform ${PLAT} ${REPO}/coredns:1.7.0

docker tag ${REPO}/kube-apiserver:v1.19.16 k8s.gcr.io/kube-apiserver:v1.19.16
docker tag ${REPO}/kube-controller-manager:v1.19.16 k8s.gcr.io/kube-controller-manager:v1.19.16
docker tag ${REPO}/kube-scheduler:v1.19.16 k8s.gcr.io/kube-scheduler:v1.19.16
docker tag ${REPO}/kube-proxy:v1.19.16 k8s.gcr.io/kube-proxy:v1.19.16
docker tag ${REPO}/pause:3.2 k8s.gcr.io/pause:3.2
docker tag ${REPO}/etcd:3.4.13-0 k8s.gcr.io/etcd:3.4.13-0
docker tag ${REPO}/coredns:1.7.0 k8s.gcr.io/coredns:1.7.0

docker save k8s.gcr.io/kube-apiserver:v1.19.16          -o kube-apiserver_v1.19.16.tar
docker save k8s.gcr.io/kube-controller-manager:v1.19.16 -o kube-controller-manager_v1.19.16.tar
docker save k8s.gcr.io/kube-scheduler:v1.19.16          -o kube-scheduler_v1.19.16.tar
docker save k8s.gcr.io/kube-proxy:v1.19.16              -o kube-proxy_v1.19.16.tar
docker save k8s.gcr.io/pause:3.2                        -o pause_3.2.tar
docker save k8s.gcr.io/etcd:3.4.13-0                    -o etcd_3.4.13-0.tar
docker save k8s.gcr.io/coredns:1.7.0                    -o coredns_1.7.0.tar
