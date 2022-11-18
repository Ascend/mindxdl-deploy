import os
import time
import sys
import signal

import numpy as np
from npu_bridge.npu_init import *

from training_toolkit.framework_tester.pseudo_data import gen_linear_regression_data
from training_toolkit.config.config import RANK_SIZE_ENV_KEY


def receive_signal(signum, stack):
    print(f"It's tensorflow {os.getpid()}, received signal {signum}")
    exit(signum)


class LogSessionRunHook(tf.train.SessionRunHook):
    def __init__(self, global_batch_size, data_num):
        self.global_batch_size = global_batch_size
        self.iterations_per_loop = 10
        self.iter_times = []
        self.num_records = data_num
        self.display_every = 100
        print(f"Py version: {sys.version.strip()}; TF version: {tf.__version__}")

    def before_run(self, run_context):
        self.t0 = time.time()
        return tf.train.SessionRunArgs(fetches=[tf.train.get_global_step(), 'loss:0'])

    def after_create_session(self, session, coord):
        self.elapsed_secs = 0.
        self.count = 0

    def after_run(self, run_context, run_values):
        batch_time = time.time() - self.t0
        self.iter_times.append(batch_time)
        self.elapsed_secs += batch_time
        self.count += 1
        global_step, loss = run_values.results
        if global_step == 1 or global_step % self.display_every == 0:
            dt = self.elapsed_secs / self.count
            sample_per_sec = self.global_batch_size * self.iterations_per_loop / dt
            epoch = global_step * self.global_batch_size / self.num_records
            self.elapsed_secs = 0.
            self.count = 0
            print(f"step:%6i epoch:%5.1f FPS:%7.1f loss:%6.3f" % (global_step, epoch, sample_per_sec, loss))


def input_fn(x, y, data_num, batch_size, epoch_num):
    dataset = tf.data.Dataset.from_tensor_slices((x, y)).repeat(epoch_num)
    dataset = dataset.shuffle(data_num).batch(batch_size, drop_remainder=True)
    return dataset


def linear_model(x):
    w = tf.get_variable("w", shape=[1])
    b = tf.get_variable("b", shape=[1])
    return w * x + b


def model_fn(features, labels, mode):
    y = linear_model(features)
    loss = tf.reduce_mean(tf.square(labels - y), name="loss")
    global_step = tf.train.get_global_step()
    optimizer = tf.train.AdamOptimizer()
    npu_optimizer = NPUDistributedOptimizer(optimizer)
    train_op = tf.group(tf.assign_add(global_step, 1), npu_optimizer.minimize(loss))
    return tf.estimator.EstimatorSpec(mode=mode, train_op=train_op, loss=loss)


def tensorflow_train():
    signal.signal(signal.SIGTERM, receive_signal)
    signal.signal(signal.SIGINT, receive_signal)
    group_size = int(os.environ[RANK_SIZE_ENV_KEY])

    data_num = 10000 * group_size
    k = 2
    b = 3
    derivation = 1
    epoch_num = 200
    batch_size = 256

    x, y = map(lambda x: np.asarray(x, dtype=np.float32).reshape(-1, 1), gen_linear_regression_data(data_num, k, b,
                                                                                                    derivation))

    npu_config = NPURunConfig(
        session_config=tf.ConfigProto(allow_soft_placement=True, log_device_placement=False)
    )

    trainer = NPUEstimator(
        model_fn=model_fn,
        config=npu_config
    )

    log_hook = LogSessionRunHook(global_batch_size=batch_size * group_size, data_num=data_num)
    max_steps = int(epoch_num * data_num // batch_size // group_size)
    print(f"pid: {os.getpid()}, group size: {group_size}, data num: {data_num}, max_steps: {max_steps}")
    trainer.train(input_fn=lambda: input_fn(x, y, data_num, batch_size, epoch_num), hooks=[log_hook],
                  max_steps=max_steps)


if __name__ == '__main__':
    tensorflow_train()
