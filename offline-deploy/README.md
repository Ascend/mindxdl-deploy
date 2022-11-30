### 快速入门

本文主要介绍如何使用ansible安装MindX DL软件及其依赖的开源软件

### 版本说明

| 版本   | 版本说明                                                     |
| ------ | ------------------------------------------------------------ |
| V3.0.0 | 1.MindX DL按场景安装方式，可选择场景一、二、三方式安装组件，部分组件可选装。<br/>2.适配ubuntu，openEuler操作系统，并且支持x86_64和aarch64。<br/>3.增加使用harbor镜像仓拉取镜像的方式 <br/>4.支持部署高可用kubernetes集群 |

### 软件描述

本文主要介绍如何使用ansible安装MindX DL所需开源软件安装。其中包含如下开源软件,具体功能请参考官网。

| 软件名        | 备注                    |
| ---------- | ------------------------- |
| Docker    | 容器运行时 |
| kubernetes | 容器编排工具            |
| Ascend Device Plugin | mindx-dl基础组件 |
| NodeD | mindx-dl基础组件 |
| Volcano | mindx-dl基础组件 |
| Npu-Exporter | mindx-dl基础组件 |
| HCCL-Controller | mindx-dl基础组件 |
| ToolBox | mindx-dl基础组件 |

### 环境要求

### 支持的操作系统说明

| 操作系统   | 版本   | CPU架构 |
|:------:|:---------:|:-------:|
| ubuntu | 18.04.1 | aarch64 |
| ubuntu | 18.04.1 | x86_64  |
| openEuler | 20.03 LTS | aarch64 |
| openEuler | 20.03 LTS | x86_64 |

根目录的磁盘空间利用率高于85%会触发Kubelet的镜像垃圾回收机制，将导致服务不可用。请确保根目录有足够的磁盘空间，建议大于1 TB**

### 支持的硬件形态说明

| 服务器类型 |
|:---------------|
| Atlas 800 训练服务器（型号：9000/9010） |
| Atlas 800 训练服务器（型号：3000/3010） |
| 服务器（插Atlas 300T 训练卡） |
| 服务器（插Atlas 300I 推理卡） |
| 服务器（插Atlas 300I Pro 推理卡） |
| 服务器（插Atlas 300I Duo 推理卡） |
| 服务器（插Atlas 300V Pro 视频解析卡） |
| 服务器（插Atlas 300V 训练解析卡） |

### 安装方式说明

| 安装场景                                        | 安装组件                                                     |
| ----------------------------------------------- | ------------------------------------------------------------ |
| 场景一：基础全量安装场景                        | Docker, Kubernetes, Toolbox, Ascend Device Plugin, Volcano, HCCL-Controller, NodeD, NPU-Exporter |
| 场景二：已有Kubernetes集群，使用volcano调度器   | Toolbox, Ascend Device Plugin, Volcano, HCCL-Controller(可选), NodeD(可选), NPU-Exporter(可选) |
| 场景三：已有Kubernetes集群，不使用volcano调度器 | Toolbox, Ascend Device Plugin, NPU-Exporter(可选)            |



## 下载本工具

1.下载批量部署脚本，可使用git clone和下载zip方法，下载地址为：[Ascend/mindxdl-deploy](https://gitee.com/ascend/mindxdl-deploy)。，请放置在/root目录下，安装部署脚本在master分支的offline-deploy目录下。

2.下载开源软件的离线安装包[resources.tar.gz](https://ascend-repo-modelzoo.obs.cn-east-2.myhuaweicloud.com/MindXDL/resources.tar.gz)，将离线安装包解压在/root目录下。按如下方式放置

```bash
root@master:~# ls
mindxdl-deploy
resources             //由resources.tar.gz解压得到，必须放置在/root目录下
resources.tar.gz
```

## 安装步骤

### 步骤1：配置ssh免密登录

设置了ssh的连接方式请跳过，如果未设置可以参考以下方式设置ssh连接

```
ssh-keygen #一直按回车   
ssh-copy-id <ip>   # 将管理节点的公钥拷贝到所有节点的机器上(包括自己)，<ip>替换成要拷贝到的对应节点的ip。
```

注意事项: 请用户注意ssh密钥和密钥密码在使用和保管过程中的风险,安装完成后请删除控制节点~/.ssh/目录下的id_rsa和id_rsa_pub文件，和其他节点~/.ssh目录下的authorized_keys文件。

### 步骤2：安装ansible

如果已安装ansible，请跳过这一步骤：

```bash
#在代码脚本的offline-deploy目录下执行以下命令
root@master:~/mindxdl-deploy/offline-deploy# bash install_ansible.sh
```

### 步骤3：检查集群状态

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

   当所有设备都能ping通，则表示inventory_file中所有设备连通性正常。否则，请检查设备的ssh连接和inventory_file文件配置是否正确

3. 各个节点的时间应保持同步，不然可能会出现不可预知异常。手动将各个节点的时间设置为一致，可参考执行如下命令，'2022-06-01 08:00:00'请改成当前实际时间

   ```
   root@master:~/mindxdl-deploy/offline-deploy# ansible -i inventory_file all -m shell -a "date -s '2022-06-01 08:00:00'; hwclock -w"
   ```

4. 请先安装NPU硬件对应的驱动和固件，才能构建昇腾NPU的训练和推理任务。

### 步骤4：下载MindX DL基础组件

1. 下载mindxdl基础组件

   ```
   Ascend-mindxdl-hccl-controller_{version}_{os}-{arch}.zip
   Ascend-mindxdl-device-plugin_{version}_{os}-{arch}.zip
   Ascend-mindxdl-noded_{version}_{os}-{arch}.zip
   Ascend-mindxdl-volcano_{version}_{os}-{arch}.zip
   Ascend-mindxdl-npu-exporter_{version}_{os}-{arch}.zip
   Ascend-mindx-toolbox_{version}_{os}-{arch}.run
   ```

   注：ToolBox为run后缀包

2. 将MindX DL基础组件放在~/resource/mindxdl/dlPackage/{arch}目录中。如果k8s集群中包含异构节点，需要将异构节点的安装包放在同目录对应架构一下。




### 步骤5：配置集群信息

在代码脚本的offline-deploy目录下修改配置文件参数，用户可根据配置文件注释自行设置

```bash
root@ubuntu-1:~/mindxdl-deploy/offline-deploy# vi inventory_file
```



### 步骤6：执行安装

在代码脚本的offline-deploy目录下执行以下命令：

```bash
#安装集群环境
root@master:~/mindxdl-deploy/offline-deploy# ansible-playbook -i inventory_file all.yaml
```

注：

1. 当场景一执行安装kubernetes失败时，请先在所有节点执行如下命令，清除节点上已有的kubernetes残留文件
   ```bash
   kubeadm reset -f; iptables -F && iptables -t nat -F && iptables -t mangle -F && iptables -X; systemctl restart docker
   ```

3. 如果部署多master集群，需要使用ip a查看每个节点虚拟ip有没有被分配，如果有则使用以下命令删除

   ```
   ip addr delete <ip地址> dev <网卡名>
   ```

### 步骤7：MindX DL基础组件升级

1.将MindX DL基础组件放在~/resource/mindxdl/dlPackage/{arch}目录中。如果k8s集群中包含异构节点，需要将异构节点的安装包放在同目录对应架构一下。

2.如果要安装device-plugin和npu-exporter，需要将~/mindxdl-deploy/yamls/目录下的device-plugin和npu-exporter文件替换为指定版本的部署文件。

```
root@master:~/mindxdl-deploy/offline-deploy# ansible-playbook -i inventory_file playbooks/05.mindxdl.yaml
```



### 步骤8：安装后检查

检查kubernetes节点

```bash
root@master:~# kubectl get nodes
NAME             STATUS   ROLES    AGE   VERSION
master           Ready    master   60s   v1.19.16
worker-1         Ready    worker   60s   v1.19.16
```

检查kubenetes pods是否正常运行

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

   

