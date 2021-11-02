#IMG_REPO="registry.aliyuncs.com/google_containers"
#IMG_REPO="registry.aliyuncs.com/google_containers"
IMG_REPO="calico"
IMG_TAG="v3.8.9"

PLAT="linux/amd64"

echo "docker pull --platform ${PLAT} ${IMG_REPO}/node:${IMG_TAG}"
docker pull --platform ${PLAT} ${IMG_REPO}/node:${IMG_TAG}
#docker tag  ${IMG_REPO}/node:${IMG_TAG} calico_node:${IMG_TAG}
echo "calico_node complete"

docker pull --platform ${PLAT} ${IMG_REPO}/pod2daemon-flexvol:${IMG_TAG}
#docker tag  ${IMG_REPO}/pod2daemon-flexvol:${IMG_TAG} pod2daemon-flexvol:${IMG_TAG}
echo "pod2daemon-flexvol complete"

docker pull --platform ${PLAT}  ${IMG_REPO}/cni:${IMG_TAG}
#docker tag  ${IMG_REPO}/cni:${IMG_TAG} calico_cni:${IMG_TAG}
echo "calico_cni complete"

docker pull  --platform ${PLAT} ${IMG_REPO}/kube-controllers:${IMG_TAG}
#docker tag  ${IMG_REPO}/kube-controllers:${IMG_TAG} calico_kube-controllers:${IMG_TAG}
echo "kube-scheduler complete"

docker save calico/node:${IMG_TAG}               -o calico_node_${IMG_TAG}.tar
docker save calico/pod2daemon-flexvol:${IMG_TAG} -o calico_pod2daemon-flexvol_${IMG_TAG}.tar
docker save calico/cni:${IMG_TAG}                -o calico_cni_${IMG_TAG}.tar
docker save calico/kube-controllers:${IMG_TAG}   -o calico_kube-controllers_${IMG_TAG}.tar
