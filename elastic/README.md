# 项目说明

基于断点续训临终遗言和恢复策略现有功能，优化用户集成功能到现有训练脚本的流程。

详细功能说明请参考MindXDL[用户文档](https://support.huawei.com/enterprise/zh/doc/EDOC1100234301/7f3a162c)

# 使用介绍

约束：
1. 训练脚本使用MindSpore的Model高阶API进行模型训练。
2. Model类train函数的callbacks参数包含周期性保存ckpt的callback。
3. 所有芯片的模型保存路径在同一个父路径下，芯片自身子目录名称包含芯片ID编号。比如xxx/rank_1，xxx/rank_2。
4. 节点故障场景恢复（某个节点的临终ckpt文件未保存），需要用户配置GROUP_INFO_FILE环境变量。该环境变量说明请参考MindSpore[官方文档](https://www.mindspore.cn/tutorials/experts/zh-CN/r1.8/parallel/fault_recover.html?highlight=group_info_file) 。需要为每个芯片训练进程设置不同的环境变量。例如，rank为x的芯片环境变量为xxx/rank_x/。

现象说明：
1. 该功能会加载用户指定模型保存路径中的可用模型文件。如果用户在训练脚本中自行实现了加载已有模型的功能，会出现加载两次模型文件的情况。

安装方式： 
- 方式一（推荐）：执行`python setup.py bdist_wheel`命令构建whl包，pip install xxx进行安装。 
- 方式二：直接将mindx_elastic源码目录放在训练项目根目录下。

功能集成流程：

```python
# 1. 引入ElasticModel
from mindx_elastic.ms_wrapper.model_wrapper import ElasticModel

# 2. MindSpore的Model实例作为参数实例化ElasticModel
model = ElasticModel(mindspore_model)

# 3. 执行train方法进行训练。train方法接口与mindspore Model类train接口保持一致
model.trian(epoch, train_dateset, callbacks, dataset_sink_mode, sink_size)

```



