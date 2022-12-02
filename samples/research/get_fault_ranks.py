from mindx_elastic.restore_module.fault_rank_manager.fault_rank_manager import FaultRanksDLManager

try:
    fault_ranks = FaultRanksDLManager().get_fault_ranks()
    print(fault_ranks)
except OSError:
    exit(1)
except Exception:
    exit(1)
