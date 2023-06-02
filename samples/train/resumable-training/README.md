## introduction
This directory is used to support the **resumable training** feature of NPUs with chip type **Ascend 910**, and needs to be used in conjunction with the training method of **ranktable**. It includes sample scripts for starting training and yaml files for creating tasks through the command line in K8s scenarios. It can support Tensorflow, MindSpore, and Pytorch training frameworks. The relevant training model code and dataset need to be prepared by the user.

## scene
The training sample script and yaml file are applicable to the following scenarios: 

| framework     | basic training | resumable training |
| :----------: | :--------: | :--------: |
| Tensorflow | ×      | √      |
| Pytorch    | ×      | √       |
| MindSpore    | ×      | √       |

**Tip**: The resumable training example script and yaml file of Tensorflow framework are located in [the `ranktable` directory](../basic-training/ranktable/) directory.