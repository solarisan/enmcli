#!/usr/bin/python
# -*- coding:utf-8 -*-

from enmcli import EnmCli
import sys
import os

cli_files_folder = os.path.expanduser('~/enm_cli')
EnmCli(cli_files_folder).start(sys.argv)
