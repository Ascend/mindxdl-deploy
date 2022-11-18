from multiprocessing import cpu_count


def get_cpu_bound_subcmd_list(process_num=8) -> list:
    """
    generate cpu bound subcmd like "taskset -c 0-11"
    Args:
        process_num: total process num for current training task at current node.

    Returns:

    """
    r = []
    core_num = cpu_count()
    step = core_num // process_num
    for start in range(0, core_num, step):
        r.append(f"taskset -c {start}-{start + step - 1} ")
    return r
