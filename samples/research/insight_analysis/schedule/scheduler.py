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
from apscheduler.executors.pool import ProcessPoolExecutor
from apscheduler.schedulers.background import BackgroundScheduler
from pytz import utc

from schedule.job import ProcessJob


class Scheduler(object):
    """
    classdocs
    """

    def __init__(self):
        """
        Constructor
        """
        executors = {
            'default': {'type': 'threadpool',
                        'max_workers': 1},
            'processpool': ProcessPoolExecutor(max_workers=1)
        }
        job_defaults = {
            'coalesce': False,
            'max_instances': 1,
        }
        self._sched = BackgroundScheduler(executors=executors,
                                          job_defaults=job_defaults,
                                          timezone=utc)

    def get_apscheduler(self):
        return self._sched

    def start_analyze_schedule(self):
        stop_process_sched_job = ProcessJob(self)
        stop_process_sched_job.create_job()
        self._sched.start()
