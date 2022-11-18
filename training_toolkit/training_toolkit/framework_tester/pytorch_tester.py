import os
import signal

import torch
from torch.utils.data import DataLoader, Dataset
import torch.npu
import torch.multiprocessing as mp
import torch.distributed as dist

from training_toolkit.framework_tester.pseudo_data import gen_linear_regression_data
from training_toolkit.config.config import DEVICE_RANK_LIST_ENV_KEY, RANK_SIZE_ENV_KEY, PYTORCH_RANK_ENV_KEY, \
    MAX_CHIP_ONE_NODE, PYTORCH_MASTER_IP_ENV_KEY, PYTORCH_MASTER_PORT_ENV_KEY


def receive_signal(signum, stack):
    print(f"It's pytorch {os.getpid()}, received signal {signum}")
    exit(signum)


class TorchDataset(Dataset):
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __len__(self):
        return len(self.x)

    def __getitem__(self, item):
        return torch.Tensor([self.x[item]]), torch.Tensor([self.y[item]])


class Model(torch.nn.Module):
    def __init__(self):
        super(Model, self).__init__()
        self.linear = torch.nn.Linear(1, 1)

    def forward(self, x):
        return self.linear(x)


def main_worker(device_index: int, distributed: bool, rank_size: int, device_id_list: list, device_num_on_node: int):
    node_rank = int(os.environ[PYTORCH_RANK_ENV_KEY])
    device_id = device_id_list[device_index]
    if device_id == 0:
        print(f"process on node: {node_rank}")

    model = Model()

    if distributed:
        device_rank = node_rank * device_num_on_node + device_id
        if device_id == 0:
            print(f"init process group: {os.environ[PYTORCH_MASTER_IP_ENV_KEY]}:"
                  f"{os.environ[PYTORCH_MASTER_PORT_ENV_KEY]}")
        dist.init_process_group(backend="hccl", world_size=rank_size, rank=device_rank)

    loc = f"npu:{device_id}"
    torch.npu.set_device(loc)
    model = model.to(loc)
    loss_fn = torch.nn.MSELoss().to(loc)
    optimizer = torch.optim.Adam(params=model.parameters())

    data_num = 10000
    k = 2
    b = 3
    derivation = 1
    train, label = gen_linear_regression_data(data_num, k, b, derivation)

    dataset = TorchDataset(train, label)

    if distributed:
        model = torch.nn.parallel.DistributedDataParallel(model, device_ids=[device_id])

    train_data = DataLoader(dataset=dataset,
                            batch_size=64,
                            shuffle=True,
                            pin_memory=False,
                            drop_last=True)

    model.train()
    node_num = 1 if rank_size <= MAX_CHIP_ONE_NODE else rank_size // MAX_CHIP_ONE_NODE
    total_epoch = 30 * node_num
    for epoch in range(total_epoch):
        total = 0.
        for step, batch in enumerate(train_data):
            x, y = list(map(lambda i: i.to(loc, non_blocking=True), batch))
            x = x.to(torch.float)

            out = model(x)
            loss = loss_fn(out.view(-1), y.view(-1))
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            total += loss.item()
            if device_id == 0 and step == 0:
                print("Epoch: %d/%d. Loss: %.4f" % (epoch + 1, total_epoch, total / (step + 1)))
            torch.npu.synchronize()


def torch_train():
    signal.signal(signal.SIGTERM, receive_signal)
    signal.signal(signal.SIGINT, receive_signal)
    rank_size = int(os.environ[RANK_SIZE_ENV_KEY])
    device_id_list = list(map(int, os.environ[DEVICE_RANK_LIST_ENV_KEY].split(",")))

    distributed = rank_size > 1
    device_num_on_node = len(device_id_list)

    print(f"rank id list: {device_id_list}, rank size: {rank_size}")
    print(f"device count over current node: {torch.npu.device_count()}")
    print(f"npu is available: {torch.npu.is_available()}")
    print(f"distributed: {distributed}")
    if distributed:
        mp.spawn(main_worker, nprocs=device_num_on_node,
                 args=(distributed, rank_size, device_id_list, device_num_on_node))
    else:
        main_worker(0, distributed, rank_size, device_id_list, device_num_on_node)


if __name__ == '__main__':
    torch_train()
