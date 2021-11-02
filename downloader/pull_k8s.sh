IMG_REPO="registry.aliyuncs.com/google_containers"
ORIGIN_REPO="k8s.gcr.io"
IMG_TAG="v1.19.6"

PLAT="linux/arm64"

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


docker pull --platform ${PLAT} ${IMG_REPO}/pause:3.2
docker tag  ${IMG_REPO}/pause:3.2 ${ORIGIN_REPO}/pause:3.2
docker save ${ORIGIN_REPO}/pause:3.2 -o pause_3.2.tar
echo "pause complete"

docker pull --platform ${PLAT}  ${IMG_REPO}/etcd:3.4.13-0
docker tag  ${IMG_REPO}/etcd:3.4.13-0 ${ORIGIN_REPO}/etcd:3.4.13-0
docker save ${ORIGIN_REPO}/etcd:3.4.13-0 -o etcd_3.4.13-0.tar
echo "etcd complete"

docker pull --platform ${PLAT}  ${IMG_REPO}/coredns:1.7.0
docker tag  ${IMG_REPO}/coredns:1.7.0 ${ORIGIN_REPO}/coredns:1.7.0
docker save ${ORIGIN_REPO}/coredns:1.7.0 -o coredns_1.7.0.tar
echo "coredns complete"
