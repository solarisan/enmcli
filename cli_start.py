#!/usr/bin/python
# -*- coding:utf-8 -*-

from enmcli import EnmCli
import sys

cli_files_folder = '/home/shared/unprotected_user/enm_cli'
EnmCli(cli_files_folder).start(sys.argv)
