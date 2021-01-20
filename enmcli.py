#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
cli - module for using enmscripting terminal cli without web-based cli. Allow to use unix cmd via | statement.
It defines classes_and_methods
@author:....Ilya Shevchenko
@contact:    Ilya.Shevchenko@tele2.ru / inightwolfsleep@yandex.ru
"""

import enmscripting
import sys
import os
import readline
import re
import subprocess
import getpass
import time
from socket import gethostname


class EnmCli(object):
    def __init__(self, cli_dir):
        super(EnmCli, self).__init__()
        self.cli_history_file_name = os.path.expanduser('~/.cliHistory')
        self.UserFileName = cli_dir + '/CLI_ENM_UserGroup.csv'
        self.PolicyFileName = cli_dir + '/CLI_ENM_UserRestrictPolicy.csv'
        self.extend_manual_file_name = cli_dir + '/CLI_ENM_help.csv'
        self.completerFileName = cli_dir + '/CLI_ENM_Completer.csv'
        self.completerArray = self.get_CLIcompleter_array(self.completerFileName)
        self.unsafe_log_dir = cli_dir + '/cli_log/'
        self.safe_log_dir = cli_dir + '/cli_safelog/'
        self.session = None
        self.cliInputString = 'CLI> '
        self.maxAutoCliCmdInBashSequence = 100

    def start(self, sys_args):
        # main, reffer to infinite cli loop or execute_cmd_file
        if len(sys_args) > 1:
            if sys_args[1] == '-c' and len(sys_args) > 2:
                cmd_file_name = sys_args[2]
                if len(sys_args) > 3:
                    out_file_name = sys_args[3]
                else:
                    out_file_name = ''
                self.execute_cmd_file(cmd_file_name, out_file_name)
            else:
                self.infinite_cli_loop(' '.join(sys_args[1:]))
        else:
            print('''Type q or quit for exit from cli.
    Type h or help for short help.
    Use TAB for command completion. ''')
            self.infinite_cli_loop()

    def open_enm_scripting_session(self, enm_address='', login='', password=''):
        # open EnmScriptingSession (internal or external)
        self.session = None
        if enm_address == '':
            try:
                session = enmscripting.private.session._open_internal_session()
                return session
            except:
                print("\nCan't open internal session, try external " + enm_address)
        if enm_address == '':
            enm_address = raw_input('ENM URL: ')
        if login == '':
            login = os.getlogin()
        if password == '':
            password = getpass.getpass(login + ' ENM password: ')
        try:
            self.session = enmscripting.private.session._open_external_session(enm_address, login, password)
        except:
            print('Error while open session! Check login/pass!')

    def infinite_cli_loop(self, single_cmd=''):
        self.open_enm_scripting_session()
        terminal = self.session.terminal()
        readline.parse_and_bind('tab: complete')
        readline.set_completer_delims('')
        readline.set_completer(self.CLIcompleter)
        readline.set_completion_display_matches_hook(self.completion_display_matches_pass)
        if not os.path.exists(self.cli_history_file_name):
            cli_history_file = open(self.cli_history_file_name, 'w')
            cli_history_file.close()
        readline.read_history_file(self.cli_history_file_name)
        readline.set_history_length(1000)
        file_out = None
        cmd_string = single_cmd

        # infinite while-input loop
        while cmd_string not in ['q', 'q ', 'quit', 'quit ']:
            if cmd_string in ['h', 'h ', 'help', 'help ']:
                self.print_short_help()
            elif cmd_string.startswith('manual') or cmd_string.startswith('help'):
                self.print_extend_manual(cmd_string)
            elif cmd_string.startswith('?'):
                print('Use TAB or "help" or "manual"!')
            elif cmd_string.startswith('execute file:'):
                try:
                    self.execute_cmd_file(cmd_string[13:])
                except:
                    print("Error while open file! Check path! Check restrict ' ' symbols!")
            if cmd_string.startswith('l '):
                response_cli_text = self.subprocess_cmd(cmd_string[2:])
            elif cmd_string.startswith('l+'):
                if file_out is None:
                    if len(cmd_string.split(' ')) > 1 and len(cmd_string.split(' ')[1]):
                        file_out = open(cmd_string.split(' ')[1], 'a')
                    else:
                        file_out = \
                            open('cli_' + time.strftime('%Y%m%d_%H%M%S') + '.log', 'a')
                    print('opened logfile: ' + file_out.name)
                else:
                    print('logfile already open: ' + file_out.name)
            elif cmd_string in ['l-', 'l- ']:
                if file_out is not None:
                    file_out.close()
                    print('logfile closed: ' + file_out.name)
                    file_out = None
                else:
                    print 'logfile already closed'
            else:
                response_cli_text = self.terminal_cmd_execute(terminal, cmd_string.split(' | ')[0])
                if len(cmd_string.split(' | ')) > 1 and len(response_cli_text) > 0:
                    conveer_cmd_list = cmd_string.split(' | ')[1:]
                    for conveer_cmd in conveer_cmd_list:
                        if conveer_cmd.find('cli>') > -1:
                            next_cli_comandlist = response_cli_text.split('\n')
                            response_cli_text = ''
                            cmdnumcheck = 'y'
                            if len(next_cli_comandlist) \
                                    > self.maxAutoCliCmdInBashSequence:
                                cmdnumcheck = raw_input('It is ' + str(len(next_cli_comandlist))
                                                        + ' cli commands in sequence. Too much! Are you sure? (y/n) ')
                            if cmdnumcheck == 'y':
                                for next_cmd in next_cli_comandlist:
                                    response_cli_text = response_cli_text + '\n' \
                                                        + self.terminal_cmd_execute(terminal,
                                                                                    next_cmd.replace('\r', '').replace(
                                                                                        '\n', ''))
                            else:
                                response_cli_text = 'Aborted by user! Too much cli command in sequence! It is ' \
                                                    + str(len(next_cli_comandlist)) + 'cmd!'
                        else:
                            response_cli_text = self.subprocess_cmd(conveer_cmd,
                                                                    response_cli_text)
                self.formatted_print(response_cli_text)
                if file_out != None:
                    try:
                        file_out.write('\n' + self.cliInputString + cmd_string + '\n' + response_cli_text)
                        file_out.flush()
                    except:
                        print("Cant write logfile! Please, check file permissions! File:" + str(file_out.name))
            try:
                readline.write_history_file(self.cli_history_file_name)
            except:
                print("Cant write cli history to file: " + self.cli_history_file_name)
            if len(single_cmd) > 0:
                break
            cmd_string = raw_input(self.cliInputString)
        return enmscripting.close(self.session)

    def formatted_print(self, s):
        ss = ""
        for i in s:
            if ord(i) < 127:
                ss = ss + i
            else:
                ss = ss + " "
        print(ss)

    def terminal_cmd_execute(self, terminal, cmd_string):
        response_cli_text = ''
        try:
            if len(cmd_string) > 0:
                cmd_permission = self.check_cmd_permission(cmd_string, os.getlogin())
                self.add_cmd_to_log(cmd_string, os.getlogin(), cmd_permission)
                if cmd_permission == 'permit':
                    if cmd_string.find('file:') > -1:
                        file_to_upload = cmd_string[cmd_string.find('file:') + 5:].split(' ')[0]
                        file_to_upload = file_to_upload.replace('"', '')
                        if cmd_string.find('file:/') > -1:
                            cmd_string = \
                                cmd_string.replace(cmd_string[cmd_string.find('/'):cmd_string.rfind('/') + 1], '')
                        if os.path.exists(file_to_upload) == False:
                            response_cli_text = 'Cant find file for upload: ' + file_to_upload
                        else:
                            fileUp = open(file_to_upload, 'rb')
                            response = self.terminal_cmd(terminal,
                                                        cmd_string.replace(file_to_upload,
                                                                           os.path.basename(file_to_upload)), fileUp)
                            response_cli_text = '\n'.join(response.get_output())
                            if response.has_files():
                                for enm_file in response.files():
                                    enm_file.download()
                                    response_cli_text = response_cli_text + '\nfile downloaded to ' \
                                                        + os.getcwd() + '/' + enm_file.get_name()
                    else:
                        response = self.terminal_cmd(terminal, cmd_string)
                        response_cli_text = '\n'.join(response.get_output())
                        if response.has_files():
                            for enm_file in response.files():
                                enm_file.download()
                                response_cli_text = response_cli_text + '\nfile downloaded to ' \
                                                    + os.getcwd() + '/' + enm_file.get_name()
                else:
                    response_cli_text = '\n Command "' + cmd_string + '" not permitted!\n' + cmd_permission
        except:
            response_cli_text = '>>> Wrong command or expired session: ' + cmd_string
        return response_cli_text

    @staticmethod
    def terminal_cmd(terminal, cmd_string, openedBinaryFile=None):
        if openedBinaryFile is None:
            return terminal.execute(cmd_string)
        else:
            return terminal.execute(cmd_string, openedBinaryFile)

    @staticmethod
    def subprocess_cmd(command, insertToStdin=''):
        process = subprocess.Popen(command, stdout=subprocess.PIPE,
                                   stdin=subprocess.PIPE, shell=True)
        proc_stdout = process.communicate(insertToStdin)[0].strip()
        return proc_stdout

    def completion_display_matches_pass(self, substitution, matches_list, longest_match_length):
        pass

    def CLIcompleter(self, text, state):
        word_n_help_space_count = 18
        word_count = len(text.split(' '))
        completer_list = []
        if word_count == 0:
            word_count = 1
            completer_list = [line.replace('\n', '').replace('\r', '')
                              for line in self.completerArray
                              if len(line.split('@')[0].replace('\n', '').split(' ')) == word_count
                              and line.startswith(text)
                              and not line.startswith('@')]
        if state == 0 and len(completer_list) != 0:
            print('')
        if len(completer_list[state].split('@')[0]) < word_n_help_space_count:
            print(' ' * len(self.cliInputString) +
                  completer_list[state].replace('@', ' ' * (word_n_help_space_count -
                                                            len(completer_list[state].split('@')[0]))))
        else:
            print(' ' * len(self.cliInputString) + completer_list[state].replace('@', ' '))
        if state == len(completer_list) - 1:
            print self.cliInputString + readline.get_line_buffer(),
        if len(completer_list) == 0:
            print self.cliInputString + readline.get_line_buffer(),
        return completer_list[state].split('@')[0].replace('\n', '') + ' '

    def get_CLIcompleter_array(self, completerFileName):
        try:
            if os.path.exists(completerFileName) == True:
                completerArray = []
                completerFile = open(completerFileName, 'r')
                for line in completerFile:
                    completerArray.append(line)
                completerFile.close()
                return completerArray
            else:
                return [None]
        except:
            return [None]

    def check_cmd_permission(self, cmd_string, username ):
        return_value = 'permit'
        user_group = 'default'
        try:
            if os.path.exists(self.UserFileName):
                with open(self.UserFileName, 'r') as user_file:
                    for line in user_file:
                        if line.split(';')[0] == username:
                            user_group = line.split(';')[1].replace('\n', '').replace('\r', '')
            else:
                return_value = 'cant find UserFile'
            if os.path.exists(self.PolicyFileName):
                with open(self.PolicyFileName, 'r') as policy_file:
                    for line in policy_file:
                        if line.split(';')[0] == user_group:
                            if re.search(line.split(';')[2].replace('\n', '').replace('\r', ''), cmd_string,
                                         re.IGNORECASE) is not None:
                                return_value = line.split(';')[1].replace('USERNAME', username)
            else:
                return_value = 'cant find PolicyFile'
        except:
            return_value = \
                'cli.py script error during check permission!'
        return return_value

    def add_cmd_to_log(self, cmd_string, username, return_value):
        try:
            log_filename = self.unsafe_log_dir + 'ssh_cli_' + time.strftime('%Y%m%d') + '.log'
            with open(log_filename, 'a') as CLI_ENM_log_file:
                log_filename.write('\n' + time.strftime('%Y%m%d_%H%M%S') + ';'
                                       + username + ';' + return_value + ';' + cmd_string)
            try:
                os.chmod(log_filename, 0666)
            except:
                return True
            return True
        except:
            print("Cant write log1!!!")
            return False

    def execute_cmd_file(self, cmd_file_name, out_file_name=''):
        session = enmscripting.open()
        terminal = session.terminal()
        fileIn = open(cmd_file_name.replace(' ', ''), 'r')
        lines = fileIn.readlines()
        fileIn.close()
        file_out = None
        if len(out_file_name.replace(' ', '')) > 2:
            file_out = open(out_file_name.replace(' ', ''), 'a')
        for line in lines:
            response_cli_text = self.terminal_cmd_execute(terminal, line)
            print '\n' + self.cliInputString + line + '\n' + response_cli_text
            try:
                if file_out != None:
                    file_out.write('\n' + self.cliInputString + line + '\n' + response_cli_text)
            except:
                print("Cant write log!!!")
        if file_out != None:
            file_out.close()
        enmscripting.close(session)

    def print_short_help(self):
        print '''Type q or quit for exit from cli. 
    Type h or help for short help. 
    Use TAB for command completion.
    For start cli command by one string - "cli <command>" (dont use special shell char).
    For start cli command file from bash - "cli -c <commandFile> <logFile>".
    For start logging type "l+" or "l+ logfile.txt" (default logfile "cli_DATE_TIME.log"). For stop logging type l-.
    For start bash cmd from cli use l, for example "l cat set.xml" )
    Use bash conveer " | " for start text processing sequence or write to file. Example:
            cmedit get * networkelement | grep TY | grep BL | tee result.txt
    Use "cli>" in bash conveer for send output to next cli command. Example:
            cmedit get RNCE* utranrelation=TU4881_* | grep FDN | awk '{print "cmedit get ",$3}' | cli> | grep loadSharingCandidate
    For more info about cli command use web-help, TAB or "manual "! For question about cli.py contact Ilya.Shevchenko@tele2.ru
    Extended help command:'''

    def print_extend_manual(self, quest):
        with open(self.extend_manual_file_name, 'r') as help_file:
            help_list = help_file.read().split('@@@@@')
            help_finded = False
            for help in help_list:
                if help.find('@@@@') >= 0:
                    if help.split('@@@@')[0] == quest and len(help.split('@@@@')) > 1:
                        print(help.split('@@@@')[1])
                        help_finded = True
                    if help.split('@@@@')[0] + ' ' == quest and len(help.split('@@@@')) > 1:
                        print(help.split('@@@@')[1])
                        help_finded = True
            if not help_finded:
                for help in help_list:
                    if help.find('@@@@') >= 0:
                        if help.split('@@@@')[0].find(quest) > -1:
                            print(" " * len(self.cliInputString) + help.split('@@@@')[0])

    @staticmethod
    def cli_log_copy_to_safe(unsafe_log_dir, safe_log_dir, obsolescence_days):
        try:
            for file in os.listdir(unsafe_log_dir):
                if obsolescence_days < 1:
                    obsolescence_days = 360
                if os.path.getmtime(unsafe_log_dir + file) + int(obsolescence_days) * 3600 * 24 < time.time():
                    os.remove(unsafe_log_dir + file)
                else:
                    if os.path.getsize(unsafe_log_dir + file) > 0:
                        log_file = open(unsafe_log_dir + file, 'a+')
                        safelog_file = open(safe_log_dir + file, 'a')
                        log_file.seek(0, 0)
                        safelog_file.write(log_file.read())
                        log_file.truncate(0)
                        log_file.close()
                        safelog_file.close()
            return True
        except:
            return False
