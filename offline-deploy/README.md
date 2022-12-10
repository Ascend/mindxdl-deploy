 - [功能简介](#功能简介)
 - [环境依赖](#环境依赖)
    - [运行环境要求](#运行环境要求)
    - [软件支持列表](#软件支持列表)
    - [硬件支持列表](#硬件支持列表)
 - [安装场景](#安装场景)
 - [安装步骤](#安装步骤)
    - [步骤1：配置ssh免密登录](#步骤1配置ssh免密登录)
    - [步骤2：下载离线软件包](#步骤2下载离线软件包)
    - [步骤3：安装Ansible](#步骤3安装ansible)
    - [步骤4：配置安装信息](#步骤4配置安装信息)
    - [步骤5：执行安装](#步骤5执行安装)
 - [安装后状态查看](#安装后状态查看)
 - [组件升级](#组件升级)
 - [Kubernetes证书更新](#kubernetes证书更新)
 - [安装脚本对系统的修改](#安装脚本对系统的修改)
 - [常用操作](#常用操作)
 - [常见问题](#常见问题)
    - [常见安装问题](#常见安装问题)
    - [其他问题](#其他问题)
 - [历史版本](#历史版本)
 - [CHANGELOG](#changelog)

# 功能简介
使用基于Ansible的脚本安装MindX DL、以及运行MindX DL依赖的软件（Docker、kubernetes）。

# 环境依赖
## 运行环境要求

 1. 存放镜像目录的磁盘空间利用率**高于85%**会触发Kubelet的镜像垃圾回收机制，**将导致服务不可用**。请确保每台服务器上存放镜像的目录有足够的磁盘空间，建议≥**1 TB**。
 2. **执行安装命令前，需要提前在服务器安装好昇腾NPU的驱动和固件，并[配置训练服务器NPU的device IP](https://www.hiascend.com/document/detail/zh/canncommercial/60RC1/envdeployment/instg/instg_000039.html)**。
 3. 执行安装脚本前，保证安装Kubernetes的服务器的时间一致，可参考[常用操作1](#常用操作)快速设置各节点时间。
 4. 所有节点需要**已安装Python2.7以上**
 5. 安装脚本支持在下表的操作系统运行，脚本支持在如下操作系统上安装MindX DL、Docker、Kubernetes软件。
	<table>
    <thead>
      <tr>
        <th align="left">操作系统</th>
        <th align="left">版本</th>
        <th align="left">架构</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td rowspan="2">Ubuntu </td>
        <td rowspan="2">18.04</td>
        <td>aarch64</td>
      </tr>
      <tr>
        <td>x86_64</td>
      </tr>
      <tr>
        <td rowspan="2">OpenEuler</td>
        <td rowspan="2">20.03 LTS</td>
        <td>aarch64</td>
      </tr>
      <tr>
        <td>x86_64</td>
      </tr>
    </tbody>
    </table>

## 软件支持列表
<table>
<thead>
  <tr>
    <th align="left">软件名</th>
    <th align="left">软件版本</th>
    <th align="left">架构</th>
    <th align="left">说明</th>
  </tr>
</thead>
<tbody>
  <tr>
    <td rowspan="2">Docker</td>
    <td rowspan="2">18.09</td>
    <td>aarch64</td>
    <td rowspan="2">容器运行时</td>
  </tr>
  <tr>
    <td>x86_64</td>
  </tr>
  <tr>
    <td rowspan="2">Kubernetes</td>
    <td rowspan="2">1.19.16</td>
    <td>aarch64</td>
    <td rowspan="2">容器编排工具</td>
  </tr>
  <tr>
    <td>x86_64</td>
  </tr>
  <tr>
    <td>Ascend Device Plugin</td>
    <td rowspan="6">3.0.0</td>
    <td rowspan="6"><li>aarch64</li><br /><li>x86_64</li></td>
    <td rowspan="6">MindX DL的组件</td>
  </tr>
  <tr>
    <td>Volcano</td>
  </tr>
  <tr>
    <td>NodeD</td>
  </tr>
  <tr>
    <td>HCCL-Controller</td>
  </tr>
  <tr>
    <td>NPU-Exporter</td>
  </tr>
  <tr>
    <td>Ascend Docker Runtime</td>
  </tr>
</tbody>
</table>

## 硬件支持列表

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



# 安装场景
可选组件默认不安装
<table>
<thead>
  <tr>
    <th align="left">场景</th>
    <th align="left">安装组件</th>
    <th align="left">说明</th>
  </tr>
</thead>
<tbody>
  <tr>
    <td rowspan="8">场景一</td>
    <td rowspan="8"><li>Docker</li><br /><li>Kubernetes</li><br /><li>Ascend Docker Runtime</li><br /><li>Ascend Device Plugin</li><br /><li>Volcano</li><br /><li>NodeD</li><br /><li>HCCL-Controller</li><br /><li>NPU-Exporter</li></td>
    <td rowspan="8">常用安装场景，包含大多数MindX DL功能</td>
  </tr>
  <tr>
  </tr>
  <tr>
  </tr>
  <tr>
  </tr>
  <tr>
  </tr>
  <tr>
  </tr>
  <tr>
  </tr>
  <tr>
  </tr>
  <tr>
    <td rowspan="6">场景二</td>
    <td rowspan="6"><li>Ascend Docker Runtime</li><br /><li>Ascend Device Plugin</li><br /><li>Volcano</li><br /><li>NodeD(可选)</li><br /><li>HCCL-Controller(可选)</li><br /><li>NPU-Exporter(可选)</li></td>
    <td rowspan="6">Volcano基础调度场景</td>
  </tr>
  <tr>
  </tr>
  <tr>
  </tr>
  <tr>
  </tr>
  <tr>
  </tr>
  <tr>
  </tr>
  <tr>
    <td rowspan="3">场景三</td>
    <td rowspan="3"><li>Ascend Docker Runtime</li><br /><li>Ascend Device Plugin</li><br /><li>NPU-Exporter(可选)</li></td>
    <td rowspan="3">其他调度器场景</td>
  </tr>
  <tr>
  </tr>
  <tr>
  </tr>
</tbody>
</table>

# 安装步骤

## 步骤1：配置ssh免密登录

设置了ssh的连接方式请跳过，如果未设置可以参考以下方式设置ssh连接

```
ssh-keygen #一直按回车
ssh-copy-id <ip>   # 将管理节点的公钥拷贝到所有节点的机器上(包括自己)，<ip>替换成要拷贝到的对应节点的ip。
```

注意事项: 请用户注意ssh密钥和密钥密码在使用和保管过程中的风险,安装完成后请删除控制节点~/.ssh/目录下的id_rsa和id_rsa_pub文件，和其他节点~/.ssh目录下的authorized_keys文件。

## 步骤2：下载离线软件包
选择其中一种方式准备离线安装包

 - 在Window或其他机器上下载[历史版本](#历史版本)中的resources.tar.gz包，将离线包上传到执行安装命令服务器的/root目录下，然后解压。
 - 登录执行安装命令服务器，将下面`wget`命令后的`https://example`替换成[历史版本](#历史版本)中某个版本的resources.tar.gz的地址，然后执行如下命令
```bash
# resources.tar.gz解压出的内容必须放置在/root目录下
cd /root
wget https://example
tar -xf resources.tar.gz
```

## 步骤3：安装Ansible
```bash
cd /root/offline-deploy
bash scripts/install_ansible.sh
```
出现类似下面的回显，表示ansible安装成功
```
[INFO]	2022-07-28 22:53:09	 start install ansible...
...
[INFO]	2022-07-28 22:53:24	 successfully installed ansible

ansible 2.9.27
  config file = /etc/ansible/ansible.cfg
  configured module search path = [u'/root/.ansible/plugins/modules', u'/usr/share/ansible/plugins/modules']
  ansible python module location = /usr/lib/python2.7/dist-packages/ansible
  executable location = /usr/bin/ansible
  python version = 2.7.17 (default, Jul  1 2022, 15:56:32) [GCC 7.5.0]
```

## 步骤4：配置安装信息

修改配置文件参数，用户可根据配置文件注释自行设置

```bash
cd /root/offline-deploy
vi inventory_file
```

## 步骤5：执行安装

在[步骤4](#步骤4配置安装信息)同级目录中执行下面的安装命令。如果安装过程出现错误，请根据回显中的信息进行排查处理，也可查看[常见安装问题](#常见安装问题)进行处理，处理完毕后再执行如下命令进行安装。
```
bash scripts/install.sh
```

# 安装后状态查看

使用命令`kubectl get nodes`检查kubernetes节点，如下所示表示正常

```bash
NAME             STATUS   ROLES    AGE   VERSION
master           Ready    master   60s   v1.19.16
worker-1         Ready    worker   60s   v1.19.16
```

使用命令`kubectl get pods --all-namespaces`检查kubernetes pods，如下所示表示正常

```
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

# 组件升级
目前**仅支持MindX DL升级**，**不支持**Docker和Kubernetes的升级，并且升级时会按照之前`/root/offline-deploy/inventory_file`中配置的**节点**、**节点类型**、**场景包含的组件**进行升级。

升级会先卸载旧的MindX DL组件再重新安装，请选择空闲时间进行，避免影响训练或者推理任务。

升级MindX DL时需要获取[历史版本](#历史版本)中的resources.tar.gz包，上传到脚本执行节点**非/root目录**(如/root/upgrade)下，执行如下命令先备份旧的resources.tar.gz中的内容。
```
# 解压新的resources.tar.gz
cd /root/upgrade
tar -xf resources.tar.gz

# 备份旧的resources.tar.gz解压出的内容
cd /root/upgrade/offline-deploy
bash scripts/backup.sh
```
然后执行更新命令，如果在更新过程出现错误，请根据打印信息处理错误，然后再次执行下面的命令进行升级（不需要再执行上面的备份命令，除非更换了resources.tar.gz包）。
```
# 如需修改inventory_file，可在执行下一条命令之前自行修改/root/offline-deploy/inventory_file
cd /root/offline-deploy
bash scripts/upgrade.sh
```

# Kubernetes证书更新
K8s默认的证书有效期为1年，可通过如下命令查看证书有效期。
```
kubeadm alpha certs check-expiration
```
回显示例如下
```
[check-expiration] Reading configuration from the cluster...
[check-expiration] FYI: You can look at this config file with 'kubectl -n kube-system get cm kubeadm-config -oyaml'

CERTIFICATE                EXPIRES                  RESIDUAL TIME   CERTIFICATE AUTHORITY   EXTERNALLY MANAGED
admin.conf                 Dec 05, 2023 14:56 UTC   364d                                    no      
apiserver                  Dec 05, 2023 14:56 UTC   364d            ca                      no      
apiserver-etcd-client      Dec 05, 2023 14:56 UTC   364d            etcd-ca                 no      
apiserver-kubelet-client   Dec 05, 2023 14:56 UTC   364d            ca                      no      
controller-manager.conf    Dec 05, 2023 14:56 UTC   364d                                    no      
etcd-healthcheck-client    Dec 05, 2023 14:56 UTC   364d            etcd-ca                 no      
etcd-peer                  Dec 05, 2023 14:56 UTC   364d            etcd-ca                 no      
etcd-server                Dec 05, 2023 14:56 UTC   364d            etcd-ca                 no      
front-proxy-client         Dec 05, 2023 14:56 UTC   364d            front-proxy-ca          no      
scheduler.conf             Dec 05, 2023 14:56 UTC   364d                                    no      

CERTIFICATE AUTHORITY   EXPIRES                  RESIDUAL TIME   EXTERNALLY MANAGED
ca                      Dec 02, 2032 14:01 UTC   9y              no      
etcd-ca                 Dec 02, 2032 14:01 UTC   9y              no      
front-proxy-ca          Dec 02, 2032 14:01 UTC   9y              no
```
基于K8s的<a href="https://kubernetes.io/zh-cn/docs/tasks/administer-cluster/kubeadm/kubeadm-certs/#manual-certificate-renewal">官方更新机制</a>，提供了一键更新节点K8s证书的功能，**仅支持K8s默认的证书签发机制生成的证书**。**升级时可能会有短时间的服务中断，请合理规划更新证书的时间**。执行更新命令需要满足如下的前提条件
1. [完成Ansible安装](#步骤3安装ansible)
2. [配置了inventory_file](#步骤4配置安装信息)

执行如下命令，完成K8s证书更新，只更新inventory_file中配置节点的证书
```
cd /root/offline-deploy
bash scripts/renew_certs.sh
```

# 安装脚本对系统的修改

 1. 如果安装时选择了安装Kubernetes，脚本会对系统进行如下修改
     1. 关闭swap分区
     2. 将`bridge-nf-call-iptables`和`bridge-nf-call-ip6tables`这两个内核参数置为1
     3. 关闭系统防火墙
 2. 脚本会安装Ascend Docker Runtime，自动为Docker的runtime增加昇腾的`ascend`runtime，配置文件的修改位置`/etc/docker/daemon.json`。
 3. 如果安装时选择了使用Harbor仓库，以下情况会修改`/etc/docker/daemon.json`文件，在“insecure-registries”字段中增加Harbor的地址，以保证能够使用Harbor。
     1. Harbor使用HTTPS服务，但inventory_file中未配置Harbor的CA证书路径
     2. Harbor使用HTTP服务
 4. 安装脚本会在操作系统上安装如下软件，以方便使用`unzip` `lspci` `bc` `ip` `ifconfig`命令
 	```
    pcituils,bc,net-tools,unzip,iproute
    ```


# 常用操作
 1. 保证安装Kubernetes的各节点的时间一致，避免因为时间问题导致kubernetes集群出现问题。

    **前提条件**：
    1. [安装Ansible](#步骤3安装ansible)
    2. [配置inventory\_file](#步骤4配置安装信息)
    3. 节点已连通，可参考[常用操作2](#常用操作)

    将下面命令中的***2022-06-01 08:00:00***替换成用户需要的时间后，再执行
    ```
    cd /root/offline-deploy
    ansible -i inventory_file all -m shell -a "date -s '2022-06-01 08:00:00'; hwclock -w"
    ```

 2. 查看安装脚本执行节点能否访问inventory_file中的其他节点，即检查连通性。

    **前提条件**：
    1. [安装Ansible](#步骤3安装ansible)
    2. [配置inventory\_file](#步骤4配置安装信息)

    **执行命令**：
    ```
    ansible -i inventory_file all -m ping
    ```
    回显中无“UNREACHABLE”表示连通，否则参考[常见安装问题1](#常见安装问题)进行处理
 3. 查看Ascend Docker Runtime是否生效，请执行命令`docker info 2>/dev/null | grep Runtime`，回显中出现“ascend”表示生效，回显示例如下。

    ```
    Runtimes: ascend runc
    Default Runtime: ascend
    ```

# 常见问题
## 常见安装问题

 1. 回显信息出现“UNREACHABLE”，参考信息如下：
     ```
     172.0.0.100 | UNREACHABLE! => {
        "changed": false, 
        "msg": "Failed to connect to the host via ssh: \nAuthorized users only. All activities may be monitored and reported.\nroot@172.0.0.100: Permission denied (publickey,gssapi-keyex,gssapi-with-mic,password).", 
        "unreachable": true
    }

     ```
     **原因**：<br />
     ansible脚本无法ssh登录到inventory_file中配置的服务器上

     **解决方法**：<br />
     请检查对应服务器的ssh配置是否正确，ssh服务是否启动，以及inventory_file文件配置是否正确
 2. 安装说明
 	- 安装脚本对Docker和Kubernetes的处理逻辑
 		- 场景包含的安装组件中没有Docker或Kubernetes时，脚本不会执行安装，以及初始化、加入集群等操作。
 		- 场景包含的安装组件中有Docker或Kubernetes时
 			- 如果用户已在部分节点安装过Docker或Kubernetes，则脚本会打印这些节点上软件的版本信息，并且跳过软件的安装；剩余未安装的节点，则会根据[软件支持列表](#软件支持列表)中的软件版本安装软件;此时用户需要保证自行安装的Docker或Kubernetes版本与软件支持列表中的软件版本一致，避免出现不可预测的问题。
 			- 如果master节点已经加入过Kubernetes集群，则该master节点会跳过初始化，不做任何操作；否则会初始化集群或者多master场景下会加入已有master集群；用户需要自行保证各master节点Kubernetes版本一致，避免不可预测的问题。
 			- 如果worker节点已经加入过集群，则该worker节点会不会再加入master的集群，不做任何操作；未加入过集群的worker节点会加入到master集群中；用户需要自行保证各worker节点，以及worker节点与master节点Kubernetes版本一致，避免不可预测的问题。
 	- 安装脚本安装的组件由两部分组成，场景1,2,3默认安装的组件加上EXTRA_COMPONENT中配置的组件
 	- 如果用户已经安装了Kubernetes，其版本不能高于1.21
 	- 多Master场景下每个Master的kube_interface参数的值必须为本机上已存在的网卡名
 	- 无论是单Master、还是多Master场景，k8s_api_server_ip参数必须配置为本机上已经存在的IP
 	- 节点的存放Docker镜像的磁盘分区需要保留至少30%的空间
 	- 如果节点的IP网段与默认的K8s集群网段冲突，请用户修改inventory_file中的`POD_NETWORK_CIRD`参数为其他私有网段，如：10.0.0.0/16
 	- 训练节点需要配置device IP，可参考[配置训练服务器NPU的device IP](https://www.hiascend.com/document/detail/zh/canncommercial/60RC1/envdeployment/instg/instg_000039.html)
 	- 场景1中，inventory_file配置文件`[master]`下配置的节点个数必须为奇数，如1,3,5...


## 其他问题

 1. 某个节点的calico-node-**出现READY “0/1”

     **分析：**
    - 使用`kubectl describe pod `命令查看K8s master节点的`calico-node`Pod时有报错信息“calico/node is not ready: BIRD is not ready: BGP not established with...”
    - kubelet日志报错“failed to run Kubelet: running with swap on is not supported, please disable swap”，通过`free`查询，存在swap空间。

    **原因：**<br />
    操作系统的swap分区未关闭

    **解决方案：**<br />
    执行命令`swapoff -a`


 2. 部署高可用集群时，出现phase preflight: couldn't validate the identity of the API Server: Get `"https://192.168.56.120:6443/api/v1/namespaces/kube-public/configmaps/cluster-info?timeout=10s"`: dial tcp 192.168.56.120:6443: connect: connection refused\nTo see the stack trace of this error execute with --v=5 or higher

    **原因：**<br />
    有多个master节点存在虚拟ip

     **解决方案：**<br />
    重启master节点，使kube-vip部署的虚拟ip地址失效

 3. 使用`kubectl`命令时，报错:The connection to the server xxxxx:6443 was refused - did you specify the right host or port?
    **原因：**<br />
    有可能是配置了代理；k8s服务未启动；未给用户配置授权文件

    **解决方案：**<br />
    如果是配置了代理，使用如下命令，去掉代理后再试
    ```
    unset http_proxy https_proxy
    ```
    如果是k8s服务未启动，使用如下命令，启动K8s服务后再试
    ```
    systemctl start kubelet
    ```
    如果未给用户配置授权文件，使用如下命令，配置授权文件后再试
    ```
    export KUBECONFIG=/etc/kubernetes/admin.conf
    或者
    export KUBECONFIG=/etc/kubernetes/kubelet.conf
    ```

 4. 部署多master集群时，需要使用ip a查看每个节点虚拟ip有没有被分配，如果有则需要在对应节点上使用以下命令删除
    ```
    ip addr delete <ip地址> dev <网卡名>
    ```
# 历史版本
<table>
<thead>
  <tr>
    <th>版本</th>
    <th>资源</th>
    <th>发布日期</th>
  </tr>
</thead>
<tbody>
  <tr>
    <td>3.0.0</td>
    <td><a href=""></a></td>
    <td>2022.12.30</td>
  </tr>
  <tr>
    <td>3.0.RC3</td>
    <td><a href="https://ascend-repo-modelzoo.obs.cn-east-2.myhuaweicloud.com/MindXDL/3.0.RC3/resources.tar.gz">https://ascend-repo-modelzoo.obs.cn-east-2.myhuaweicloud.com/MindXDL/3.0.RC3/resources.tar.gz</a></td>
    <td>2022.09.30</td>
  </tr>
</tbody>
</table>

# CHANGELOG
<table>
<thead>
  <tr>
    <th>版本</th>
    <th>版本说明</th>
  </tr>
</thead>
<tbody>
  <tr>
    <td>3.0.0</td>
    <td><li>支持按场景进行安装部署</li><br /><li>部署脚本支持运行环境为：Ubuntu 18.04和OpenEuler 20.03 LTS</li><br /><li>支持使用Harbor仓</li><br /><li>支持K8s多master部署</li></td>
  </tr>
</tbody>
</table>
