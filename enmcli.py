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
    _cli_completer_text = "123456789"
    _completer_line_list = []
    _completer_list = []
    enm_session = None
    cli_input_string = 'CLI> '
    conveyor_to_cli_prefix = 'cli>'
    conveyor_delimeter = '|'
    max_conveyor_cmd_ask_user = 30
    cli_history_file_name = '~/.cliHistory'
    user_group_file_name = '/CLI_ENM_UserGroup.csv'
    restrict_policy_file_name = '/CLI_ENM_UserRestrictPolicy.csv'
    unprotected_mode = False
    extend_manual_file_name = '/CLI_ENM_help.csv'
    unsafe_log_dir = '/cli_log/'
    safe_log_dir = '/cli_safelog/'
    completer_file_name = '/CLI_ENM_Completer.csv'
    completer_space_count_before_text = 20

    def __init__(self, cli_dir):
        """
        init code, set folder with all suplimentary files (log dir, restriction files, help files...)
        :param cli_dir:
        """
        self.cli_history_file_name = os.path.expanduser(self.cli_history_file_name)
        self.user_group_file_name = cli_dir + self.user_group_file_name
        self.restrict_policy_file_name = cli_dir + self.restrict_policy_file_name
        self.extend_manual_file_name = cli_dir + self.extend_manual_file_name
        self.unsafe_log_dir = cli_dir + self.unsafe_log_dir
        self.safe_log_dir = cli_dir + self.safe_log_dir
        self.completer_file_name = cli_dir + self.completer_file_name
        self._completer_line_list = self._get_cli_completer_array()

    def start(self, sys_args, unprotected_mode=False):
        """
        This method for beginning to starts CLI shell - parse input args and go to initialize_shell
        :param sys_args:
        :param unprotected_mode:
        :return:
        """
        self.unprotected_mode = unprotected_mode
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
                if self.initialize_enm_session() is None:
                    exit()
                self._infinite_cli_loop(first_cmd=' '.join(sys_args[1:]), run_single_cmd=True)
        else:
            print(self.invite_help)
            if self.initialize_enm_session() is None:
                exit()
            self._initialize_shell_config()
            self._infinite_cli_loop()

    def initialize_enm_session(self, enm_url='', enm_login='', enm_password=''):
        """
        This method starts and return enm session. Overwrite self.enm_session if exist
        :param enm_url:
        :param enm_login:
        :param enm_password:
        :return:
        """
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
            return None
        self.enm_session = new_enm_session
        return new_enm_session

    def _initialize_shell_config(self):
        """
        This prepare CLI shell configuration - set readline methods and cli_history_file
        :return:
        """
        readline.parse_and_bind('tab: complete')
        readline.set_completer_delims('')
        readline.set_completer(self._cli_completer)
        readline.set_completion_display_matches_hook(self._completion_display_matches)
        if not os.path.exists(self.cli_history_file_name):
            cli_history_file = open(self.cli_history_file_name, 'w')
            cli_history_file.close()
        readline.read_history_file(self.cli_history_file_name)
        readline.set_history_length(1000)

    def _infinite_cli_loop(self, first_cmd='', run_single_cmd=False):
        """
        This is main shell method. This starts infinite raw_input loop, contain commands parser.
        Refer to _conveyor_cmd_executor running cli commands.
        :param first_cmd:
        :param run_single_cmd:
        :return: enm_session close status
        """
        file_out_name = None
        cmd_string = first_cmd
        # this is a loop if cmd_string not "quit"
        while cmd_string not in ['q', 'q ', 'quit', 'quit ']:
            response_text = ''
            # parse and execute cmd_string
            if cmd_string in ['h', 'h ', 'help', 'help ']:
                print(self.extended_help)
            elif cmd_string.startswith('manual') or cmd_string.startswith('help'):
                self.print_extend_manual(cmd_string)
            elif cmd_string.startswith('?'):
                print('Use TAB or "help" or "help <command>" or "manual <command>"!')
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
                    file_out_name = 'cli_' + time.strftime('%Y%m%d_%H%M%S') + '.log'
                    if len(cmd_string.split(' ')) > 1:
                        if len(cmd_string.split(' ')[1]) > 0:
                            file_out_name = cmd_string.split(' ')[1]
                    print('set logfile: ' + file_out_name)
                else:
                    print('logfile already set: ' + file_out_name)
            elif cmd_string.startswith('l-'):
                if file_out_name is not None:
                    print('logfile unset: ' + file_out_name)
                    file_out_name = None
                else:
                    print('logfile already unset')
            elif len(cmd_string) > 0:
                response_text = self._conveyor_cmd_executor(cmd_string)
                print(self._utf8_chars_to_space(response_text))
            # try to write log&history files
            try:
                if file_out_name is not None and len(response_text) > 0:
                    with open(file_out_name, 'a') as file_out:
                        file_out.write('\n' + self.cli_input_string + cmd_string + '\n' + response_text)
            except Exception as e:
                print("Cant write logfile! Please, check file permissions! File:" + str(file_out_name), e)
            try:
                readline.write_history_file(self.cli_history_file_name)
            except Exception as e:
                print("Cant write cli history to file: " + self.cli_history_file_name, e)
            if run_single_cmd:
                break
            # start input for next iteration
            cmd_string = raw_input(self.cli_input_string)
        return enmscripting.close(self.enm_session)

    def _conveyor_cmd_executor(self, cmd_string):
        """
        This is conveyor, split cmd_string to cmd list, if it is needed,
        then run cmd one-by-one, and send previous response to next cmd
        :param cmd_string:
        :return response_text
        """
        response_text = self.enm_execute(cmd_string.split(self.conveyor_delimeter)[0])
        # if there are conveyor delimeter in cmd_string and first command execution done, start conveyor
        if len(cmd_string.split(self.conveyor_delimeter)) > 1 and len(response_text) > 0:
            conveyor_cmd_list = cmd_string.split(self.conveyor_delimeter)[1:]
            for conveyor_cmd in conveyor_cmd_list:
                if conveyor_cmd.lstrip().startswith(self.conveyor_to_cli_prefix):
                    next_cmd_list = response_text.split('\n')
                    response_text = ''
                    cmd_length_ok = 'y'
                    if len(next_cmd_list) > self.max_conveyor_cmd_ask_user:
                        cmd_length_ok = \
                            raw_input('It is ' + str(len(next_cmd_list)) +
                                      ' cli commands in sequence. Too much! Are you sure? (y/n): ')
                    if cmd_length_ok == 'y' or cmd_length_ok == 'Y':
                        for next_cmd in next_cmd_list:
                            next_cmd = next_cmd.replace('\r', '').replace('\n', '')
                            response_text = \
                                response_text + "\n" + self.enm_execute(next_cmd)
                    else:
                        response_text = 'Aborted by user! Too much cli command in sequence! It is ' \
                                        + str(len(next_cmd_list)) + 'cmd!'
                else:
                    response_text = self.subprocess_cmd(conveyor_cmd, response_text)
        return response_text

    def enm_execute(self, cmd_string):
        """
        This method check cli command, parse and refer to terminal_execute for running command.
        refer to _check_cmd_permission for check permissions
        refer to _add_cmd_to_log for save files to log
        """
        terminal = self.enm_session.terminal()
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
                            response = terminal.execute(cmd_string, file_up)
                            response_text = '\n'.join(response.get_output())
                    else:
                        response = terminal.execute(cmd_string)
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

    def _check_cmd_permission(self, cmd_string, username):
        """
        support method, get command permissions
        :param cmd_string:
        :param username:
        :return:
        """
        return_value = 'permit'
        user_group = 'default'
        if not self.unprotected_mode:
            try:
                if os.path.exists(self.user_group_file_name):
                    with open(self.user_group_file_name, 'r') as user_file:
                        for line in user_file:
                            if line.split(';')[0] == username:
                                user_group = line.split(';')[1].replace('\n', '').replace('\r', '')
                else:
                    return_value = 'cant find UserFile'
                if os.path.exists(self.restrict_policy_file_name):
                    with open(self.restrict_policy_file_name, 'r') as policy_file:
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

    def _add_cmd_to_log(self, cmd_string, username, return_value):
        """
        support method, send command to logs
        :param cmd_string:
        :param username:
        :param return_value:
        :return:
        """
        if not os.path.exists(self.unsafe_log_dir):
            os.mkdir(self.unsafe_log_dir)
        try:
            if os.path.isdir(self.unsafe_log_dir):
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

    def execute_cmd_file(self, cmd_file_name, out_file_name='', enm_url='', enm_login='', enm_password=''):
        """
        This method using to read command file and send command to enm terminal.
        Commands need to pass enm_execute permission check!
        :param cmd_file_name:
        :param out_file_name:
        :param enm_url:
        :param enm_login:
        :param enm_password:
        :return:
        """
        # prepare sessions and cli options
        self.initialize_enm_session(enm_url=enm_url, enm_login=enm_login, enm_password=enm_password)
        with open(cmd_file_name.replace(' ', ''), 'r') as file_in:
            lines = file_in.readlines()
        file_out = None
        if len(out_file_name.replace(' ', '')) > 2:
            file_out = open(out_file_name.replace(' ', ''), 'a')
        for line in lines:
            response_text = self.enm_execute(line)
            print('\n' + self.cli_input_string + line + '\n' + response_text)
            try:
                if file_out is not None:
                    file_out.write('\n' + self.cli_input_string + line + '\n' + response_text)
            except Exception as e:
                print(e)
                print("Cant write log!!!")
        if file_out is not None:
            file_out.close()
        enmscripting.close(self.enm_session)

    def _completion_display_matches(self, substitution, matches_list, longest_match_length):
        """
        dummy method for readline, for future use
        :param substitution:
        :param matches_list:
        :param longest_match_length:
        :return:
        """
        pass

    def _cli_completer(self, text, state):
        """
        command completion method for readline
        :param text:
        :param state:
        :return:
        """
        try:
            word_n = len(text.split(' '))
            cmedit_get_flag = False
            if state == 0 and text != self._cli_completer_text:
                if text.startswith("cmedit get "):
                    cmedit_get_flag = True
                    fdn = text[11:]
                    new_completer_list = map(lambda x: "cmedit get " + x, self.get_fdn_childs_list(fdn))
                    if new_completer_list:
                        self._completer_list = new_completer_list
                    else:
                        for i in self._completer_list:
                            if i.find(text) == 0:
                                new_completer_list.append(i)
                        if new_completer_list:
                            self._completer_list = new_completer_list
                    self._completer_list.sort()
                elif word_n == 0:
                    self._completer_list = []
                    for line in self._completer_line_list:
                        if len(line.split('@')[0].split(' ')) == 1:
                            self._completer_list.append(line)
                elif word_n > 0:
                    self._completer_list = []
                    for line in self._completer_line_list:
                        if len(line.split('@')[0].split(' ')) == word_n \
                                and line.startswith(text) \
                                and not line.startswith('@'):
                            self._completer_list.append(line)
                self._cli_completer_text = text
            out_line = self._completer_list[state].replace('@', ' ' * (self.completer_space_count_before_text -
                                                                      len(self._completer_list[state].split('@')[0])))
            out_line = out_line.replace('\n', '').replace('\r', '')
            out_line = ' ' * len(self.cli_input_string) + out_line
            sys.stdout.write('\n' + out_line)
            sys.stdout.flush()
            if state == len(self._completer_list) - 1:
                sys.stdout.write('\n' + self.cli_input_string + readline.get_line_buffer(), )
                sys.stdout.flush()
            if cmedit_get_flag:
                return self._completer_list[state].split('@')[0].replace('\n', '')
            else:
                return self._completer_list[state].split('@')[0].replace('\n', '') + ' '
        except Exception:
            return None

    def _get_cli_completer_array(self):
        """
        support method, get completer_array
        :return:
        """
        try:
            if os.path.exists(self.completer_file_name):
                completer_array = []
                with open(self.completer_file_name, 'r') as completer_file:
                    for line in completer_file:
                        completer_array.append(line)
                return completer_array
            else:
                return [None]
        except Exception as e:
            print(e)
            return [None]

    def get_fdn_childs_list(self, fdn):
        """
        """
        try:
            fdn = fdn[:-1] + fdn[-1:].replace(",","")
            terminal = self.enm_session.terminal()
            # prepare ne_name
            if len(fdn) < 1 or "SubNetwor".startswith(fdn):
                return ["SubNetwork"]
            if fdn.find("MeContext=") > -1:
                ne_name = fdn.split("MeContext=")[-1].split(",")[0]
            elif fdn.startswith("NetworkElement="):
                ne_name = fdn.split('NetworkElement=')[-1]
            else:
                ne_name = "*"
            if ne_name == "":
                ne_name = "*"
            # check direct FDN
            response = terminal.execute("cmedit get " + fdn)
            # prepare cmd
            if response.get_output()[-1] == "1 instance(s)":
                mo_type = fdn.split(',')[-1].split('=')[0]
                mo_name = fdn.split(',')[-1].split('=')[-1]
                cmd = "cmedit get " + ne_name + " " + mo_type + "." + mo_type + "Id==" + mo_name + ",*"
            elif "," in fdn:
                parent_mo_type = fdn.split(',')[-2].split('=')[0]
                cmd = "cmedit get " + ne_name + " " + parent_mo_type + ",*"
            if fdn == "SubNetwork":
                cmd = "cmedit get * SubNetwork"
            if fdn.split(",")[-1].startswith("SubNetwork="):
                mo_name = fdn.split('SubNetwork=')[-1]
                cmd = "cmedit get * SubNetwork.SubNetworkId==" + mo_name + ",*"
            # get fdn list
            fdn_list = []
            response = terminal.execute(cmd)
            for line in response.get_output():
                if line.startswith("FDN : "):
                    line_fdn = line.split("FDN : ")[-1]
                    if fdn != line_fdn and line_fdn.find(fdn) == 0:
                        fdn_list.append(line.split(" ")[2])
            return fdn_list
        except Exception as e:
            print("get_fdn_childs_list", e)
            return None
            
    def print_extend_manual(self, question):
        """
        This method print extended manual page from extend_manual_file_name
        :param question:
        :return:
        """
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
                            print(" " * len(self.cli_input_string) + help.split('@@@@')[0])

    @staticmethod
    def cli_log_copy_to_safe(unsafe_log_dir, safe_log_dir, obsolescence_days):
        """
        This special static method!
        Move logfiles data from unsafe dir to safe dir!
        Do not overwrite data in safe dir!
        Remove old file in unsafe dir!
        Execution may be croned with root or equal permissions to copy unprotected log to protected log dir!
        for example:
        */1 * * * * /usr/bin/python /home/shared/protected_user/cli_safe_log.py
        :param unsafe_log_dir:
        :param safe_log_dir:
        :param obsolescence_days:
        :return:
        """
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
    def _utf8_chars_to_space(string):
        """
        encode utf to ASCII, replace undefined to " "
        :param string:
        :return:
        """
        ss = ""
        for i in string:
            if ord(i) < 127:
                ss = ss + i
            else:
                ss = ss + " "
        return ss

    @staticmethod
    def open_int_enm_session():
        """
        open and return internal ENM session
        :return:
        """
        try:
            enm_session = enmscripting.open()
            return enm_session
        except Exception as e:
            print(e)
            return None

    @staticmethod
    def open_ext_enm_session(enm_address='', login='', password=''):
        """
        open and return external ENM session
        :param enm_address:
        :param login:
        :param password:
        :return:
        """
        try:
            session = enmscripting.private.session.ExternalSession(enm_address)
            enm_session = enmscripting.enmsession.UnauthenticatedEnmSession(session)
            enm_session = enm_session.with_credentials(
                enmscripting.security.authenticator.UsernameAndPassword(login, password))
            return enm_session
        except Exception as e:
            print(e)
            return None

    @staticmethod
    def subprocess_cmd(command, insert_to_stdin=''):
        """
        execute shell command and return response
        :param command:
        :param insert_to_stdin:
        :return:
        """
        process = subprocess.Popen(command, stdout=subprocess.PIPE,
                                   stdin=subprocess.PIPE, shell=True)
        proc_stdout = process.communicate(insert_to_stdin)[0].strip()
        return proc_stdout
