#!/bin/bash
set -e

# create soft link for ubuntu image
os="$(cat /etc/*release* | grep -i "ubuntu")"
if [[ "$os" != "" ]]
then
    echo -e "[INFO]\t $(date +"%F %T:%N")\t use ubuntu image, so create soft link \"/lib64\" for \"/lib\""
    ln -s /lib /lib64 2>&1 >> /dev/null
fi

umask 027

echo -e "[INFO]\t $(date +"%F %T:%N")\t create driver's related directory"
mkdir -p /var/dmp
mkdir -p /home/drv/hdc_ppc
mkdir -p /usr/slog

export LD_LIBRARY_PATH=/usr/local/lib:/usr/local/Ascend/driver/lib64/driver:/usr/local/Ascend/driver/lib64/common:/usr/local/Ascend/add-ons:/usr/local/Ascend/driver/lib64:/usr/local/dcmi
export TMOUT=0
# log process run in background
echo -e "[INFO]\t $(date +"%F %T:%N")\t start slogd server in background"
/var/slogd &
echo -e "[INFO]\t $(date +"%F %T:%N")\t start dmp_daemon server in background"
# dcmi interface process run in background
/var/dmp_daemon -I -U 8087 &

# the host is openEuler, so the parameters "endpoint" and "containerd" are set to adapt to "-containerMode=docker" in default
# in openEuler os, the path of parameters "endpoint" and "containerd" are not in the default place
echo -e "[INFO]\t $(date +"%F %T:%N")\t start npu-exporter server"
/usr/local/bin/npu-exporter -port=8082 -ip=0.0.0.0 -updateTime=5 -logFile=/var/log/mindx-dl/npu-exporter/npu-exporter.log -logLevel=0 -containerMode=docker -endpoint=/run/dockershim.sock -containerd=/run/docker/containerd/containerd.sock

