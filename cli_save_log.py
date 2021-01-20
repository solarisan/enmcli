#!/usr/bin/python
#-*- coding:utf-8 -*-

from enmcli import EnmCli

unsafe_log_dir = '/home/shared/admin/cli/cli_safelog'
safe_log_dir = '/home/shared/admin/cli/cli_log'
obsolescence_days = 30
EnmCli.cli_log_copy_to_safe(unsafe_log_dir, safe_log_dir, obsolescence_days)

