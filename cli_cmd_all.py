#!/usr/bin/python
# -*- coding:utf-8 -*-

from enmcli import EnmCli
import sys
from threading import Thread
from getpass import getpass

cli_files_folder = '/home/USER/enm_cli'
enmlist =[
"https://enm1.enm.com/",
"https://enm2.enm.com/",
"https://enm3.enm.com/",
"https://enm4.enm.com/",
]


def run_cmd_om_enmcli(enm):
    e = EnmCli(cli_files_folder)
    e.initialize_enm_session(enm, login, password)
    print("\n\n" + str(enm) + "\n" + str(cmd) + "\n" + str(e.enm_execute(cmd)))


if __name__ == '__main__':
    if len(sys.argv) > 1:
        cmd=' '.join(sys.argv[1:])
        login = raw_input('ENM login: ')
        password = getpass('ENM password: ')
        for enm in enmlist:
            Thread(target=run_cmd_om_enmcli, args=(str(enm),)).start()
    else:
        print('There is no command in args!')
