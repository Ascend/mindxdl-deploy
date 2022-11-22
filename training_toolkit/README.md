# 工具介绍

MindXDL training toolkit是配合MindXDL使用的训练工具，主要有以下应用场景：

1. 【环境验证】协助用户快速验证基于MindXDL搭建的训练集群是否能够正常执行训练任务；
2. 【模型训练】减少用户在执行训练任务时的相关环境变量配置以及不同框架下的脚本适配工作。

## 约束

1.

用户需要按照配套关系，完成计算节点昇腾NPU固件、驱动的安装，并按照[MindXDL指南](https://www.hiascend.com/document/detail/zh/mindx-dl/30rc3/overview/index.html)
完成相关组件的安装与配置。

2. 从昇腾社区获取，或自行构建相应训练框架的训练镜像。
3. 容器中运行环境相关的软件包：驱动、NNAE、TFPlugin等需要安装在默认路径下，即：/usr/local/Ascend

## 功能

1. 支持单机/多节点训练框架可用性验证（npu训练任务是否能正常执行）
    1. 环境包含hccl-controller生成的ranktable文件：支持**Pytorch，TensorFlow，MindSpore**三种框架的验证。
    2. 环境不包含hccl-controller生成ranktable文件：暂**不支持**MindSpore。
        1. TensorFlow：需要安装对应的TFA（TensorFlow
           Adapter），容器需要接入主机网络（类似Pytorch），用户需要在训练任务yaml中额外配置如下环境变量：CM_CHIEF_IP、CM_CHIEF_PORT、CM_CHIEF_DEVICE、CM_WORKER_IP、CM_WORKER_SIZE。环境变量含义请参考"
           TensorFlow环境变量"小节。
        2. Pytorch：用户需在训练任务yaml中额外配置如下环境变量：MASTER_ADDR、RANK、WORLD_SIZE。环境变量含义请参考"
           Pytorch环境变量"小节。
2. 自动解析ranktable文件：为不同训练框架配置所需的环境变量，例如：DEVICE_ID、RANK_ID、RANK_SIZE等。
3. 自动配置运行环境（CANN包）相关的环境变量：NNAE、Toolkit或者TFPlugin环境变量。
4. 支持用户自定义环境变量：支持用户为训练进程传入指定环境变量，使用方法参考"参数说明"的"extra-env"参数。
5. 日志重定向：假设用户指定日志保存路径为/log（如未指定，路径为：当前工作目录/training_toolkit_default_log_dir/）。
    1. 包含ranktable文件：
        1. TensorFlow和MindSpore：按device rank保存日志文件；如/log/0.log，/log/12.log
        2. Pytorch: 按node rank保存日志文件；Pytorch分布式训练有业务脚本fork子进程，因此只支持按节点收集；如/log/node_0.log
    2. 不包含ranktable文件：
        1. TensorFlow：由于无法获取子进程对应的device rank和本节点的node
           rank，使用节点ip+进程启动顺序编号作为日志文件路径；如/log/192.168.2.13/0.log（这里的0表示子进程启动顺序，和device
           id/rank无关）
6. 支持MindXDL高级特性：
    1. 临终遗言及恢复策略（细节请参考MindXDL用户手册）：工具需作为容器启动命令，即1号进程（pid为1）；"yaml样例"
       有PanGu-Alpha启动命令供用户参考
    2. 最小业务系统：需要利用工具提供的环境变量，完成业务脚本适配。

# 使用说明

## 三方依赖

工具本身不依赖第三方包；框架可用性验证涉及的三方包（MindSpore、Pytorch、TensorFlow及其依赖包）不包含在本工具依赖文件中，请自行安装训练框架所需的三方包。

## 编译安装

下载源码，进入根目录，执行如下命令进行编译打包：

```shell
python setup.py bdist_wheel
```

当前目录生成本工具的whl包：`./dist/mindx_training_toolkit-1.0.0-py3-none-any.whl`。

在需要使用的镜像中安装此whl包：

```shell
pip install mindx_training_toolkit-1.0.0-py3-none-any.whl
```

## 参数说明

| 参数名称           | 参数说明                                                                                                                                                                                                                                 | 参数类型   | 可选值                                       | 默认值                                                 |
|----------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------|-------------------------------------------|-----------------------------------------------------|
| --test         | 进行框架训练流程验证，支持单机和分布式验证                                                                                                                                                                                                                | string | ms,tf,tf2,pt                              | 空串：表示不进行验证                                          |
| --wo-ranktable | 是否适用ranktable进行训练环境配置；默认使用；如不使用，启动参数添加该参数即可                                                                                                                                                                                          | 无      | 无                                         | 无                                                   |
| --platform     | 训练任务使用的框架                                                                                                                                                                                                                            | string | ms,tf,pt                                  | ms                                                  |
| --cd           | 切换训练进程的工作目录                                                                                                                                                                                                                          | string | 合法且存在的目录                                  | 空串：表示不切换工作目录，训练进程的工作目录为使用本工具时的目录                    |
| --cmd          | 训练命令                                                                                                                                                                                                                                 | string | 可执行的训练命令，请用户确认命令的**可行性和安全性**，本工具**不做相关校验** | 空串：如无指定--test进行框架验证，直接退出工具                          |
| --log-dir      | 训练进程日志保存目录                                                                                                                                                                                                                           | string | 合法且存在的目录                                  | 空串：使用默认路径"当前工作目录/training_toolkit_default_log_dir/" |
| --disable-log  | 禁用日志重定向，**用户自行**处理训练进程日志；如需禁用，启动参数添加该参数即可                                                                                                                                                                                            | 无      | 无                                         | 无                                                   |
| --bind-cpu     | 为训练进程绑定指定的cpu，默认不绑核，如需使用，启动参数添加该参数即可。Pytorch不支持                                                                                                                                                                                      | 无      | 无                                         | 无                                                   |
| --extra-env    | 为训练进程添加额外的自定义环境变量。例如，在使用MindSpore进行分布式训练时，为每个训练进程指定通信域信息存储路径GROUP_INFO_FILE（详细介绍清参考MindSpore文档），可使用"--extra-env=GROUP_INFO_FILE=/xxx/xxx/rank_%RANK_ID%/group_info.pb"进行设置，工具会根据每个进程分配的芯片rank自动替换"%RANK_ID%"为对应的值。该参数可多次使用，以添加多个环境变量 | string | 无                                         | 无                                                   |

## 环境变量说明

1. 工具会自动解析并向训练进程注入环境变量，用户可以根据需求在训练脚本中使用这些环境变量。
2. 用户根据需求，可以通过训练yaml指定部分环境变量的值（参考"用户可指定"列）
3. 用户根据需求，可以通过训练yaml传入其他自定义环境变量，工具会注入训练进程中。
4. **启动命令参数使用环境变量方式**：在环境变量名左右加上百分号，如"--npu %DEVICE_ID%"，工具会将"%DEVICE_ID%"
   替换为对应的变量值；如果不存在对应环境变量，则不进行任何处理。可以参考"yaml样例"模型训练的命令示例。

## 通用环境变量

| 环境变量名                            | 取值样例                                    | 变量说明                                                                                                                                      | 用户可指定 | 默认值                                                                                                           |
|----------------------------------|-----------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------|-------|---------------------------------------------------------------------------------------------------------------|
| RANK_TABLE_FILE                  | /usr/serverid/devindex/config/hccl.json | 昇腾AI处理器资源配置文件，分布式训练的芯片资源信息                                                                                                                | 是     | /usr/serverid/devindex/config/hccl.json                                                                       |
| XDL_IP                           | 192.168.1.1                             | 当前计算节点host ip地址；由训练yaml传入，请参考"yaml样例"小节配置方式                                                                                               | 是     | 无：必须由用户传入；建议直接参考"yaml样例"使用host ip                                                                             |
| DEVICE_ID                        | 0                                       | NPU设备物理ID；昇腾910取值范围为0-7；当环境存在ranktable文件时才会配置此变量                                                                                          | 否     | 无：由ranktable解析得到                                                                                              |
| ASCEND_DEVICE_ID                 | 0                                       | NPU设备物理ID；昇腾910取值范围为0-7；当环境存在ranktable文件时才会配置此变量                                                                                          | 否     | 无：由ranktable解析得到                                                                                              |
| RANK_ID                          | 0                                       | NPU设备rank ID；昇腾910取值范围为0-4095；当环境存在ranktable文件时才会配置此变量                                                                                    | 否     | 无：由ranktable解析得到                                                                                              |
| DEVICE_INDEX                     | 0                                       | NPU设备rank ID；昇腾910取值范围为0-4095；当环境存在ranktable文件时才会配置此变量                                                                                    | 否     | 无：由ranktable解析得到                                                                                              |
| RANK_SIZE                        | 8                                       | 当前训练任务使用的NPU芯片数，取值范围1-4095                                                                                                                | 是     | 无：1、由ranktable解析得到；2、无ranktable训练TensorFlow模型，为用户指定的CM_WORKER_SIZE值；3、无ranktable训练Pytorch模型，为用户指定的WORLD_SIZE值 |
| NODE_NUM                         | 1                                       | 当前训练任务使用的计算节点个数，取值范围1-512                                                                                                                 | 否     | 无：根据RANK_SIZE求得                                                                                               |
| TERMINATION_GRACE_PERIOD_SECONDS | 600                                     | 优雅退出等待时间：当训练进程异常退出，或者训练工具接收到外部INT或TERM信号量，等待所有训练进程退出的时间。超时则强制删除训练进程。取值范围[30, 1800]                                                        | 是     | 600                                                                                                           |
| ASCEND_SLOG_PRINT_TO_STDOUT      | 0                                       | 芯片日志输出至标准输出流；"0"关闭，"1"开启。关闭是，存储默认路径为/root/ascend/log                                                                                      | 是     | 0                                                                                                             |
| HCCL_CONNECT_TIMEOUT             | 120                                     | 用于限制不同设备之间socket建链过程的超时等待时间，默认值120s。取值范围[120,7200]。不同设备进程在集合通信初始化之前由于其他因素会导致执行不同步。该环境变量控制设备间的建链超时时间，在该配置时间内各设备进程等待其他设备建链同步。               | 是     | 120                                                                                                           |
| HCCL_EXEC_TIMEOUT                | 600                                     | 用于限制不同设备之间执行时同步等待时间，默认值600s。取值范围[60,17340]。不同设备进程在分布式训练过程中存在卡间执行任务不一致（如仅特定进程保存checkpoint数据）。该环境变量控制设备间执行时同步等待阈值，在该配置时间内各设备进程等待其他设备执行通信同步。 | 是     | 600                                                                                                           |

## TensorFlow环境变量

| 环境变量名           | 取值样例        | 变量说明                                                    | 用户可指定 | 默认值       |
|-----------------|-------------|---------------------------------------------------------|-------|-----------|
| JOB_ID          | 12345       | 训练任务ID，用户自定义。仅支持大小写字母，数字，中划线，下划线。不建议使用以0开始的纯数字作为JOB_ID。 | 是     | 123456789 |
| CM_CHIEF_IP     | 192.168.1.1 | master rank所在node的ip地址。当**不使用ranktable**时，由**用户自行**指定   | 是     | 无：必须由用户传入 |
| CM_CHIEF_PORT   | 9678        | master node使用的socket端口。当**不使用ranktable**时，由**用户自行**指定   | 是     | 无：必须由用户传入 |
| CM_CHIEF_DEVICE | 0           | master rank使用的device id。当**不使用ranktable**时，由**用户自行**指定  | 是     | 无：必须由用户传入 |
| CM_WORKER_IP    | 192.168.1.2 | local node使用的host ip。当**不使用ranktable**时，由**用户自行**指定     | 是     | 无：必须由用户传入 |
| CM_WORKER_SIZE  | 8           | 当前任务使用的集群deivice数量。当**不使用ranktable**时，由**用户自行**指定       | 是     | 无：必须由用户传入 |

## Pytorch环境变量

| 环境变量名                  | 取值样例            | 变量说明                                                                                    | 用户可指定 | 默认值                    |
|------------------------|-----------------|-----------------------------------------------------------------------------------------|-------|------------------------|
| TASK_QUEUE_ENABLE      | 1               | 使用异步任务下发，异步调用acl接口。建议开启，开启设置为1                                                          | 是     | 1                      |
| MASTER_ADDR            | 192.168.1.1     | 分布式训练master节点ip。暂只支持host网卡                                                              | 是     | ranktable的第一个节点host ip |
| MASTER_PORT            | 29501           | 分布式训练master节点通信端口                                                                       | 是     | 29501                  |
| DEVICE_RANK_LIST       | 0,1,2,3,4,5,6,7 | 当前训练节点使用的设备rank列表                                                                       | 否     | 无：由工具根据训练配置生成          |
| RANK                   | 0               | 当前**计算节点**rank，取值0-511                                                                  | 是     | 无：由ranktable解析得到       |
| WORLD_SIZE             | 8               | 当前训练任务使用的device数量，取值范围1-4095                                                            | 是     | 无：由ranktable解析得到       |
| HCCL_WHITELIST_DISABLE | 1               | 配置在使用HCCL时是否关闭通信白名单。1：关闭白名单，无需校验HCCL通信白名单。0：开启白名单，校验HCCL通信白名单。此时需要配置HCCL_WHITELIST_FILE | 是     | 1                      |
| COMBINED_ENABLE        | 1               | 设置是否开启combined标志，用于优化非连续两个算子组合类场景，1为开始                                                  | 是     | 1                      |
| HCCL_IF_IP             | 192.168.1.1     | 配置HCCL的初始化root通信网卡ip。暂只支持host网卡，且只能配置一个ip地址。                                            | 是     | 无：同"XDL_IP"            |


## 日志

工具的日志默认路径为：/var/log/mindx-dl/training_toolkit，run.log文件记录了运行日志。

## 使用场景介绍

### 一、训练环境可用性验证

1. 验证MindSpore在当前训练配置下是否能够正常执行训练：
```shell
training-toolkit --test ms
```

2. 验证Pytorch在当前训练配置下是否能够正常执行训练：
```shell
training-toolkit --test pt
```

3. 验证TensorFLow在当前训练配置下是否能够正常执行训练：
```shell
training-toolkit --test tf
```

验证的日志保存在/var/log/mindx-dl/training_toolkit/{ms/pt/tf}_test_log目录下。如果日志中的loss下降，表明模型训练收敛，当前训练环境和训练框架可用。如果异常退出，请检查环境配置是否异常，常见的异常排查方向：
1. 已按照对应框架适配手册完成框架和插件安装；
2. device-plugin组件启动参数配置使用ascend docker runtime，但未安装mindx toolbox；
3. NPU芯片被host训练任务占用。

也可通过工具运行日志查看验证流程是否成功执行。视具体的训练device数量和框架类型，整个验证流程持续几十秒至几分钟不等。

在观察到训练成功执行，loss正常下降后，也可直接终止验证流程。

### 二、模型训练

用户在昇腾设备上执行训练任务之前，需要进行一系列的环境变量配置，不同的训练框架配置的环境变量也存在或多或少的差异。这对用户而言是一种负担。

本工具可以自动地为用户配置训练所需的相关环境变量，让用户聚焦于模型的开发和训练。同时，可以为用户做一些简单的日志收集工作：按照不同的训练配置（训练框架类型，有无ranktable文件），实现按rank或按node完成日志的收集。

## yaml样例

yaml基于[mindxdl-deploy](https://gitee.com/ascend/mindxdl-deploy/tree/master/samples/train/yaml)仓提供的示例进行修改：

根据需要测试的训练框架或者执行特定的训练任务，修改[a800_vcjob_mindxdl_training_toolkit_demo.yaml](docs/a800_vcjob_mindxdl_training_toolkit_demo.yaml)中的"command"启动命令即可（yaml的任务名称、资源需求量、数据与代码挂载路径、镜像名称、节点筛选标签、DL高级特性参数配置等请按照实际情况进行修改和调整）。

1. 验证训练环境可用性：
   - 验证MindSpore：`command: ["/bin/bash", "-c", "training-toolkit --test ms"]`
   - 验证Pytorch：`command: ["/bin/bash", "-c", "training-toolkit --test pt"]`
   - 验证TensorFlow 1.15：`command: ["/bin/bash", "-c", "training-toolkit --test tf"]`
   - 验证TensorFlow 2.6.5：`command: ["/bin/bash", "-c", "training-toolkit --test tf2"]`
2. 模型训练：
   1. MindSpore：
      1. ResNet50：源码来自MindSpore开源[ModelZoo](https://gitee.com/mindspore/models)（样例于r1.9分支进行验证）： 
         - 单卡： `command: ["/bin/bash", "-c", "training-toolkit --cd /job/code/models-r1.9/official/cv/resnet/ --cmd 'python train.py --data_path=/job/data/resnet50/imagenet/train --config_path=./config/resnet50_imagenet2012_config.yaml --output_path=./output'"]`
         - 单机多卡/多节点：`command: ["/bin/bash", "-c", "training-toolkit --cd /job/code/models-r1.9/official/cv/resnet/ --cmd 'python train.py --run_distribute=True --device_num=%RANK_SIZE% --data_path=/job/data/resnet50/imagenet/train --config_path=./config/resnet50_imagenet2012_config.yaml --output_path=./output'"]`
      2. Pangu-Alpha：源码来自MindSpore开源[ModelZoo](https://gitee.com/mindspore/models)（样例于r1.9分支进行验证）：
         - 单机多卡/多节点：`command: ["/bin/bash", "-c", "training-toolkit --cd /job/code/models-r1.9/official/nlp/pangu_alpha --cmd 'python train.py --distribute=true --device_num=%RANK_SIZE% --data_url=/job/data/train_data/ --run_type=train --param_init_type=fp32 --mode=2.6B --stage_num=1 --micro_size=1 --per_batch_size=8'"]`
         - 使用mindx-elastic恢复策略（脚本请按照MindXDL用户手册完成适配）：`command: ["/bin/bash", "-c", "training-toolkit --cd /job/code/models-r1.9/official/nlp/pangu_alpha --extra-env=GROUP_INFO_FILE=/job/data/code/fault_torlence/pangu_alpha/16node/rank_%RANK_ID%/group_info.pb --cmd 'python train.py --distribute=true --device_num=%RANK_SIZE% --data_url=/job/data/train_data/ --run_type=train --param_init_type=fp32 --mode=2.6B --stage_num=1 --micro_size=1 --per_batch_size=8'"]`
   2. Pytorch（yaml需配置hostNetwork:true；Pytorch使用共享内存在进程之间共享数据，请设置充足的共享内存空间，否则加载数据集可能会产生异常）：
      1. ResNet50：源码来自Ascend开源[ModelZoo](https://www.hiascend.com/zh/software/modelzoo/models/detail/C/cf20ab8b8bea4032a6b056ab503112e4/1)
         - 单卡：`command: ["/bin/bash", "-c", "training-toolkit --platform pt --cd /job/code/ResNet50_for_Pytorch_1.4_code/ --cmd 'python pytorch_resnet50_apex.py --data /job/data/resnet50/imagenet --npu 0 -j64 -b512 --lr 0.2 --warmup 5 --label-smoothing=0.1 --epochs 90 --optimizer-batch-size 512'"]`
         - 单机多卡/多节点：`command: ["/bin/bash", "-c", "training-toolkit --platform pt --cd /job/code/ResNet50_for_Pytorch_1.4_code/ --cmd 'python ./DistributedResnet50/main_apex_d76_npu.py --data /job/data/resnet50/imagenet --seed=49 --workers=128 --learning-rate=1.6 --warmup=8 --label-smoothing=0.1 --mom=0.9 --weight-decay=1.0e-04 --static-loss-scale=128 --print-freq=1 --dist-backend=hccl --multiprocessing-distributed --benchmark=0 --device=npu --epochs=90 --batch-size=4096 --addr=%MASTER_ADDR% --world-size=%NODE_NUM% --rank=%RANK% --device-list=%DEVICE_RANK_LIST%'"]`
   3. TensorFlow（不使用ranktable时，yaml需配置hostNetwork: true，并配置上述的五个环境变量）：
      1. ResNet50：源码来自Ascend开源[ModelZoo](https://www.hiascend.com/zh/software/modelzoo/models/detail/C/d63df55c1f7f4112a97c8a33e6da89fe/1)
         - 单卡/单机多卡/多节点（配置对应config_file；样例为单卡，配合ranktable执行）：`command: ["/bin/bash", "-c", "training-toolkit --platform tf --cd /job/code/ResNet50_for_TensorFlow_1.7_code/ --cmd 'python ./src/mains/res50.py --config_file=res50_256bs_1p --max_train_steps=1000 --iterations_per_loop=100 --debug=True --eval=False --data_path=/job/data/resnet50/imagenet_TF --model_dir=./d_solution/ckpt%RANK_ID%'"]`