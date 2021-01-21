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
    """
    This class spawn CLI session with extended function with logging, history,
    dangerous command options, TAB command completion, help messages.
    """
    invite_help = '''Type q or quit for exit from cli.
Type h or help for short help.
Use TAB for command completion. '''
    extended_help = '''Type q or quit for exit from cli. 
Type h or help for short help. 
Use TAB for command completion.
For start cli command by one string - "cli <command>" (don't use special shell char).
For start cli command file from bash - "cli -c <commandFile> <logFile>".
For start logging type "l+" or "l+ logfile.txt" (default logfile "cli_DATE_TIME.log"). For stop logging type l-.
For start bash cmd from cli use l, for example "l cat set.xml" )
Use bash conveyor " | " for start text processing sequence or write to file. Example:
        cmedit get * networkelement | grep MOSCOW | tee result.txt
Use "cli>" in bash conveyor for send output to next cli command. Example:
        cmedit get RNC* utranrelation=CELL* | grep FDN | awk '{print "cmedit get ",$3}' | cli> | grep loadSharing
For more info about cli command use web-help, TAB or "manual "! 
For question about cli.py contact or innightwolfsleep@yandex.ru
Extended help command:'''
    enm_session = None
    cliInputString = 'CLI> '
    conveyor_to_cli_prefix = 'cli>'
    conveyor_delimeter = '|'
    maxAutoCliCmdInBashSequence = 30
    cli_history_file_name = '~/.cliHistory'
    UserFileName = '/CLI_ENM_UserGroup.csv'
    PolicyFileName = '/CLI_ENM_UserRestrictPolicy.csv'
    UnprotectedMode = False
    extend_manual_file_name = '/CLI_ENM_help.csv'
    unsafe_log_dir = '/cli_log/'
    safe_log_dir = '/cli_safelog/'
    completerFileName = '/CLI_ENM_Completer.csv'
    completerArray = []

    def __init__(self, cli_dir):
        self.cli_history_file_name = os.path.expanduser(self.cli_history_file_name)
        self.UserFileName = cli_dir + self.UserFileName
        self.PolicyFileName = cli_dir + self.PolicyFileName
        self.extend_manual_file_name = cli_dir + self.extend_manual_file_name
        self.unsafe_log_dir = cli_dir + self.unsafe_log_dir
        self.safe_log_dir = cli_dir + self.safe_log_dir
        self.completerFileName = cli_dir + self.completerFileName
        self.completerArray = self._get_cli_completer_array()

    # open internal ENM session
    def open_int_enm_session(self):
        try:
            self.enm_session = enmscripting.open()
            return self.enm_session
        except Exception as e:
            print(e)
            return None

    # open external ENM session
    def open_ext_enm_session(self, enm_address='', login='', password=''):
        try:
            session = enmscripting.private.session.ExternalSession(enm_address)
            enm_session = enmscripting.enmsession.UnauthenticatedEnmSession(session)
            enm_session = enm_session.with_credentials(
                enmscripting.security.authenticator.UsernameAndPassword(login, password))
            self.enm_session = enm_session
            return enm_session
        except Exception as e:
            print(e)
            return None

    # This method for beginning to starts CLI shell - parse input args and go to initialize_shell
    def start(self, sys_args):
        # main, refer to infinite cli loop or execute_cmd_file
        if len(sys_args) > 1:
            if sys_args[1] == '-c' and len(sys_args) > 2:
                cmd_file_name = sys_args[2]
                if len(sys_args) > 3:
                    out_file_name = sys_args[3]
                else:
                    out_file_name = ''
                self.execute_cmd_file(cmd_file_name, out_file_name)
            else:
                self.initialize_enm_session()
                self.infinite_cli_loop(first_cmd=' '.join(sys_args[1:]), run_single_cmd=True)
        else:
            print(self.invite_help)
            self.initialize_enm_session()
            self.initialize_shell()

    # This method starts enm session if it is not exist
    def initialize_enm_session(self, enm_url='', enm_login='', enm_password=''):
        # prepare sessions and cli options
        new_enm_session = None
        if enm_url == '':
            new_enm_session = self.open_int_enm_session()
        if new_enm_session is None or type(new_enm_session) is enmscripting.enmsession.UnauthenticatedEnmSession:
            if enm_url == '':
                enm_url = raw_input('ENM URL: ')
            if enm_login == '':
                enm_login = raw_input('ENM login: ')
            if enm_password == '':
                enm_password = getpass.getpass('ENM password: ')
            new_enm_session = self.open_ext_enm_session(enm_url, enm_login, enm_password)
        if new_enm_session is None or type(new_enm_session) is enmscripting.enmsession.UnauthenticatedEnmSession:
            print('Cant open any ENM session!')
            exit()
        return new_enm_session

    # This prepare CLI shell start - start enm session and set readline options, then go to infinite_cli_loop
    def initialize_shell(self, first_cmd=''):
        # prepare sessions and cli options
        readline.parse_and_bind('tab: complete')
        readline.set_completer_delims('')
        readline.set_completer(self._cli_completer)
        readline.set_completion_display_matches_hook(self._completion_display_matches_pass)
        if not os.path.exists(self.cli_history_file_name):
            cli_history_file = open(self.cli_history_file_name, 'w')
            cli_history_file.close()
        readline.read_history_file(self.cli_history_file_name)
        readline.set_history_length(1000)
        self.infinite_cli_loop(first_cmd)

    # This is main method. This starts infinite raw_input loop, contain commands parser.
    # refer to terminal_cmd_execute running cli commands
    def infinite_cli_loop(self, first_cmd='', run_single_cmd=False):
        terminal = self.enm_session.terminal()
        file_out_name = None
        cmd_string = first_cmd
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
                response_text = self.subprocess_cmd(cmd_string[2:])
                print(response_text)
            elif cmd_string.startswith('l+'):
                if file_out_name is None:
                    if len(cmd_string.split(' ')) > 1 and len(cmd_string.split(' ')[1]):
                        file_out_name = cmd_string.split(' ')[1]
                    else:
                        file_out_name = 'cli_' + time.strftime('%Y%m%d_%H%M%S') + '.log'

                    print('logfile: ' + file_out_name)
                else:
                    print('logfile already open: ' + file_out_name)
            elif cmd_string in ['l-', 'l- ']:
                if file_out_name is not None:
                    print('logfile closed: ' + file_out_name)
                    file_out_name = None
                else:
                    print('logfile already closed')
            elif len(cmd_string) > 0:
                response_text = self.terminal_cmd_execute(terminal, cmd_string.split(self.conveyor_delimeter)[0])
                if len(cmd_string.split(self.conveyor_delimeter)) > 1 and len(response_text) > 0:
                    conveyor_cmd_list = cmd_string.split(self.conveyor_delimeter)[1:]
                    for conveyor_cmd in conveyor_cmd_list:
                        if conveyor_cmd.lstrip().startswith(self.conveyor_to_cli_prefix):
                            next_cmd_list = response_text.split('\n')
                            response_text = ''
                            cmd_length_ok = 'y'
                            if len(next_cmd_list) > self.maxAutoCliCmdInBashSequence:
                                cmd_length_ok = \
                                    raw_input('It is ' + str(len(next_cmd_list)) +
                                              ' cli commands in sequence. Too much! Are you sure? (y/n): ')
                            if cmd_length_ok == 'y' or cmd_length_ok == 'Y':
                                for next_cmd in next_cmd_list:
                                    next_cmd = next_cmd.replace('\r', '').replace('\n', '')
                                    response_text = response_text + "\n" + self.terminal_cmd_execute(terminal, next_cmd)
                            else:
                                response_text = 'Aborted by user! Too much cli command in sequence! It is ' \
                                                    + str(len(next_cmd_list)) + 'cmd!'
                        else:
                            response_text = self.subprocess_cmd(conveyor_cmd, response_text)
                print(self._utf8_chars_to_space(response_text))
                if file_out_name is not None:
                    try:
                        with open(file_out_name, 'a') as file_out:
                            file_out.write('\n' + self.cliInputString + cmd_string + '\n' + response_text)
                    except Exception as e:
                        print("Cant write logfile! Please, check file permissions! File:" + str(file_out_name), e)
            try:
                readline.write_history_file(self.cli_history_file_name)
            except Exception as e:
                print("Cant write cli history to file: " + self.cli_history_file_name, e)
            if run_single_cmd:
                break
            cmd_string = raw_input(self.cliInputString)
        return enmscripting.close(self.enm_session)

    # This method check cli command, parse and refer to terminal_cmd for running command.
    # refer to _check_cmd_permission for check permissions
    # refer to _add_cmd_to_log for save files to log
    def terminal_cmd_execute(self, terminal, cmd_string):
        response_text = ''
        response = None
        try:
            if len(cmd_string) > 0:
                cmd_permission = self._check_cmd_permission(cmd_string, os.getlogin())
                self._add_cmd_to_log(cmd_string, os.getlogin(), cmd_permission)
                if cmd_permission == 'permit':
                    if cmd_string.find('file:') > -1:
                        file_to_upload = cmd_string[cmd_string.find('file:') + 5:].split(' ')[0]
                        file_to_upload = file_to_upload.replace('"', '')
                        if cmd_string.find('file:/') > -1:
                            cmd_string = \
                                cmd_string.replace(cmd_string[cmd_string.find('/'):cmd_string.rfind('/') + 1], '')
                        if not os.path.exists(file_to_upload):
                            response_text = 'Cant find file for upload: ' + file_to_upload
                        else:
                            file_up = open(file_to_upload, 'rb')
                            cmd_string = cmd_string.replace(file_to_upload, os.path.basename(file_to_upload))
                            response = self.terminal_cmd(terminal, cmd_string, file_up)
                            response_text = '\n'.join(response.get_output())
                    else:
                        response = self.terminal_cmd(terminal, cmd_string)
                        response_text = '\n'.join(response.get_output())
                else:
                    response_text = '\n Command "' + cmd_string + '" not permitted!\n' + cmd_permission
        except Exception as e:
            print(e)
            response_text = '>>> Wrong command or expired session: ' + cmd_string
        if response is not None:
            if response.has_files():
                for enm_file in response.files():
                    enm_file.download()
                    response_text = response_text + '\nfile downloaded ' + os.getcwd() + '/' + enm_file.get_name()
        return response_text

    # dummy method for readline
    def _completion_display_matches_pass(self, substitution, matches_list, longest_match_length):
        pass

    # readline TAB help align value
    completer_space_count_before_text = 20

    # command completion method for readline
    def _cli_completer(self, text, state):
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

    # support method, get completer_array
    def _get_cli_completer_array(self):
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

    # support method, get command permissions
    def _check_cmd_permission(self, cmd_string, username):
        return_value = 'permit'
        user_group = 'default'
        if not self.UnprotectedMode:
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

    # support method, send command to logs
    def _add_cmd_to_log(self, cmd_string, username, return_value):
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
            print("Cant write log to " + self.unsafe_log_dir)
        return False

    # This method using to read command file and send command to enm terminal.
    # Commands need to pass terminal_cmd_execute permission check!
    def execute_cmd_file(self, cmd_file_name, out_file_name='', enm_url='', enm_login='', enm_password=''):
        # prepare sessions and cli options
        self.initialize_enm_session(enm_url=enm_url, enm_login=enm_login, enm_password=enm_password)
        terminal = self.enm_session.terminal()
        with open(cmd_file_name.replace(' ', ''), 'r') as file_in:
            lines = file_in.readlines()
        file_out = None
        if len(out_file_name.replace(' ', '')) > 2:
            file_out = open(out_file_name.replace(' ', ''), 'a')
        for line in lines:
            response_text = self.terminal_cmd_execute(terminal, line)
            print('\n' + self.cliInputString + line + '\n' + response_text)
            try:
                if file_out is not None:
                    file_out.write('\n' + self.cliInputString + line + '\n' + response_text)
            except Exception as e:
                print(e)
                print("Cant write log!!!")
        if file_out is not None:
            file_out.close()
        enmscripting.close(self.enm_session)

    # This method print extended manual page from extend_manual_file_name
    def print_extend_manual(self, question):
        with open(self.extend_manual_file_name, 'r') as help_file:
            help_list = help_file.read().split('@@@@@')
            help_found = False
            for help in help_list:
                if help.find('@@@@') >= 0:
                    if help.split('@@@@')[0] == question and len(help.split('@@@@')) > 1:
                        print(help.split('@@@@')[1])
                        help_found = True
                    if help.split('@@@@')[0] + ' ' == question and len(help.split('@@@@')) > 1:
                        print(help.split('@@@@')[1])
                        help_found = True
            if not help_found:
                for help in help_list:
                    if help.find('@@@@') >= 0:
                        if help.split('@@@@')[0].find(question) > -1:
                            print(" " * len(self.cliInputString) + help.split('@@@@')[0])

    # This special static method!
    # Move logfiles data from unsafe dir to safe dir!
    # Do not overwrite data in safe dir!
    # Remove old file in unsafe dir!
    # Execution may be croned with root or equal permissions to copy unprotected log to protected log dir!
    # for example:
    # */1 * * * * /usr/bin/python /home/shared/protected_user/cli_safe_log.py
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

    # encode utf to ASCII, replace undefined to " "
    @staticmethod
    def _utf8_chars_to_space(string):
        ss = ""
        for i in string:
            if ord(i) < 127:
                ss = ss + i
            else:
                ss = ss + " "
        return ss

    # execute cli terminal command and return response
    @staticmethod
    def terminal_cmd(terminal, cmd_string, opened_binary_file=None):
        if opened_binary_file is None:
            return terminal.execute(cmd_string)
        else:
            return terminal.execute(cmd_string, opened_binary_file)

    # execute shell command and return response
    @staticmethod
    def subprocess_cmd(command, insert_to_stdin=''):
        process = subprocess.Popen(command, stdout=subprocess.PIPE,
                                   stdin=subprocess.PIPE, shell=True)
        proc_stdout = process.communicate(insert_to_stdin)[0].strip()
        return proc_stdout
