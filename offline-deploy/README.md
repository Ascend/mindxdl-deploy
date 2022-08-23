# 快速入门

本文主要介绍如何使用ansible安装mindxdl软件及其依赖的开源软件

# 版本说明

| 版本         | 版本说明                                                     |
| ------------ | ------------------------------------------------------------ |
| mindx-deploy | 该版本支持centos和ubuntu离线安装部署，可选装或全量安装<br />1.支持离线安装docker<br />2.支持离线安装kubernetes集群<br />3.支持离线安装高可用kubernetes集群<br />4.支持离线安装mindx-dl基础组件 |



## 软件描述

本文主要介绍如何使用ansible安装mindxdl所需开源软件安装。其中包含如下开源软件

| 软件名        | 备注                    |
| ---------- | -------------------------|
| docker     | 集群中所有节点都需要安装   |
| kubernetes | k8s平台                  |
| Ascend-mindxdl-device-plugin | mindx-dl基础组件 |
| Ascend-mindxdl-noded | mindx-dl基础组件 |
| Ascend-mindxdl-volcano | mindx-dl基础组件 |
| Ascend-mindxdl-npu-exporter | mindx-dl基础组件 |
| Ascend-mindxdl-hccl-controller | mindx-dl基础组件 |

## 环境要求

### 支持的操作系统说明

| 操作系统   | 版本   | CPU架构 |
|:------:|:---------:|:-------:|
| Ubuntu | 18.04 | aarch64 |
| Ubuntu | 18.04 | x86_64  |
| CentOS | 7.6 | aarch64 |
| CentOS | 7.6 | x86_64 |

根目录的磁盘空间利用率高于85%会触发Kubelet的镜像垃圾回收机制，将导致服务不可用。请确保根目录有足够的磁盘空间，建议大于1 TB**（存疑）**

### 支持的硬件形态说明（存疑）

| 中心推理硬件    | 中心训练硬件|
|:--------------:|:----------:|
| A300-3000      | A300T-9000 |
| A300-3010      | A800-9000  |
| Atlas 300I Pro | A800-9010  |
| A800-3000      |            |
| A800-3010      |            |

请先安装NPU硬件对应的驱动和固件，才能构建昇腾NPU的训练和推理任务。安装文档[链接](https://support.huawei.com/enterprise/zh/category/ascend-computing-pid-1557196528909)

## 下载本工具

本工具只支持root用户，下载地址：[Ascend/mindxdl-deploy](https://gitee.com/ascend/mindxdl-deploy)。2种下载方式：

1. 使用git clone，切换到master分支,离线安装部署在offline-deploy目录下

2. 下载mindxdl-deploy分支的[zip文件](https://gitee.com/ascend/ascend-hccl-controller/repository/archive/mindxdl-deploy.zip)

然后获得开源软件的[resources.tar.gz](https://mindx.obs.cn-south-1.myhuaweicloud.com/MindXDL/resources.tar.gz)离线安装包，将离线安装包解压在/root目录下。按如下方式放置

```bash
root@master:~# ls
mindxdl-deploy
resources             //由resources.tar.gz解压得到，必须放置在/root目录下
resources.tar.gz
```

## 安装步骤

### 步骤1：安装ansible

在resource目录中执行：

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

安装完成后执行ansible --version查看ansible是否安装成功

### 步骤2：配置集群信息

修改配置文件参数，必须添加apiserver的ip地址，ip地址为master地址，其他配置，用户可自行设置

```bash
root@ubuntu-1:~/mindxdl-deploy/offline-deploy# vi inventory_file
```

在inventory文件中，需要提前规划好如下集群信息：


```ini
# 以下为全局变量配置区域
[all:vars]

# k8s apiserver的地址，必须设置apiserver为master的ip地址
K8S_API_SERVER_IP=""
# 不使用多master场景不用配置；多master场景下配置的虚拟的IP，kube_vip需跟k8s集群节点ip在同一子网，且为闲置、未被他人使用的ip
KUBE_VIP=""

# k8s集群使用的IP网段，如果与服务器IP网段重合，需要修改下面的值为其他私有网段。如：10.0.0.0/16
POD_NETWORK_CIDR="192.168.0.0/16"

# 需要安装的组件，支持安装mindxdl,docker,k8s以英文逗号分隔
INSTALL_COMPONENT="mindxdl,docker,k8s"


# 以下为主机变量配置区域

# 1. k8s要求集群内节点(master、worker、master_backup）的hostname不一样，因此
#    建议执行安装前设置所有设备使用不同的hostname。如果未统一设置且存在相同hostname的设备，
#    那么可在本文件中主机组中设置set_hostname主机变量，set_hostname的值会作为作为K8s集群中的NodeName。
#    set_hostname的值需满足k8s和ansible的格式要求，建议用“[a-z]-[0-9]”的格式，如“worker-1”,配置示例：set_hostname=master-1
# 2. 在多master场景下，需要在每台master主机后增加变量kube_interface，用来指明每台主机使用虚拟IP的网卡名（每台服务器的网卡名可能不同），选择网卡需要保证主机之间网络能够互通
#
# 示例：
# [master]
# localhost ansible_connection=local set_hostname=master-1 kube_interface=enp125s0f0

[master]
localhost ansible_connection=local

[worker]

# 多master场景下，其他master节点的主机
[master_backup]

# k8s集群中存在与master节点架构不一致的服务器时，并且该节点(或多个异构节点)会部署MindX DL，任选其中一台异构节点配置到如下主机组即可
[other_build_image]

# 这个默认配置，即把本机部署成一个单master节点的k8s集群，而且无worker节点
```

配置项说明

| 配置项              | 说明                                                         |
| ------------------- | ------------------------------------------------------------ |
| [all:vars]          | 安装部署全局变量配置区域                                     |
| K8S_API_SERVER_IP   | k8s apiserver的地址，必须设置apiserver为master的ip地址       |
| KUBE_VIP            | 不使用多master场景不用配置；多master场景下配置的虚拟的IP，kube_vip需跟k8s集群节点ip在同一子网，且为闲置、未被他人使用的ip |
| POD_NETWORK_CIDR    | k8s集群使用的IP网段，如果与服务器IP网段重合，需要修改下面的值为其他私有网段。如：10.0.0.0/16 |
| INSTALL_COMPONENT   | 需要安装的组件，可选择安装，支持安装mindxdl,docker,k8s以英文逗号分隔 |
| [master]            | master节点ip，只能为本机localhost，不可更改                  |
| [worker]            | work节点ip。默认无，即为无worker节点集群。可更改为其他服务器ip。如果这里包括master或master_backup组的ip，即把该ip的节点同时作为master和worker节点 |
| [master_backup]     | master_backup节点ip。默认无，即为单master集群。如需部署master高可用集群，这里至少需要配置2个或2个以上的节点ip(建议这里为偶数，因为k8s奇数台控制平面节点有利于机器故障或网络分区时进行重新选主）。不可包括master节点，即不可包括localhost。master_backup节点需要与master节点的系统架构一致 |
| [other_build_image] | k8s集群中存在与master节点架构不一致的服务器时，并且该节点(或多个异构节点)会部署MindX DL，任选其中一台异构节点配置到如下主机组即可 |

注意：

1. 在部署master高可用集群时，必须给[master]和[master_backup]的设备设置kube_interface主机变量，以及增加一个[all:vars]的kube_vip主机组变量。kube_interface为各自节点实际使用的ip对应的网卡名称，可通过`ip a`查询，如"enp125s0f0"。kube_vip需跟k8s集群节点ip在同一子网，且为闲置、未被他人使用的ip，请联系网络管理员获取。

参考配置如下

```ini
# 以下为全局变量配置区域
[all:vars]
K8S_API_SERVER_IP="170.0.2.49"
KUBE_VIP=""
POD_NETWORK_CIDR="192.168.0.0/16"
INSTALL_COMPONENT="mindxdl,docker,k8s"

[master]
localhost ansible_connection=local  set_hostname="master"  kube_interface="enp125s0f0"

[worker]
192.0.2.50  set_hostname="worker-1"
192.0.2.51  set_hostname="worker-2"
192.0.2.52  set_hostname="worker-3"

[master_backup]
192.0.3.100  set_hostname="master-backup-1"  kube_interface="enp125s0f0"
192.0.3.101  set_hostname="master-backup-2"  kube_interface="enp125s0f0"

[other_build_image]
192.0.2.50

# 这个配置，即部署一个3 master高可用k8s集群，而且有3个worker节点
# 以上192.0.*.*等ip仅为示例，请修改为实际规划的ip地址
# other_build_image为与master节点架构不同的节点
```

inventory文件配置详细可参考[[How to build your inventory &mdash; Ansible Documentation](https://docs.ansible.com/ansible/latest/user_guide/intro_inventory.html)]

### 

### 步骤3：检查集群状态

如果inventory_file内配置了非localhost的远程ip，根据ansible官方建议，请用户自行使用SSH密钥的方式连接到远程机器，可参考[[connection_details; Ansible Documentation](https://docs.ansible.com/ansible/latest/user_guide/connection_details.html#setting-up-ssh-keys)]

在工具目录中执行：

```bash
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

各个节点的时间应保持同步，不然可能会出现不可预知异常。手动将各个节点的时间设置为一致，可参考执行如下命令，'2022-06-01 08:00:00'请改成当前实际时间

```bash
root@master:~/mindxdl-deploy/offline-deploy# ansible -i inventory_file all -m shell -a "date -s '2022-06-01 08:00:00'; hwclock -w"
```

注：

可以参考使用以下方式设置ssh连接

1. 基于密钥认证的ssh连接，安装前请确认系统中未安装paramiko（ansible在某些情况下会使用paramiko，其配置不当容易引起安全问题）。

   设置密钥认证的参考操作如下，请注意ssh密钥和密钥密码在使用和保管过程中的风险，特别是密钥未加密时的风险，用户应按照所在组织的安全策略进行相关配置，包括并不局限于软件版本、口令复杂度要求、安全配置（协议、加密套件、密钥长度等，特别是/etc/ssh下和~/.ssh下的配置）：

   ```
   ssh-keygen -t rsa -b 3072   # 登录管理节点并生成SSH Key。安全起见，建议用户到"Enter passphrase"步骤时输入密钥密码，且符合密码复杂度要求。建议执行这条命令前先将umask设置为0077，执行完后再恢复原来umask值。
   ssh-copy-id -i ~/.ssh/id_rsa.pub <user>@<ip>   # 将管理节点的公钥拷贝到所有节点的机器上，<user>@<ip>替换成要拷贝到的对应节点的账户和ip。
   ssh <user>@<ip>   # 验证是否可以登录远程节点，<user>@<ip>替换成要登录的对应节点的账户和ip。验证登录OK后执行`exit`命令退出该ssh连接。
   ```

   注意事项: 请用户注意ssh密钥和密钥密码在使用和保管过程中的风险。

2. 设置ssh代理管理ssh密钥，避免工具批量安装操作过程中输入密钥密码。设置ssh代理的参考操作如下：

   ```
   ssh-agent bash   # 开启ssh-agent的bash进程
   ssh-add ~/.ssh/id_rsa         # 向ssh-agent添加私钥
   ```

3. 工具的批量安装操作完成后，及时退出ssh代理进程，避免安全风险。

   ```
   exit   # 退出ssh-agent的bash进程
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

2. 如果不想重新安装docker和k8s，请在配置文件中设置只安装mindxdl基础软件

3. 如果inventory_file内配置了非localhost的远程ip，本工具会将本机的/root/resources目录分发到远程机器上。如果有重复执行以上命令的需求，可在以上命令后加`-e NO_COPY=true`参数，避免重复执行耗时的~/resources目录打包、分发操作

### 步骤6：安装后检查

检查kubernetes节点

```bash
root@master:~# kubectl get nodes -A
NAME             STATUS   ROLES    AGE   VERSION
master           Ready    master   60s   v1.19.16
worker-1         Ready    worker   60s   v1.19.16
```

检查kubenetes pods

```bash
root@master:~# kubectl get pods -A
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

注：

1. 手动执行kubectl命令时，需取消http(s)_proxy系统网络代理配置，否则会连接报错或一直卡死
1. device-plugin只能在有npu节点上部署

# 对系统修改

1. k8s集群安装时，关闭了swap分区，当内存不足时，linux会自动使用swap，将部分内存数据存放到磁盘中，会使性能下降，为了性能考虑推荐关掉。
2. k8s集群安装时，需要将`bridge-nf-call-iptables` 这个内核参数 (置为 1)，如果不开启或中途因某些操作导致参数被关闭了，就可能造成一些奇奇怪怪的网络问题。
3. k8s集群安装时，centos系统关闭防火墙（firewalld），如果不关闭，k8s集群会安装失败。

# FAQ

1. Q: 某个节点的calico-node-**出现READY “0/1”，`kubectl describe pod calico-node-**(master的calico-node)`时有报错信息“calico/node is not ready: BIRD is not ready: BGP not established with \<ip\>”

   A: 可能是该节点的交换分区被打开了（swap on，可通过`free`查询)，kubelet日志报错“failed to run Kubelet: running with swap on is not supported, please disable swap”，导致该节点calico访问失败。解决方案是禁用swap（执行`swapoff -a`）

2. Q:部署高可用集群时，出现phase preflight: couldn't validate the identity of the API Server: Get \"https://192.168.56.120:6443/api/v1/namespaces/kube-public/configmaps/cluster-info?timeout=10s\": dial tcp 192.168.56.120:6443: connect: connection refused\nTo see the stack trace of this error execute with --v=5 or higher

   A：有可能多个master节点分配了虚拟ip，需要重启master节点，使kube-vip部署的虚拟ip地址失效

3. 

