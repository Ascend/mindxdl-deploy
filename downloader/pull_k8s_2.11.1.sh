IMG_REPO="registry.aliyuncs.com/google_containers"
ORIGIN_REPO="k8s.gcr.io"
IMG_TAG="v1.22.1"

PLAT="linux/amd64"

docker pull --platform ${PLAT} ${IMG_REPO}/kube-apiserver:${IMG_TAG}
docker tag  ${IMG_REPO}/kube-apiserver:${IMG_TAG} ${ORIGIN_REPO}/kube-apiserver:${IMG_TAG}
docker save ${ORIGIN_REPO}/kube-apiserver:${IMG_TAG} -o kube-apiserver_${IMG_TAG}.tar
echo "kube-apiserver complete"

docker pull --platform ${PLAT} ${IMG_REPO}/kube-controller-manager:${IMG_TAG}
docker tag  ${IMG_REPO}/kube-controller-manager:${IMG_TAG} ${ORIGIN_REPO}/kube-controller-manager:${IMG_TAG}
docker save ${ORIGIN_REPO}/kube-controller-manager:${IMG_TAG} -o kube-controller-manager_${IMG_TAG}.tar
echo "kube-controller-manager complete"

docker pull --platform ${PLAT}  ${IMG_REPO}/kube-proxy:${IMG_TAG}
docker tag  ${IMG_REPO}/kube-proxy:${IMG_TAG} ${ORIGIN_REPO}/kube-proxy:${IMG_TAG}
docker save ${ORIGIN_REPO}/kube-proxy:${IMG_TAG} -o kube-proxy_${IMG_TAG}.tar
echo "kube-proxy complete"

docker pull  --platform ${PLAT} ${IMG_REPO}/kube-scheduler:${IMG_TAG}
docker tag  ${IMG_REPO}/kube-scheduler:${IMG_TAG} ${ORIGIN_REPO}/kube-scheduler:${IMG_TAG}
docker save ${ORIGIN_REPO}/kube-scheduler:${IMG_TAG} -o kube-scheduler_${IMG_TAG}.tar
echo "kube-scheduler complete"


docker pull --platform ${PLAT} ${IMG_REPO}/pause:3.5
docker tag  ${IMG_REPO}/pause:3.5 ${ORIGIN_REPO}/pause:3.5
docker save ${ORIGIN_REPO}/pause:3.5 -o pause_3.5.tar
echo "pause complete"

docker pull --platform ${PLAT}  ${IMG_REPO}/etcd:3.5.0-0
docker tag  ${IMG_REPO}/etcd:3.5.0-0 ${ORIGIN_REPO}/etcd:3.5.0-0
docker save ${ORIGIN_REPO}/etcd:3.5.0-0 -o etcd_3.5.0-0.tar
echo "etcd complete"

docker pull --platform ${PLAT}  ${IMG_REPO}/coredns:1.8.4
docker tag  ${IMG_REPO}/coredns:1.8.4 ${ORIGIN_REPO}/coredns:1.8.4
docker save ${ORIGIN_REPO}/coredns:1.8.4 -o coredns_1.8.4.tar
echo "coredns complete"
