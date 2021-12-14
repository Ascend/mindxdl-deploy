#!/bin/bash
# Copyright 2021 Huawei Technologies Co., Ltd
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
ROOT_PATH=$(cd "`dirname $0`" || exit; pwd)

cd /job || exit
bash gen_ranks.sh

if [ $? -eq 0 ]; then
  source /job/code/restore_ranks.sh

  if [ $? -eq 0 ]; then
    cd ${ROOT_PATH} || exit
    bash train_start.sh
  else
    export RESTORE_RANKS=""
    export RESTORE_RANKS_MAP=""
    cd ${ROOT_PATH} || exit
    bash train_start.sh
  fi
else
  file=/job/code/restore_ranks.sh
  if [ -f $file ]; then
    rm -f /job/code/restore_ranks.sh
  fi
  cd ${ROOT_PATH} || exit
  bash train_start.sh
fi
