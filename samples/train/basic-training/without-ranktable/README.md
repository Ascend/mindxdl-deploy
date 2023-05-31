## introduction
This directory is used to support the training method of **without ranktable** for NPUs with chip type **Ascend 910** and **Ascend 910B**. It includes sample scripts for starting training and yaml files for creating tasks through the command line in K8s scenarios. It can support Tensorflow, MindSpore, and Pytorch training frameworks. The relevant training model code and dataset need to be prepared by the user.

## scene
The training sample script and yaml file are applicable to the following scenarios: 

| framework     | basic training | resumable training |
| :----------: | :--------: | :--------: |
| Tensorflow | √      | ×      |
| Pytorch    | √      | ×       |
| MindSpore    | √      | ×       |