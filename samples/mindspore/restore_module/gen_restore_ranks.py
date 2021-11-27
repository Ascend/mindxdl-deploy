from k8s_client.config_map import ConfigMap
from restore_manager.restore_manager import RestoreManager

if __name__ == "__main__":
    res_manager = RestoreManager()
    config_map_handler = ConfigMap()
    fault_ranks = config_map_handler.get_fault_ranks(namespace="vcjob")
    res_manager.generate_restore_strategy(
        strategy_input_file_path="",
        fault_ranks=fault_ranks,
        restore_strategy_output_file_path="/job/code/restore_ranks.sh"
    )


