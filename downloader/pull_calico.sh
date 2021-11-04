#IMG_REPO="registry.aliyuncs.com/google_containers"
#IMG_REPO="registry.aliyuncs.com/google_containers"
IMG_REPO="calico"
IMG_TAG="v3.20.2"

PLAT="linux/arm64"

echo "docker pull --platform ${PLAT} ${IMG_REPO}/node:${IMG_TAG}"
docker pull --platform ${PLAT} ${IMG_REPO}/node:${IMG_TAG}
docker save calico/node:${IMG_TAG} -o calico_node_${IMG_TAG}.tar
echo "calico_node complete"

docker pull --platform ${PLAT} ${IMG_REPO}/pod2daemon-flexvol:${IMG_TAG}
docker save calico/pod2daemon-flexvol:${IMG_TAG} -o calico_pod2daemon-flexvol_${IMG_TAG}.tar
echo "pod2daemon-flexvol complete"

docker pull --platform ${PLAT}  ${IMG_REPO}/cni:${IMG_TAG}
docker save calico/cni:${IMG_TAG} -o calico_cni_${IMG_TAG}.tar
echo "calico_cni complete"

docker pull  --platform ${PLAT} ${IMG_REPO}/kube-controllers:${IMG_TAG}
docker save calico/kube-controllers:${IMG_TAG} -o calico_kube-controllers_${IMG_TAG}.tar
echo "kube-scheduler complete"

