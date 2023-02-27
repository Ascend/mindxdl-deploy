# -*- coding: utf-8 -*-
# Copyright 2022-2023 Huawei Technologies Co., Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ============================================================================
import collections
import glob
import os
import re
from abc import ABC, abstractmethod
from ast import literal_eval
from typing import Optional, List
from hashlib import sha256

from constants import constants
from constants.constants import MAX_FILE_PATH_LENGTH
from constants.constants import MAX_SIZE
from constants.constants import MAX_RANK_STRING_LENGTH
from logger.log import run_log
from validator.validators import ClassValidator, FileValidator
from validator.validators import DirectoryValidator
from validator.validators import MapValidator
from validator.validators import RankSizeValidator
from validator.validators import StringValidator


class FaultRanksManager(ABC):
    """
    Abstract class of fault ranks manager.
    """
    @abstractmethod
    def get_fault_ranks(self, file_path: Optional[str] = None) -> None:
        raise NotImplementedError


class FaultRanksDLManager(FaultRanksManager):
    """
    Get fault ranks for fault-torlence distrited training job.
    For MindX DL situation, fault ranks read from configmap related file
    For ModelArts sutiation, fault ranks calculated based on checkpoint directory content
    """
    def __init__(self):
        super().__init__()
        self.fault_config_path = constants.FAULT_RANK_CONFIG

    @staticmethod
    def _compute_hash(content: str) -> str:
        try:
            hash_code = sha256(content.encode('utf-8')).hexdigest()
            return hash_code
        except TypeError:
            return ""
        except ValueError:
            return ""
        except Exception:
            return ""

    @staticmethod
    def check_input_file(path: Optional[str]) -> bool:
        validation = DirectoryValidator(path, max_len=MAX_FILE_PATH_LENGTH) \
            .check_is_not_none() \
            .check_dir_name() \
            .path_should_exist(is_file=True, msg="Cannot find the fault ranks config file.") \
            .should_not_contains_sensitive_words() \
            .with_blacklist() \
            .check()

        if not validation.is_valid():
            return False

        if not FileValidator(path).check_file_size().check().is_valid():
            run_log.error("File size exceeds limited size.")
            return False
        return True

    def _fault_ranks_process(self, res: Optional[str], fault_ranks: str) -> str:
        """
        Get fault ranks process.
        :param res: configmap content
        :param fault_ranks: fault rank string
        :return: processed fault rank string
        """
        res = res.replace("null", "[]")
        if not StringValidator(res).is_valid():
            run_log.error("The content of the fault config file is invalid.")
            return fault_ranks

        if not MapValidator(literal_eval(res), inclusive_keys=["FaultRankIds"]).is_valid():
            run_log.error("The content of the fault config file has not key(FaultRankIds)")
            return fault_ranks

        record_fault_rank_list_content = str(literal_eval(res)["FaultRankIds"])
        if not StringValidator(record_fault_rank_list_content,
                               max_len=MAX_RANK_STRING_LENGTH).check_string_length().check().is_valid():
            run_log.error("The content of fault rank exceed the max string length.")
            return fault_ranks

        record_fault_rank_list = literal_eval(record_fault_rank_list_content)
        if not ClassValidator(record_fault_rank_list, collections.Iterable) \
                .check_isinstance() \
                .check().is_valid():
            run_log.error("The value of the key(FaultRankIds) is not list")
            return fault_ranks

        clear_fault_rank_list = []
        for ele in record_fault_rank_list:
            if ele.isdigit() and RankSizeValidator(literal_eval(ele)).check_rank_size_valid().check().is_valid():
                clear_fault_rank_list.append(ele)

        res_config_map_fault_ranks = ",".join(clear_fault_rank_list)
        fault_ranks += res_config_map_fault_ranks
        run_log.info(f"Fault ranks is {fault_ranks}, type is {type(fault_ranks)}")
        return fault_ranks

    def _restore_ranks_process(self, res: Optional[str], restore_ranks: str) -> str:
        """
        Get fault ranks process.
        :param res: configmap content
        :param fault_ranks: fault rank string
        :return: processed fault rank string
        """
        if not StringValidator(res).is_valid():
            run_log.error("The content of the fault config file is invalid.")
            return restore_ranks

        if not MapValidator(literal_eval(res), inclusive_keys=["RestoreRankIds"]).is_valid():
            run_log.error("The content of the fault config file has not key(FaultRankIds)")
            return restore_ranks

        restore_ranks_content = str(literal_eval(res)["RestoreRankIds"])

        if not StringValidator(restore_ranks_content,
                               max_len=MAX_RANK_STRING_LENGTH).check_string_length().check().is_valid():
            run_log.error("The content of fault rank exceed the max string length.")
            return restore_ranks

        record_restore_ranks_list = literal_eval(restore_ranks_content)
        if not ClassValidator(record_restore_ranks_list, collections.Iterable) \
                .check_isinstance() \
                .check().is_valid():
            run_log.error("The value of the key(FaultRankIds) is not list")
            return restore_ranks

        clear_restore_ranks_list = []
        for ele in record_restore_ranks_list:
            if ele.isdigit() and RankSizeValidator(literal_eval(ele)).check_rank_size_valid().check().is_valid():
                clear_restore_ranks_list.append(ele)

        res_config_map_restore_ranks = ",".join(clear_restore_ranks_list)
        restore_ranks += res_config_map_restore_ranks
        run_log.info(f"Fault ranks is {restore_ranks}, type is {type(restore_ranks)}")
        return restore_ranks

    def get_fault_ranks(self, ckpt_local_path: Optional[str] = None) -> str:
        """
        Get fault ranks in training job when exception happens.
        :param ckpt_local_path: default is None for DL sutiation
        :return: fault ranks
        """
        print("Start query fault ranks")
        run_log.info("Start query fault ranks.")
        fault_npu_file_path = os.path.join(self.fault_config_path, constants.FAULT_NPU_FILE)
        if not self.check_input_file(fault_npu_file_path):
            run_log.error("Fault npu file path is invalid or check code file path is invalid")
            return ""

        fault_ranks = ""
        try:
            with open(fault_npu_file_path, "r", encoding='utf-8') as fault_config_out:
                fault_ranks = self._fault_ranks_process(fault_config_out.read(MAX_SIZE), "")
        except OSError:
            run_log.error(f"Load fault config file failed, OSError raised")
        finally:
            run_log.info("Finish the operation for querying fault ranks")

        return fault_ranks

    def get_restore_ranks(self, ckpt_local_path: Optional[str] = None) -> str:
        """
        Get fault ranks in training job when exception happens.
        :param ckpt_local_path: default is None for DL sutiation
        :return: fault ranks
        """

        run_log.info("Start query fault ranks.")

        fault_npu_file_path = os.path.join(self.fault_config_path, constants.FAULT_NPU_FILE)
        if not self.check_input_file(fault_npu_file_path):
            run_log.error("Fault npu file path is invalid or check code file path is invalid")
            return ""

        restore_ranks = ""
        try:
            with open(fault_npu_file_path, "r", encoding='utf-8') as fault_config_out:
                restore_ranks = self._restore_ranks_process(fault_config_out.read(MAX_SIZE), "")
        except OSError:
            run_log.error(f"Load fault config file failed, OSError raised")
        finally:
            run_log.info("Finish the operation for querying fault ranks")

        return restore_ranks

    def clear_fault_ranks(self):
        run_log.info("Start clear fault ranks.")

        fault_npu_file_path = os.path.join(self.fault_config_path, constants.FAULT_NPU_FILE)
        if not self.check_input_file(fault_npu_file_path):
            run_log.error("Fault npu file path is invalid or check code file path is invalid")
            return
        try:
            with open(fault_npu_file_path, "r", encoding='utf-8') as fault_config_out:
                fault_map = literal_eval(fault_config_out.read(MAX_SIZE))
                if isinstance(fault_map, dict):
                    fault_map["RestoreRankIds"] = ""
            with open(fault_npu_file_path, "w", encoding='utf-8') as fault_config_out:
                fault_config_out.write(str(fault_map))
        except OSError:
            run_log.error(f"Load fault config file failed, OSError raised")
        finally:
            run_log.info("Finish the operation for querying fault ranks")

class FaultRanksMAManager(FaultRanksManager):
    @staticmethod
    def _check_path(path: Optional[str]) -> str:
        validation = DirectoryValidator(path)
        if not validation.is_valid():
            return ""
        return validation.get_value()

    @staticmethod
    def _get_rank_id(subdir: str) -> str:
        """
        Get rank id based on checkpoint sub directory
        :param subdir: checkpoint sub directory (contains rank information in standard naming principle for
        distributed model training)
        :return: rank id
        """
        pattern = re.compile(r'\d+')
        match_res = pattern.findall(subdir)
        if len(match_res) == 1:
            string_validation = StringValidator(match_res[0]).can_be_transformed2int().check()
            rank_id_validation = RankSizeValidator(int(match_res[0])).check_rank_size_valid().check()
            if string_validation.is_valid() and rank_id_validation.is_valid():
                return match_res[0]
        return ""

    def check_input_file(self, ckpt_local_path: Optional[str]) -> str:
        ckpt_local_path_res = self._check_path(ckpt_local_path)
        ckpt_local_real_path = os.path.realpath(ckpt_local_path_res)
        if not DirectoryValidator(ckpt_local_real_path) \
                .check_is_not_none() \
                .check_dir_name() \
                .path_should_exist(is_file=False, msg="Cannot find the checkpoint directory.") \
                .should_not_contains_sensitive_words() \
                .check_dir_file_number() \
                .with_blacklist() \
                .check() \
                .is_valid():
            return ""
        return ckpt_local_real_path

    def get_fault_ranks(self, ckpt_local_path: Optional[str] = None) -> str:
        """
        Inference fault ranks according to saved checkpoint files.
        :param ckpt_local_path: saved checkpoint files directory
        :return: fault ranks
        """
        run_log.info("Start query fault ranks.")
        ckpt_local_real_path = self.check_input_file(ckpt_local_path)
        if not ckpt_local_real_path:
            return ""

        fault_ranks_list = []
        try:
            for dirpath, dirnames, filenames in os.walk(ckpt_local_real_path):
                self._get_subdir_fault_ranks(dirnames, dirpath, fault_ranks_list)
        except OSError as os_exp:
            run_log.error(f"Get fault ranks for modelarts failed, {str(os_exp)}.")
            return ""
        except IndexError as index_exp:
            run_log.error(f"Get fault ranks for modelarts failed, index error raise {index_exp}, "
                          f"please check checkpoint directory.")
            return ""
        except Exception as exp:
            run_log.error(f"Get fault ranks for modelarts failed, exception raise {exp}.")
            return ""
        else:
            run_log.info("Get fault ranks for modelarts success.")
            return ",".join(fault_ranks_list)

    def _get_subdir_fault_ranks(self,
                                dirnames: List[str],
                                dirpath: str,
                                fault_ranks_list: List[str]):
        for subdir in dirnames:
            candi_dirs = os.path.join(dirpath, subdir)
            ckpt_pattern = os.path.join(candi_dirs, "*.ckpt")
            ckpt_exp_pattern = os.path.join(candi_dirs, "*breakpoint.ckpt")
            ckpt_all_files = glob.glob(ckpt_pattern)
            ckpt_exp_files = glob.glob(ckpt_exp_pattern)

            if not ckpt_exp_files and not self._get_rank_id(subdir):
                continue

            if not ckpt_exp_files and self._get_rank_id(subdir):
                fault_ranks_list.append(self._get_rank_id(subdir))
                continue

            ckpt_exp_files.sort(key=os.path.getmtime, reverse=True)
            ckpt_all_files.sort(key=os.path.getmtime, reverse=False)
            latest_exp_ckpt_file = ckpt_exp_files[0]
            oldest_ckpt_file = ckpt_all_files[0]
            if latest_exp_ckpt_file != oldest_ckpt_file and os.path.getsize(latest_exp_ckpt_file) != \
                    os.path.getsize(oldest_ckpt_file) and self._get_rank_id(subdir):
                fault_ranks_list.append(self._get_rank_id(subdir))
