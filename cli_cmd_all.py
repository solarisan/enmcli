#!/usr/bin/python
# -*- coding:utf-8 -*-

from enmcli import EnmCli
import sys
from threading import Thread

cli_files_folder = '/home/bsscp/python/scripts/Ericsson/cli/enm_cli'
enmlist =[
"https://enm1.enm.com/",
"https://enm2.enm.com/",
"https://enm3.enm.com/",
"https://enm4.enm.com/",
]
cmd=' '.join(sys.argv[1:])
login = raw_input('ENM login: ')
password = raw_input('ENM password: ')


def run_cmd_om_enmcli(enm):
    e = EnmCli(cli_files_folder)
    e.initialize_enm_session(enm, login, password)
    print e.enm_execute(cmd)


if __name__ == '__main__':
    for enm in enmlist:
        Thread(target=run_cmd_om_enmcli, args=(str(enm),)).start()
