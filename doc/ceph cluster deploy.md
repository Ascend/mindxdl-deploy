# ceph集群部署

本教程使用cephadm部署工具部署
使用ubuntu 18.04部署，ceph版本为15.2
本教程参考ceph官网，官网为 https://docs.ceph.com/en/pacific/
本教程使用节点信息如下

|node| hostname |ip| 操作系统版本|架构|
|:-----:|:-------:|:-------:|:-------:|:----:|
|node1|ceph1|51.38.65.33|ubuntu 18.04| x86|
|node2|ceph1|51.38.65.35|ubuntu 18.04| x86|
|node3|ceph1|51.38.68.151|ubuntu 18.04| x86|

ARM架构设备也支持部署
满足以下条件存储设备才会被视为可用：
+ 设备必须没有分区
+ 设备不得具有任何LVM状态
+ 设备不能被挂载
+ 设备不能包含文件系统
+ 设备不能包含 CephBlueStore OSD
+ 设备必须大于5GB

若是作为存储设备的磁盘数量≤3，请尽量保持各盘容量大小一致，否则，数据归置可能会异常。

1. 安装docker-ce
    **此步骤需要各个节点执行**
    在华为开源镜像站查看容器类源https://mirrors.huaweicloud.com/home , 点击dokcer-ce,查看docker-ce源配置教程，请注意选择系统为ubuntu。
    ```bash
    sudo apt-get remove docker docker-engine docker.io
    sudo apt-get install apt-transport-https ca-certificates curl gnupg2 software-properties-common
    
    curl -fsSL https://repo.huaweicloud.com/docker-ce/linux/ubuntu/gpg | sudo apt-key add -

    # 对于amd64架构的计算机，添加软件仓库:
    sudo add-apt-repository "deb [arch=amd64] https://repo.huaweicloud.com/docker-ce/linux/ubuntu $(lsb_release -cs) stable"

    sudo apt-get update
    sudo apt-get install docker-ce
    ```
2. 安装cephadm
    参见清华源[ceph清华大学开源软件镜像站](https://mirrors.tuna.tsinghua.edu.cn/help/ceph/)。cephadm安装方式有两种，具体参考[cephadm安装](https://docs.ceph.com/en/quincy/cephadm/install/#install-cephadm)， 推荐使用基于特定发行版的安装方式，并修改源为第三方镜像源。
    执行以下命令修改源为三方源。
    ```bash
    wget -q -O- 'https://download.ceph.com/keys/release.asc' | sudo apt-key add -
    sudo apt-add-repository 'deb https://mirrors.tuna.tsinghua.edu.cn/ceph/debian-octopus/ buster main'
    sudo apt update
    ```
    安装后执行apt install cephadm 安装cephadm。
3. 部署ceph集群
    执行命令`cephadm bootstrap --mon-ip xxx.xxx.xxx.xxx`,请其中的xxx换成你的节点IP。
    以上命令会拉取镜像 ，所以预计会等待30分钟左右，视网速而定。命令执行成功后会输出一些关键信息，包括集群配置文件 ，admin的认证key，集群的Dashboard信息，以及如何进入ceph shell环境，请注意留存。
    ```bash
    [root@nceph1 ~]# cephadm bootstrap --mon-ip xxx.xxx.xxx.xxx
    ..........
    Wrote keyring to /etc/ceph/ceph.client.admin.keyring
    Wrote config to /etc/ceph/ceph.conf
    ..........
    ..........
    Ceph Dashboard is now availabe at:
             URL: https://ceph1:8443/
            User: admin
        Password: zisu8xegser
    You can access the ceph cli with:
    sudo /usr/sbin/cephadm shell --fsid xxxxxxxxxxxxx -c /etc/ceph/ceph.conf -k /etc/ceph/ceph.client.admin.keyring
    ```
4. 登录DashBoard设置存储副本为2
    1. 使用步骤3中出现的Dashboard信息登录Dashboard，点击左侧的Configuration。
    2. 点击右上角的“Level:basic”旁边的叉，关闭过滤条件，并在搜索框输入osd_pool_default_size，进行搜索。
    3. 选中“osd_pool_default_size",点击左上角编辑，进入编辑界面。
    4. 把global对应的值设置为2，即为设置ceph存储集群副本为2，设置完成，点击保存。
5. 把集群的ssh密钥分发到其它节点
    `ssh-copy-id -f -i /etc/ceph/ceph.pub root@*<new-host>*`

    ```bash
    ssh-copy-id -f -i /etc/ceph/ceph.pub root@51.38.65.35
    ssh-copy-id -f -i /etc/ceph/ceph.pub root@51.38.68.203
    ```
6. 添加节点
    进入ceph shell 环境，执行下面命令：
    ```bash
    ceph orch host add ceph2 51.38.65.33
    ceph orch host add ceph3 51.38.68.151
    ```
    **这里ceph2和ceph3是对应节点的hostname**
7. 部署osd 
    在节点上部署osd有两种方式 ，一种是在未使用的设备中自动创建osd
    `ceph orch apply osd --all-available-devices`
    另一种是从特定节点上特定设备创建osd
    `ceph orch daemon add osd host1:/dev/sdb`
    示例:
    ```bash
    ceph orch daemon add osd ceph1:/dev/sdb
    ceph orch daemon add osd ceph2:/dev/sdb
    ceph orch daemon add osd ceph3:/dev/sda
    ```
    执行完以后可以命令`ceph -s`查看状态
    ```bash
    [root@nceph1 ~]# ceph -s
     .......   
     .......
       osd: 3osds：3 up (since 23s), 3 in (since 23)
    ........
    ........
    ```
8. 部署MDS
    先创建CephFs文件系统，CephFS需要两个Pool， cephfs-data和cephfs-metadata,分别存储文件数据和文件元数据。
    ```bash
    ceph osd pool create cephfs_data 16
    ceph osd pool create cephfs_metadata 16
    # 创建一个CephFS 名字为cephfs
    ceph fs new cephfs cephfs_metadata cephfs_data
    # 部署MDS
    ceph orch apply mds cephfs --placement="2 ceph1 ceph2 ceph3"
    ```
    部署完成后可以通过`ceph -s`查看状态
    ```bash
    [root@nceph1 ~]# ceph -s
     .......   
     .......
        mds: cephfs: 1 {0=cephfs.ceph2.iphpfs=up:active} 2 up:stadnby
    ........
    ........
    ```
    可以看到已经有一个MDS状态是active，代表mds已经正常工作。默认情况下，ceph只支持一个活跃的MDS，其它的作为备用MDS。可以通过以下命令查看对应文件系统状态：
    `ceph fs status cephfs`
    ```bash
    [root@nceph1 ~]# ceph fs status cephfs
     .......   
     ========
     RANK    STATE            MDS          ACTIVITY     DNS    INOS
     ......  active
    ........
    ........
    ```
    至此，安装完毕。
9. 挂载测试
    a. 退出ceph shell环境，执行命令查看 admin用户密钥， `cat /etc/ceph/ceph.client.admin.keyring` 。
    b. 在需要进行挂载的节点创建挂载目录。
    c. 执行挂载测试
    ```bash
    mount -t ceph 51.38.65.33:6789:/  /ceph_test -o name=admin,secret=A......LLFSFF==
    ```
    **示例为的/ceph_test请替换成你创建的挂载目录 ，‘secret=’后面的值即为你对应的admin的key**