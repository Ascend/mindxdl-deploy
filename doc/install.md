# 快速入门

## 功能描述

本文主要介绍如何使用ansible安装mindxdl所需开源软件安装。其中包含如下开源软件

| 软件名        | 备注                             |
| ---------- | ------------------------------ |
| docker     | 集群中所有节点都需要安装                   |
| kubernetes | k8s平台                          |
| mysql      | 安装在k8s集群中，挂载host的文件系统，需要绑定特点节点 |
| nfs        | 所有节点都需要安装nfsclient             |
| harbor     | 容器镜像仓                          |
| prometheus | 安装在kubernetes集群中               |
| grafana    | 安装在kubernetes集群中               |

## 下载本工具

下载地址[MindXDL-deploy: MindX DL platform deployment.](https://gitee.com/ascend/mindxdl-deploy)下载。下载方式：

1. 使用git clone

2. 下载master分支的[zip文件](https://gitee.com/ascend/mindxdl-deploy/repository/archive/master.zip)
   
   

然后联系工程师取得开源软件的离线安装包。将本工具解压后放在HOME目录下。再将离线安装包解压放在工具目录中。按如下方式放置

```bash
root@master:~# ls
mindxdl-deploy
resources             //resources目录，由resources.tar.gz解压得到
resources.tar.gz
```

## 安装步骤

### 步骤1：安装ansible

工具中包含一个install_ansible.sh文件用于安装ansible

按如下步骤执行即可：

```bash
root@master:~/mindxdl-deployer#./install_ansible.sh
root@master:~/mindxdl-deployer#ansible --version
config file = None
configured module search path = ['/root/.ansible/plugins/modules', '/usr/share/ansible/plugins/modules']
ansible python module location = /usr/local/lib/python3.6/dist-packages/ansible
ansible collection location = /root/.ansible/collections:/usr/share/ansible/collections
executable location = /usr/local/bin/ansible
python version = 3.6.9 (default, Jan 26 2021, 15:33:00) [GCC 8.4.0]
jinja version = 3.0.1
libyaml = True


```

安装完成后执行ansible --version查看ansible是否安装成功

如果环境有网络也可通过apt和python pip安装ansible

```bash
root@master:~#apt install python3-pip
root@master:~#python3 -m pip install ansible
```

### 步骤2：配置集群信息

需要提前规划好如下集群信息：

1. master节点ip

2. work节点ip

3. mysql安装的节点ip

4. harbor安装的节点ip

5. nfs服务器信息。nfs可使用已有nfs服务器。如不需要安装nfsserver，去掉nfs_server配置即可

```bash
[master]
localhost ansible_connection=local

[worker]
worker1_ip
worker1_ip
worker1_ip

[mysql]
localhost ansible_connection=local

[nfs_server]
localhost ansible_connection=local
```

注意：k8s要求所有设备的hostname不一样，因此建议执行安装前设置所有设备使用不同的hostname。如果未统一设置且存在相同hostname的设备，那么可在inventory文件中设置set_hostname变量，安装过程将自动设置设备的hostname。例如：

```ini
[master]
localhost ansible_connection=local

[worker]
worker1_ipaddress  set_hostname="worker1"
worker2_ipaddress  set_hostname="worker1" 
worker3_ipaddress
```

inventory文件配置详细可参加[[How to build your inventory &mdash; Ansible Documentation](https://docs.ansible.com/ansible/latest/user_guide/intro_inventory.html)]

### 步骤3：检查集群状态

在目录中执行：

```bash
ansible -i inventory_file all -m ping
localhost | SUCCESS => {
    "ansible_facts": {
        "discovered_interpreter_python": "/usr/bin/python3"
    },
    "changed": false,
    "ping": "pong"
}
worker1_ipaddres | SUCCESS => {
    "ansible_facts": {
        "discovered_interpreter_python": "/usr/bin/python3"
    },
    "changed": false,
    "ping": "pong"
}
```

当所有设备都能ping通，则表示inventory中所有设备连通性正常

### 步骤4：安装配置

本工具中提供了all.yaml文件用于自动安装所有组件。可更加需要自行调整安装配置

如果master存在多个网卡，请打开all.yaml找到如下部分：

```yaml
- hosts: master
  roles:
    - role: mindx.k8s.master
    - role: mindx.k8s.label
      vars:
        label_key: masterselector
        label_value: dls-master-node
    - role: mindx.k8s.prom
    - role: mindx.kubeedge

```

在mindx.k8s.master角色下增加apiserver_advertise_address参数，用于指定k8s apiserver绑定的ip地址

```yaml
- hosts: master
  roles:
    - role: mindx.k8s.master
      vars:
        apiserver_advertise_address: ipaddress
    - role: mindx.k8s.label
      vars:
        label_key: masterselector
        label_value: dls-master-node
    - role: mindx.k8s.prom
    - role: mindx.kubeedge
```

master节点中将自动安装Prometheus和kubeedge中的edgecore。如不需要，将对应角色删除即可。

### 步骤5：执行安装

使用ansible-playbook执行安装：

```bash
root@master:~/mindxdl-deployer#ansible-playbook -i inventory_file all.yaml
```

### 步骤6：安装后检查

检查kubernetes节点

```bash
root@master:~# kubectl get nodes -A
NAME             STATUS   ROLES    AGE   VERSION
master           Ready    master   60s   v1.19.16
work1            Ready    worker   60s   v1.19.16
检查
```

检查kubenetes pods

```bash
root@master:~# kubectl get pods -A
NAMESPACE     NAME                                       READY   STATUS    RESTARTS   AGE
default       node-exporter-ds5f5                        1/1     Running   0          19h
default       node-exporter-s5j9s                        1/1     Running   1          19h
kube-system   calico-kube-controllers-659bd7879c-l7q55   1/1     Running   2          19h
kube-system   calico-node-5zk76                          1/1     Running   1          19h
kube-system   calico-node-cxhdn                          1/1     Running   0          19h
kube-system   coredns-f9fd979d6-l42rb                    1/1     Running   2          19h
kube-system   coredns-f9fd979d6-x2bg2                    1/1     Running   2          19h
kube-system   etcd-node-10-0-2-15                        1/1     Running   1          19h
kube-system   grafana-core-58664d599b-4d8s8              1/1     Running   1          19h
kube-system   kube-apiserver-node-10-0-2-15              1/1     Running   1          19h
kube-system   kube-controller-manager-node-10-0-2-15     1/1     Running   5          19h
kube-system   kube-proxy-g65rn                           1/1     Running   1          19h
kube-system   kube-proxy-vqzb7                           1/1     Running   0          19h
kube-system   kube-scheduler-node-10-0-2-15              1/1     Running   4          19h
kube-system   prometheus-577fb6b799-k6mwl                1/1     Running   1          19h
mindx-dl      mysql-55569fc484-bb6kw                     1/1     Running   1          19h
```



# 高级配置

## 角色介绍

本工具提供了多个ansible role。可灵活组以满足不同安装需求

### 角色：mindx.docker

安装docker-ce

### 角色：mindx.k8s.install

安装kubernetes相关二进制文件。并启动kubelet。改角色只安装，不作任何配置

### 角色：mindx.k8s.master

初始化集群。该角色将在执行的节点上执行kubeadm init初始化kubernetes集群。并安装calico网络插件

参数：

| 参数名                         | 说明                                                             |
| --------------------------- | -------------------------------------------------------------- |
| apiserver_advertise_address | 指定kubenetes的apiserver绑定的ip地址，默认空。在多网卡时建议配置，防止apiserver监听到其他网卡上 |



### 角色：mindx.k8s.worker

加入集群。该角色将在执行的节点上执行kubeadm join加入已经初始化好kubernetes集群。需在mindx.k8s.master之后执行

