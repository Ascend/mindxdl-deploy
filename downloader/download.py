#!/usr/bin/env python3
# coding: utf-8
# Copyright 2020 Huawei Technologies Co., Ltd
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
# ===========================================================================
"""downloader"""
import os
import sys
import shutil
import argparse
import platform

FILE_PATH = os.path.realpath(__file__)
CUR_DIR = os.path.dirname(__file__)

sys.path.append(CUR_DIR)

import logger_config
import pip_downloader
import os_dep_downloader
import software_mgr

LOG = logger_config.get_logger(__file__)


def download_python_packages(dst=None):
    """
    download_python_packages
    """
    script = os.path.realpath(__file__)
    require_file = os.path.join(os.path.dirname(script), 'requirements.txt')
    if dst is None:
        repo_path = os.path.join(os.path.dirname(script), '../resources/pylibs')
    else:
        repo_path = os.path.join(dst, 'pylibs')

    pip = pip_downloader.MyPip()
    results = {'ok': [], 'failed': []}
    with open(require_file) as file_content:
        for line in file_content.readlines():
            LOG.info('[{0}]'.format(line.strip()))
            if pip.download(line.strip(), repo_path):
                results['ok'].append(line.strip())
                continue
            results['failed'].append(line.strip())
    return results


def download_os_packages(os_list=None, software_list=None, dst=None):
    """
    download_os_packages
    """
    os_dep = os_dep_downloader.OsDepDownloader()
    return os_dep.download(os_list, software_list, dst)


def download_all(os_list, software_list, dst):
    """
    download all resources for specific os list
    """
    res_dir = os.path.join(dst, "resources")
    download_python_packages(res_dir)
    download_os_packages(os_list, software_list, res_dir)


def parse_argument(download_path=''):
    """
    解析参数
    """
    support_os_list = os.listdir(os.path.join(CUR_DIR, 'config'))
    if download_path.endswith('ascend-deployer'):
        support_os_list = os.listdir(os.path.join(download_path, 'downloader', 'config'))
    os_list_help = 'for example: --os-list=<OS1>,<OS2>\nSpecific OS list to download, supported os are:\n'
    for osname in sorted(support_os_list):
        os_list_help += '{}\n'.format(osname)
    download_help = 'for example: --download=<PK1>,<PK2>==<Version>\n' \
                    'Specific package list to download, supported packages are:\n'

    parser = argparse.ArgumentParser(
        epilog="  notes: When <Version> is missing, <PK> is the latest.\r\n",
        formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('--os-list', action='store', dest='os_list',
            help=os_list_help)
    parser.add_argument('--download', action='store', dest='packages',
            help=download_help)

    args = parser.parse_args()
    if args.os_list is None and args.packages is None:
        parser.print_help()
        return

    if args.os_list is not None:
        for os_item in args.os_list.split(','):
            if os_item not in support_os_list:
                print('os {} is not supported'.format(os_item))
                parser.print_help()
                sys.exit(1)
    if args.packages is not None:
        for soft in args.packages.split(','):
            if not software_mgr.is_software_support(soft):
                print('software {} is not supported'.format(soft))
                parser.print_help()
                sys.exit(1)

    return args


def get_download_path():
    """
    get download path
    """
    if 'site-packages' not in CUR_DIR and 'dist-packages' not in CUR_DIR:
        cur = os.path.dirname(FILE_PATH)
        return os.path.dirname(cur)

    deployer_home = ''
    if platform.system() == 'Linux':
        deployer_home = os.getenv('HOME')
        if os.getenv('ASCEND_DEPLOYER_HOME') is not None:
            deployer_home = os.getenv('ASCEND_DEPLOYER_HOME')
    else:
        deployer_home = os.getcwd()
    return os.path.join(deployer_home, 'ascend-deployer')


def main():
    """
    entry for console
    """
    download_path = get_download_path()
    args = parse_argument(download_path)

    if args is None:
        sys.exit(0)

    os_list = []
    if args.os_list is not None:
        os_list = args.os_list.split(',')
    software_list = []
    if args.packages is not None:
        software_list = args.packages.split(',')
    download_all(os_list, software_list, download_path)


if __name__ == "__main__":
    if len(sys.argv) == 1:
        download_python_packages()
        download_os_packages()
        sys.exit(0)
    main()
