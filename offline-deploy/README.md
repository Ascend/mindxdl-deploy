# 快速入门

本文主要介绍如何使用ansible安装MindX DL软件及其依赖的开源软件

# 版本说明

| 版本 | 版本说明                                                     |
| ---- | ------------------------------------------------------------ |
| V1.0 | 1.支持离线安装docker,kubernetes集群(含高可用kubernetes集群),MindX DL基础组件<br />2.支持在centos7.6和ubuntu 18.04上安装上述软件<br />3.在1点中的安装中，支持全量和部分安装两种安装方式 |



## 软件描述

本文主要介绍如何使用ansible安装MindX DL所需开源软件安装。其中包含如下开源软件

| 软件名        | 备注                    |
| ---------- | -------------------------|
| docker     | 集群中所有节点都需要安装   |
| kubernetes | k8s平台                  |
| Ascend-Device-Plugin | mindx-dl基础组件 |
| NodeD | mindx-dl基础组件 |
| Volcano | mindx-dl基础组件 |
| Npu-Exporter | mindx-dl基础组件 |
| HCCL-Controller | mindx-dl基础组件 |

## 环境要求

### 支持的操作系统说明

| 操作系统   | 版本   | CPU架构 |
|:------:|:---------:|:-------:|
| Ubuntu | 18.04 | aarch64 |
| Ubuntu | 18.04 | x86_64  |
| CentOS | 7.6 | aarch64 |
| CentOS | 7.6 | x86_64 |

根目录的磁盘空间利用率高于85%会触发Kubelet的镜像垃圾回收机制，将导致服务不可用。请确保根目录有足够的磁盘空间，建议大于1 TB**

### 支持的硬件形态说明

| 中心推理硬件    | 中心训练硬件|
|:--------------:|:----------:|
| A300-3000      | A300T-9000 |
| A300-3010      | A800-9000  |
| Atlas 300I Pro | A800-9010  |
| A800-3000      |            |
| A800-3010      |            |

请先安装NPU硬件对应的驱动和固件，才能构建昇腾NPU的训练和推理任务。安装文档[链接](https://support.huawei.com/enterprise/zh/category/ascend-computing-pid-1557196528909)

## 下载本工具

1.下载批量部署脚本，可使用git clone和下载zip方法，下载地址为：[Ascend/mindxdl-deploy](https://gitee.com/ascend/mindxdl-deploy)。，请放置在/root目录下，安装部署脚本在master分支的offline-deploy目录下。

2.然后获得开源软件的[resources.tar.gz](https://cann-camp.obs.cn-north-4.myhuaweicloud.com:443/resources.tar.gz?AccessKeyId=JVGDRD4RF2155LDZKGSV&Expires=1696757752&Signature=3DrHcy3MWqYXXFS66SZe46mWoys%3D)离线安装包，将离线安装包解压在/root目录下。按如下方式放置

```bash
root@master:~# ls
mindxdl-deploy
resources             //由resources.tar.gz解压得到，必须放置在/root目录下
resources.tar.gz
```

## 安装步骤

### 步骤1：安装ansible

如果已安装ansible，请跳过这一步骤：

```bash
#进入到ansible的安装目录，其中${osName_version_arch}为对应操作系统依赖包目录
cd ~/resources/ansible/${osName_version_arch}

#安装ansible，使用对应操作系统命令
dpkg -i --force-all *.deb #Ubuntu使用dpkg安装
rpm -i *.rpm --nodeps --force #CentOS使用rpm安装

#查看ansible是否成功安装
ansible --version
#输出以下内容表示成功安装
ansible 2.9.27
  config file = /etc/ansible/ansible.cfg
  configured module search path = [u'/root/.ansible/plugins/modules', u'/usr/share/ansible/plugins/modules']
  ansible python module location = /usr/lib/python2.7/dist-packages/ansible
  executable location = /usr/bin/ansible
  python version = 2.7.17 (default, Jul  1 2022, 15:56:32) [GCC 7.5.0]


#修改ansible配置文件，将获取到的主机信息保存在本地缓存
sed -i "s?#gathering = implicit?gathering = smart?" /etc/ansible/ansible.cfg 
sed -i "s?#fact_caching = memory?fact_caching = jsonfile?" /etc/ansible/ansible.cfg
sed -i "s?#fact_caching_connection=/tmp?fact_caching_connection=/etc/ansible/facts-cache?" /etc/ansible/ansible.cfg
```

### 步骤2：配置集群信息

修改配置文件参数，必须添加apiserver的ip地址，ip地址为master地址，其他配置，用户可自行设置

```bash
root@ubuntu-1:~/mindxdl-deploy/offline-deploy# vi inventory_file
```

参考配置如下，请根据各个参数说明自行修改


```ini
# 以下为全局变量配置区域
[all:vars]
KUBE_VIP="192.0.3.120"
POD_NETWORK_CIDR="100.100.0.0/16"
INSTALL_COMPONENT="mindxdl,docker,k8s"

[master]
localhost ansible_connection=local  set_hostname="master"  kube_interface="enp125s0f0" k8s_api_server_ip="192.0.3.100"

[worker]
192.0.3.103  set_hostname="worker-1"
192.0.3.104  set_hostname="worker-2"
192.0.3.105  set_hostname="worker-3"

[master_backup]
192.0.3.101  set_hostname="master-backup-1"  kube_interface="enp125s0f0" k8s_api_server_ip="192.0.3.101"
192.0.3.102  set_hostname="master-backup-2"  kube_interface="enp125s0f0" k8s_api_server_ip="192.0.3.102"

[other_build_image]
192.0.3.105

# 1. 这个配置，即部署一个3 master高可用k8s集群，而且有3个worker节点
# 2. other_build_image为与master节点架构不同的节点，如果有异构节点，请设置对应ip，如果没有则不设置
# 3. 在多master场景下，需要在每台master主机后增加变量kube_interface，用来指明每台主机使用虚拟IP的网卡名（每台服务器的网卡名可能不同），选择网卡需要保证主机之间网络能够互通
#其中主机名和ip地址对应为,用户根据实际ip自行配置：
#master              192.0.3.100
#master_backup-1     192.0.3.101
#master_backup-2     192.0.3.102
#worker-1            192.0.3.103
#worker-2            192.0.3.104
#worker-3            192.0.3.105 此为异构节点
#KUBE_VIP            192.0.3.120
```

配置项说明

| 配置项              | 说明                                                         |
| ------------------- | ------------------------------------------------------------ |
| [all:vars]          | 安装部署全局变量配置区域                                     |
| KUBE_VIP            | 不使用多master场景不用配置；多master场景下配置的虚拟的IP，kube_vip需跟k8s集群节点ip在同一子网，且为闲置、未被他人使用的ip |
| POD_NETWORK_CIDR    | k8s集群使用的IP网段，如果与服务器IP网段重合，需要修改下面的值为其他私有网段。如：10.0.0.0/16 |
| INSTALL_COMPONENT   | 需要安装的组件，可选择安装，支持安装mindxdl,docker,k8s以英文逗号分隔 |
| [master]            | master节点ip，只能为本机localhost，不可更改<br />1. localhost ansible_connection=local: 表示本机，不可修改<br />2. set_hostname：设置主机名字，建议用“[a-z]-[0-9]”的格式，如“worker-1”,配置示例：set_hostname=master-1 <br />3. k8s_api_server_ip="192.0.3.100" 网卡对应的ip地址，用作apiserver的入口地址<br />4. kube_interface="enp125s0f0"：设置使用的网卡，单master节点可以不设置 |
| [worker]            | work节点ip。默认无，即为无worker节点集群。可更改为其他服务器ip。如果这里包括master或master_backup组的ip，即把该ip的节点同时作为master和worker节点 |
| [master_backup]     | master_backup节点ip。默认无，即为单master集群。如需部署master高可用集群，这里至少需要配置2个或2个以上的节点ip(建议这里为偶数，因为k8s奇数台控制平面节点有利于机器故障或网络分区时进行重新选主）。不可包括master节点，即不可包括localhost。master_backup节点需要与master节点的系统架构一致<br />1. <ip>: 表示本机的ip地址<br />2. set_hostname：设置主机名字，建议用“[a-z]-[0-9]”的格式，如“worker-1”,配置示例：set_hostname=master-1 <br />3. kube_interface="enp125s0f0"：设置使用的网卡<br />4. k8s_api_server_ip="192.0.3.100" 网卡对应的ip地址，用作apiserver的入口地址 |
| [other_build_image] | k8s集群中存在与master节点架构不一致的服务器时，并且该节点(或多个异构节点)会部署MindX DL，任选其中一台异构节点配置到如下主机组即可 |

 

### 步骤3：检查集群状态

1. 设置了ssh的连接方式请跳过，如果未设置可以参考以下方式设置ssh连接

   ```
   ssh-keygen #一直按回车   
   ssh-copy-id <ip>   # 将管理节点的公钥拷贝到所有节点的机器上，<ip>替换成要拷贝到的对应节点的ip。
   ```

   注意事项: 请用户注意ssh密钥和密钥密码在使用和保管过程中的风险,安装完成后请删除控制节点~/.ssh/目录下的id_rsa和id_rsa_pub文件，和其他节点~/.ssh目录下的authorized_keys文件。

2. 在工具目录中执行：

   ```
   root@master:~/mindxdl-deploy/offline-deploy# ansible -i inventory_file all -m ping
   
   localhost | SUCCESS => {
       "changed": false,
       "ping": "pong"
   }
   192.168.56.103 | SUCCESS => {
       "changed": false,
       "ping": "pong"
   }
   ```

   当所有设备都能ping通，则表示inventory中所有设备连通性正常。否则，请检查设备的ssh连接和inventory文件配置是否正确

3. 各个节点的时间应保持同步，不然可能会出现不可预知异常。手动将各个节点的时间设置为一致，可参考执行如下命令，'2022-06-01 08:00:00'请改成当前实际时间

```
root@master:~/mindxdl-deploy/offline-deploy# ansible -i inventory_file all -m shell -a "date -s '2022-06-01 08:00:00'; hwclock -w"
```

### 步骤4：下载MindX DL基础组件

1. 下载mindxdl基础组件

   ```
   Ascend-mindxdl-hccl-controller_{version}_{os}-{arch}.zip
   Ascend-mindxdl-device-plugin_{version}_{os}-{arch}.zip
   Ascend-mindxdl-noded_{version}_{os}-{arch}.zip
   Ascend-mindxdl-volcano_{version}_{os}-{arch}.zip
   Ascend-mindxdl-npu-exporter_{version}_{os}-{arch}.zip
   ```

   

2. 将MindX DL基础组件放到~/resource/mindxdl目录中。如果k8s集群中包含异构节点，需要将所有架构的安装包都放在该目录下，安装脚本会自动识别架构

   ```bash
   ~/resources/
    `── mindxdl
        ├── Ascend-mindxdl-hccl-controller_{version}_{os}-{arch}.zip
        ├── Ascend-mindxdl-device-plugin_{version}_{os}-{arch}.zip
         ....
   ```

   

### <a name="resources_no_copy">步骤5：执行安装</a>

在工具目录中执行：

```bash
#采集所有主机的信息
root@master:~/mindxdl-deploy/offline-deploy# ansible-playbook -i inventory_file playbooks/00.gather_facts.yaml
#安装集群环境
root@master:~/mindxdl-deploy/offline-deploy# ansible-playbook -i inventory_file all.yaml
```

注：

1. k8s节点不可重复初始化或加入，执行本步骤前，请先在master和worker节点执行如下命令，清除节点上已有的k8s系统
   ```bash
   kubeadm reset -f; iptables -F && iptables -t nat -F && iptables -t mangle -F && iptables -X; systemctl restart docker
   ```

2. 如果执行失败，需要手动删除/root/resources/mindxdl/目录下的x86_64和aarch64目录

3. 如果部署高可用集群，需要使用ip a查看每个节点虚拟ip有没有被分配，如果有则使用一下命令删除掉

   ```
   ip addr delete <ip地址> dev <网卡名>
   ```

4. 如果不想重新安装docker和k8s，请在配置文件中设置只安装mindxdl基础软件

5. 如果inventory_file内配置了非localhost的远程ip，本工具会将本机的/root/resources目录分发到远程机器上。如果有重复执行以上命令的需求，可在以上命令后加`-e NO_COPY=true`参数，避免重复执行耗时的~/resources目录打包、分发操作

### 步骤6：安装后检查

检查kubernetes节点

```bash
root@master:~# kubectl get nodes
NAME             STATUS   ROLES    AGE   VERSION
master           Ready    master   60s   v1.19.16
worker-1         Ready    worker   60s   v1.19.16
```

检查kubenetes pods

```bash
root@master:~# kubectl get pods --all-namespaces
NAMESPACE        NAME                                      READY   STATUS             RESTARTS   AGE
kube-system      ascend-device-plugin-daemonset-910-lq     1/1     Running            0          21h
kube-system      calico-kube-controllers-68c855c64-4fn2k   1/1     Running            1          21h
kube-system      calico-node-4zfjp                         1/1     Running            0          21h
kube-system      calico-node-jsdws                         1/1     Running            0          21h
kube-system      coredns-f9fd979d6-84xd2                   1/1     Running            0          21h
kube-system      coredns-f9fd979d6-8fld7                   1/1     Running            0          21h
kube-system      etcd-ubuntu-1                             1/1     Running            0          21h
kube-system      kube-apiserver-ubuntu-1                   1/1     Running            0          21h
kube-system      kube-controller-manager-ubuntu-1          1/1     Running            8          21h
kube-system      kube-proxy-6zr9j                          1/1     Running            0          21h
kube-system      kube-proxy-w9lw9                          1/1     Running            0          21h
kube-system      kube-scheduler-ubuntu-1                   1/1     Running            6          21h
mindx-dl         hccl-controller-8ff6fd684-9pgxm           1/1     Running            0          19h
mindx-dl         noded-c2h7r                               1/1     Running            0          19h
npu-exporter     npu-exporter-7kt25                        1/1     Running            0          19h
volcano-system   volcano-controllers-56cbbb9c6-9trf7       1/1     Running            0          19h
volcano-system   volcano-scheduler-66f75bf89f-94jkx        1/1     Running            0          19h
```

# 安装脚本对系统的修改

1. k8s集群安装时，关闭了swap分区，当内存不足时，linux会自动使用swap，将部分内存数据存放到磁盘中，会使性能下降，为了性能考虑关掉了swap分区。
2. k8s集群安装时，需要将`bridge-nf-call-iptables` `和bridge-nf-call-ip6tables`这个内核参数 (置为 1)，如果不开启或中途因某些操作导致参数被关闭了，就可能造成一些奇奇怪怪的网络问题。
3. k8s集群安装时，会关闭防火墙。

# FAQ

1. Q: 某个节点的calico-node-**出现READY “0/1”，`kubectl describe pod calico-node-**(master的calico-node)`时有报错信息“calico/node is not ready: BIRD is not ready: BGP not established with \<ip\>”

   A: 可能是该节点的交换分区被打开了（swap on，可通过`free`查询)，kubelet日志报错“failed to run Kubelet: running with swap on is not supported, please disable swap”，导致该节点calico访问失败。解决方案是禁用swap（执行`swapoff -a`）

2. Q:部署高可用集群时，出现phase preflight: couldn't validate the identity of the API Server: Get \"https://192.168.56.120:6443/api/v1/namespaces/kube-public/configmaps/cluster-info?timeout=10s\": dial tcp 192.168.56.120:6443: connect: connection refused\nTo see the stack trace of this error execute with --v=5 or higher

   A：有可能多个master节点分配了虚拟ip，需要重启master节点，使kube-vip部署的虚拟ip地址失效

3. Q:k8s报错:The connection to the server xxxxx:6443 was refused - did you specify the right host or port?

   A:有可能是配置了代理，可以使用env查看是否配置了代理，如果配置了，需要关闭代理。

   

