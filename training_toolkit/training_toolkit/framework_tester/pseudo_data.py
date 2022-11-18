import numpy as np


def gen_linear_regression_data(data_num, k, b, derivation):
    """
    generate pseudo data for linear regression
    Args:
        data_num: sample num of data
        k: parameter
        b: parameter
        derivation: noise

    Returns:

    """
    np.random.seed(0)
    train_x = np.asarray(list(range(data_num)))
    train_y = np.asarray([[np.random.normal(k * i, derivation)] for i in range(data_num)]) + b
    return train_x.tolist(), train_y.tolist()
