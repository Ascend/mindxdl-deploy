import os
import shutil

from training_toolkit.monitor.manager import ProcessManager
from training_toolkit.config.config import WORK_DIR, LOG_PATH, PlatformType


def set_manager(manager: ProcessManager, platform: str):
    manager.platform = platform

    if platform == PlatformType.MindSpore.value:
        script_path = f"{WORK_DIR}/framework_tester/mindspore_tester.py"
        manager.log_dir = os.path.join(LOG_PATH, "ms_test_log")
    elif platform == PlatformType.Pytorch.value:
        script_path = f"{WORK_DIR}/framework_tester/pytorch_tester.py"
        manager.log_dir = os.path.join(LOG_PATH, "pt_test_log")
    elif platform == PlatformType.TensorFlow.value:
        script_path = f"{WORK_DIR}/framework_tester/tensorflow_tester.py"
        manager.log_dir = os.path.join(LOG_PATH, "tf_test_log")
        manager.platform = PlatformType.TensorFlow.value
    else:
        script_path = f"{WORK_DIR}/framework_tester/tensorflow2_tester.py"
        manager.log_dir = os.path.join(LOG_PATH, "tf2_test_log")
        manager.platform = PlatformType.TensorFlow.value

    manager.cmd = f"/usr/bin/python {script_path}"
    if os.path.exists(manager.log_dir):
        shutil.rmtree(manager.log_dir, ignore_errors=True)
    os.makedirs(manager.log_dir, exist_ok=True)
