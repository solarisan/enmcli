#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
cli - module for using enmscripting terminal cli without web-based cli. Allow to use unix cmd via | statement.
It defines classes_and_methods
@author:....Ilya Shevchenko
@contact:    inightwolfsleep@yandex.ru
"""

import enmscripting
import sys
import os
import readline
import re
import subprocess
import getpass
import time


class EnmCli(object):
    invite_help = '''Type q or quit for exit from cli.
Type h or help for short help.
Use TAB for command completion. '''
    extended_help = '''Type q or quit for exit from cli. 
Type h or help for short help. 
Use TAB for command completion.
For start cli command by one string - "cli <command>" (dont use special shell char).
For start cli command file from bash - "cli -c <commandFile> <logFile>".
For start logging type "l+" or "l+ logfile.txt" (default logfile "cli_DATE_TIME.log"). For stop logging type l-.
For start bash cmd from cli use l, for example "l cat set.xml" )
Use bash conveer " | " for start text processing sequence or write to file. Example:
        cmedit get * networkelement | grep TY | grep BL | tee result.txt
Use "cli>" in bash conveer for send output to next cli command. Example:
        cmedit get RNCE* utranrelation=TU4881_* | grep FDN | awk '{print "cmedit get ",$3}' | cli> | grep loadSharing
For more info about cli command use web-help, TAB or "manual "! 
For question about cli.py contact or innightwolfsleep@yandex.ru
Extended help command:'''
    session = None
    cliInputString = 'CLI> '
    maxAutoCliCmdInBashSequence = 100

    def __init__(self, cli_dir):
        super(EnmCli, self).__init__()
        self.cli_history_file_name = os.path.expanduser('~/.cliHistory')
        self.UserFileName = cli_dir + '/CLI_ENM_UserGroup.csv'
        self.PolicyFileName = cli_dir + '/CLI_ENM_UserRestrictPolicy.csv'
        self.extend_manual_file_name = cli_dir + '/CLI_ENM_help.csv'
        self.completerFileName = cli_dir + '/CLI_ENM_Completer.csv'
        self.completerArray = self.get_cli_completer_array()
        self.unsafe_log_dir = cli_dir + '/cli_log/'
        self.safe_log_dir = cli_dir + '/cli_safelog/'

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
            print(self.invite_help)
            self.infinite_cli_loop()

    def open_int_enm_session(self):
        try:
            self.session = enmscripting.open()
        except Exception as e:
            print(e)

    def open_ext_enm_session(self, enm_address='', login='', password=''):
        try:
            self.session = enmscripting.private.session._open_external_session(enm_address, login, password)
        except Exception as e:
            print(e)

    def infinite_cli_loop(self, single_cmd=''):
        # prepare sessions and cli options
        if self.session is None:
            self.open_int_enm_session()
        if self.session is None:
            self.open_ext_enm_session(raw_input('ENM URL: '), raw_input('login: '), getpass.getpass('password: '))
        if self.session is None:
            print('Cant open any ENM session!')
            exit()
        terminal = self.session.terminal()
        readline.parse_and_bind('tab: complete')
        readline.set_completer_delims('')
        readline.set_completer(self.cli_completer)
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
                print(self.extended_help)
            elif cmd_string.startswith('manual') or cmd_string.startswith('help'):
                self.print_extend_manual(cmd_string)
            elif cmd_string.startswith('?'):
                print('Use TAB or "help" or "manual"!')
            elif cmd_string.startswith('execute file:'):
                try:
                    self.execute_cmd_file(cmd_string[13:])
                except Exception as e:
                    print("Error while open file! Check path! Check restrict ' ' symbols!", e)
            elif cmd_string.startswith('l '):
                response_cli_text = self.subprocess_cmd(cmd_string[2:])
                print(response_cli_text)
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
                    print('logfile already closed')
            elif len(cmd_string) > 0:
                response_cli_text = self.terminal_cmd_execute(terminal, cmd_string.split(' | ')[0])
                if len(cmd_string.split(' | ')) > 1 and len(response_cli_text) > 0:
                    conveer_cmd_list = cmd_string.split(' | ')[1:]
                    for conveer_cmd in conveer_cmd_list:
                        if conveer_cmd.find('cli>') > -1:
                            next_cli_comandlist = response_cli_text.split('\n')
                            response_cli_text = ''
                            cmdnumcheck = 'y'
                            if len(next_cli_comandlist) > self.maxAutoCliCmdInBashSequence:
                                cmdnumcheck = raw_input('It is ' + str(len(next_cli_comandlist))
                                                        + ' cli commands in sequence. Too much! Are you sure? (y/n) ')
                            if cmdnumcheck == 'y':
                                for next_cmd in next_cli_comandlist:
                                    next_cmd = next_cmd.replace('\r', '').replace('\n', '')
                                    next_response = self.terminal_cmd_execute(terminal, next_cmd)
                                    response_cli_text = response_cli_text + '\n' + next_response
                            else:
                                response_cli_text = 'Aborted by user! Too much cli command in sequence! It is ' \
                                                    + str(len(next_cli_comandlist)) + 'cmd!'
                        else:
                            response_cli_text = self.subprocess_cmd(conveer_cmd, response_cli_text)
                self.chars_restricted_print(response_cli_text)
                if file_out is not None:
                    try:
                        file_out.write('\n' + self.cliInputString + cmd_string + '\n' + response_cli_text)
                        file_out.flush()
                    except Exception as e:
                        print("Cant write logfile! Please, check file permissions! File:" + str(file_out.name), e)
            try:
                readline.write_history_file(self.cli_history_file_name)
            except Exception as e:
                print("Cant write cli history to file: " + self.cli_history_file_name, e)
            if len(single_cmd) > 0:
                break
            cmd_string = raw_input(self.cliInputString)
        return enmscripting.close(self.session)

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
                        if not os.path.exists(file_to_upload):
                            response_cli_text = 'Cant find file for upload: ' + file_to_upload
                        else:
                            file_up = open(file_to_upload, 'rb')
                            cmd_string = cmd_string.replace(file_to_upload, os.path.basename(file_to_upload))
                            response = self.terminal_cmd(terminal, cmd_string, file_up)
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
        except Exception as e:
            print(e)
            response_cli_text = '>>> Wrong command or expired session: ' + cmd_string
        return response_cli_text

    def completion_display_matches_pass(self, substitution, matches_list, longest_match_length):
        pass

    completer_space_count_before_text = 20

    def cli_completer(self, text, state):
        word_n = len(text.split(' '))
        completer_list = []
        if state == 0 and word_n == 0:
            for line in self.completerArray:
                if len(line.split('@')[0].split(' ')) == 1:
                    completer_list.append(line)
        if state == 0 and word_n > 0:
            for line in self.completerArray:
                if len(line.split('@')[0].split(' ')) == word_n and line.startswith(text) and not line.startswith('@'):
                    completer_list.append(line)
        for line in completer_list:
            out_line = line.replace('@', ' ' * (self.completer_space_count_before_text - len(line.split('@')[0])))
            out_line = out_line.replace('\n', '').replace('\r', '')
            out_line = ' ' * len(self.cliInputString) + out_line
            sys.stdout.write('\n' + out_line)
            sys.stdout.flush()
        sys.stdout.write('\n' + self.cliInputString + readline.get_line_buffer(), )
        sys.stdout.flush()
        if len(completer_list) > 1:
            return None
        else:
            return completer_list[0].split('@')[0].replace('\n', '') + ' '

    def get_cli_completer_array(self):
        try:
            if os.path.exists(self.completerFileName):
                completer_array = []
                with open(self.completerFileName, 'r') as completer_file:
                    for line in completer_file:
                        completer_array.append(line)
                return completer_array
            else:
                return [None]
        except Exception as e:
            print(e)
            return [None]

    def check_cmd_permission(self, cmd_string, username):
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
        except Exception as e:
            print(e)
            return_value = \
                'cli.py script error during check permission!'
        return return_value

    def add_cmd_to_log(self, cmd_string, username, return_value):
        try:
            log_filename = self.unsafe_log_dir + 'ssh_cli_' + time.strftime('%Y%m%d') + '.log'
            with open(log_filename, 'a') as log_file:
                log_file.write(
                    '\n' + time.strftime('%Y%m%d_%H%M%S') + ';' + username + ';' + return_value + ';' + cmd_string)
            try:
                os.chmod(log_filename, 0666)
            except Exception as e:
                print(e)
                return True
            return True
        except Exception as e:
            print(e)
            print("Cant write log!!!")
        return False

    def execute_cmd_file(self, cmd_file_name, out_file_name=''):
        session = enmscripting.open()
        terminal = session.terminal()
        with open(cmd_file_name.replace(' ', ''), 'r') as file_in:
            lines = file_in.readlines()
        file_out = None
        if len(out_file_name.replace(' ', '')) > 2:
            file_out = open(out_file_name.replace(' ', ''), 'a')
        for line in lines:
            response_cli_text = self.terminal_cmd_execute(terminal, line)
            print('\n' + self.cliInputString + line + '\n' + response_cli_text)
            try:
                if file_out is not None:
                    file_out.write('\n' + self.cliInputString + line + '\n' + response_cli_text)
            except Exception as e:
                print(e)
                print("Cant write log!!!")
        if file_out is not None:
            file_out.close()
        enmscripting.close(session)

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
            for file_name in os.listdir(unsafe_log_dir):
                if obsolescence_days < 1:
                    obsolescence_days = 360
                if os.path.getmtime(unsafe_log_dir + file_name) + int(obsolescence_days) * 3600 * 24 < time.time():
                    os.remove(unsafe_log_dir + file_name)
                else:
                    if os.path.getsize(unsafe_log_dir + file_name) > 0:
                        with open(unsafe_log_dir + file_name, 'a+') as log_file:
                            with open(safe_log_dir + file_name, 'a') as safelog_file:
                                log_file.seek(0)
                                safelog_file.write(log_file.read())
                                log_file.truncate(0)
            return True
        except Exception as e:
            print(e)
            return False

    @staticmethod
    def chars_restricted_print(string):
        ss = ""
        for i in string:
            if ord(i) < 127:
                ss = ss + i
            else:
                ss = ss + " "
        print(ss)

    @staticmethod
    def terminal_cmd(terminal, cmd_string, opened_binary_file=None):
        if opened_binary_file is None:
            return terminal.execute(cmd_string)
        else:
            return terminal.execute(cmd_string, opened_binary_file)

    @staticmethod
    def subprocess_cmd(command, insert_to_stdin=''):
        process = subprocess.Popen(command, stdout=subprocess.PIPE,
                                   stdin=subprocess.PIPE, shell=True)
        proc_stdout = process.communicate(insert_to_stdin)[0].strip()
        return proc_stdout
