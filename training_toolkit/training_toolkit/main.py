import sys
import json
import os
from argparse import ArgumentParser, Namespace

from training_toolkit.config.config import PlatformType
from training_toolkit.logger.log import run_log
from training_toolkit.utils.env_preparation import set_dependence_env, set_task_env
from training_toolkit.framework_tester.utils import set_manager
from training_toolkit.monitor.manager import ProcessManager


def prepare_args() -> Namespace:
    parser = ArgumentParser(description="MindXDL Training Toolkit")
    parser.add_argument("--test",
                        type=str,
                        default="",
                        choices=["", PlatformType.MindSpore.value, PlatformType.Pytorch.value,
                                 PlatformType.TensorFlow.value],
                        help="test a training task can be run or not over specific framework.")

    parser.add_argument("--wo-ranktable",
                        action="store_true",
                        help="run without ranktable")

    parser.add_argument("--platform",
                        type=str,
                        default=PlatformType.MindSpore.value,
                        choices=[PlatformType.MindSpore.value, PlatformType.Pytorch.value,
                                 PlatformType.TensorFlow.value],
                        help="choose the training platform for current task."
                        )

    parser.add_argument("--cd",
                        type=str,
                        default="",
                        help="change the working directory of the task process"
                        )

    parser.add_argument("--cmd",
                        type=str,
                        default="",
                        help="command fot training task, like 'python train.py'"
                        )

    parser.add_argument("--bind-cpu",
                        action="store_true",
                        help="bind cpu to training process. Pytorch is not supported"
                        )

    parser.add_argument("--log-dir",
                        type=str,
                        default="",
                        help="directory path for training task logs; By default: working dir"
                        )

    parser.add_argument("--disable-log",
                        action="store_true",
                        help="disable log redirecting"
                        )

    parser.add_argument("--extra-env",
                        type=str,
                        action="append",
                        help="add custom environment variable"
                        )

    return parser.parse_args()


def main():
    args = prepare_args()
    if args.test:
        args.platform = args.test

    run_log.info(f"args are: \n {json.dumps(vars(args), indent=4, ensure_ascii=False)}")

    # prepare env of CANN (NNAE, toolkit or TFPlugin)
    set_dependence_env()

    # prepare env for training task
    ok, server_info = set_task_env(args)

    if not ok:
        return

    run_log.info(f"environment variables: \n {json.dumps(dict(os.environ), ensure_ascii=False, indent=4)}")

    # init task manager
    manager = ProcessManager(server_info)

    # choose to test the training environment, exit after testing done.
    if args.test:
        run_log.info(f"start testing over the specific platform: {args.test}")
        set_manager(manager, args.test)
        manager.run(bind_cpu=args.bind_cpu)
        code = manager.wait()
        manager.clean_all()
        if code == 0:
            run_log.info(f"success for testing: {args.test}. Now you can run your own task")
        else:
            run_log.error(f"failed for testing: {args.test}. Please check")
        return

    if not args.cmd:
        run_log.error("please set training cmd")
        return

    manager.cmd = args.cmd
    manager.cd = args.cd
    manager.log_dir = args.log_dir if not args.disable_log else None
    manager.platform = args.platform

    manager.run(bind_cpu=args.bind_cpu, extra_env=args.extra_env)
    code = manager.wait()
    manager.clean_all()
    run_log.info("task done. Please check the running details")
    sys.exit(code)


if __name__ == '__main__':
    main()
