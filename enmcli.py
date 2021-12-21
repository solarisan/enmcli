#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
enmcli - give access to Ericsson Network Manager Command Line Interface (cli)
from terminal shell on any other system (unix, windows...)
enmcli have extended ability for logging, restrict policy, linux conveying, mo-tree-navigating, pinging, built-in...
Notice:
This module use library "enmscripting" - property of Ericsson, so it isn't included here.
But if you have access to Ericsson Network Manager - obviously, you have access to this library)
Just copy enmscripting to enmcli folder.
Also, if you install enmcli on ENM scripting VM - you will able to use it without additional actions.
@author:    Ilya Shevchenko
@contact:   inightwolfsleep@yandex.ru
"""

import enmscripting  # enmscripting is a Ericsson property library
import sys
import os
import time
from requests import session, packages
from subprocess import Popen, PIPE
from getpass import getpass
from json import loads as j_loads
from socket import gethostbyname
from re import search, IGNORECASE
import readline  # use pyreadline on Windows system


class EnmCli(object):
    """
    This class spawn CLI session with extended function with logging, history,
    dangerous command options, TAB command completion, help messages.
    """
    invite_help = 'Type q or quit for exit from cli.' \
                  '\nType h or help for short help.' \
                  '\nUse TAB for command completion. '
    extended_help = 'Type q or quit for exit from cli.' \
                    '\nType h or help for short help.' \
                    '\nUse TAB for command completion.' \
                    '\nFor start cli command by one string - "cli <command>".' \
                    '\nFor start cli command file from bash - "cli -c <commandFile> <logFile>".' \
                    '\nFor start logging type "l+" or "l+ logfile.txt" (default logfile "cli_DATE_TIME.log").' \
                    '\nFor start bash cmd from cli use l, for example "l cat set.xml" )' \
                    '\nUse bash conveyor " | " for start text processing sequence or write to file. Example:' \
                    '\n        cmedit get * NetworkElement | grep MOSCOW | tee result.txt' \
                    '\nUse \"cli>\" in bash conveyor for send output to next cli command. Example:' \
                    '\n        cmedit get R* UtranRelation=C* | grep FDN | awk \'{print \"cmedit get \",$3}\' | cli>' \
                    '\nFor more info about cli command use web-help, TAB or "manual "!' \
                    '\nFor question about cli.py contact or innightwolfsleep@yandex.ru' \
                    '\nExtended help command:'
    _cli_completer_text = "_DEFAULT_TEXT_"
    __last_completer_list = []
    # sessions obj
    enm_session = None  # session from enmscripting module
    rest_session = None  # simple http enm session
    url = None  # ENM URL
    login = None
    password = None
    # syntax options and mode
    unprotected_mode = False  # on/off use permission restrict policy
    cli_input_string = 'CLI> '  # input string
    conveyor_delimiter = '|'  # when u send cmd with | - string fall into bash-like conveyor
    conveyor_to_cli_cmd = 'cli>'  # when to_cli_cmd find in conveyor - result send to ENM cli, not bash
    max_conveyor_cmd_ask_user = 30  # determines, when to stop too long command list
    completer_lead_space_num = 20  # TAB completer visual delimiter
    # internal files path
    cli_history_file_name = '~/.cliHistory'  # user history file
    user_group_file_name = '/CLI_ENM_UserGroup.csv'
    restrict_policy_file_name = '/CLI_ENM_UserRestrictPolicy.csv'
    extend_manual_file_name = '/CLI_ENM_help.csv'
    unsafe_log_dir = '/cli_log/'  # more one user history file, usually used for centralized logging
    safe_log_dir = '/cli_safelog/'  # used in cli_log_copy_to_safe
    completer_file_name = '/CLI_ENM_Completer.csv'
    _completer_line_list = ['help@simple help message (also "h").',
                            'manual@manual for command. "manual" will print list of available manual page',
                            'quit@if you want to rest (also "q")',
                            'l@execute bash cmd from cli, example "l cat set.xml" or "l ls"',
                            'l+@start logging, use as  "l+" or "l+ logfile.txt"',
                            'l-@stop logging',
                            'ping@ping NetworkElement by name: "ping MOSCOW001" or "ping BSC* -i 0.2 -c 2 -s 1500"',
                            'get@topology browser cli, use <TAB> for navigate topology']

    def __init__(self, cli_dir=""):
        """
        initial code, set folder with all supplementary files (log dir, restriction files, help files...)
        :param cli_dir:
        """
        # init other internal params
        self.cli_history_file_name = os.path.expanduser(self.cli_history_file_name)
        self.user_group_file_name = cli_dir + self.user_group_file_name
        self.restrict_policy_file_name = cli_dir + self.restrict_policy_file_name
        self.extend_manual_file_name = cli_dir + self.extend_manual_file_name
        self.unsafe_log_dir = cli_dir + self.unsafe_log_dir
        self.safe_log_dir = cli_dir + self.safe_log_dir
        self.completer_file_name = cli_dir + self.completer_file_name
        self._completer_line_list = self._extend_cli_completer_list(self._completer_line_list)

    def start(self, *args):
        """
        This method for beginning to starts CLI shell - parse input args and go to initialize_shell
        :param sys_args:
        :return:
        """
        # main, refer to infinite cli loop or execute_cmd_file
        if self.initialize_enm_session() is None:
            print("Cant start ENM session!")
            exit()
        if len(args) == 1:
            print(self.invite_help)
            self._initialize_shell_config()
            self._infinite_cli_loop()
        if len(args) == 2:
            self._infinite_cli_loop(cmd=' '.join(sys_args[1:]), run_single_cmd=True)
        if len(args) > 2 and args[1] == '-c':
            cmd_file_name = args[2]
            out_file_name = ''
            if len(args) == 4:
                out_file_name = args[3]
            self.execute_cmd_file(cmd_file_name, out_file_name)

    def initialize_enm_session(self):
        """
        This method starts and return enm session. Overwrite self.enm_session if exist
        :return: enm session
        """
        # prepare sessions and cli options
        new_enm_session = self._initialize_internal_enm_session()
        if new_enm_session is None or type(new_enm_session) is enmscripting.enmsession.UnauthenticatedEnmSession:
            self._ask_enm_url_login_password()
            new_enm_session = self._initialize_external_enm_session()
        if new_enm_session is None or type(new_enm_session) is enmscripting.enmsession.UnauthenticatedEnmSession:
            print('Cant open any ENM session!')
            return None
        self.rest_session = self.get_rest_session(url=self.url, login=self.login, password=self.password)
        self.enm_session = new_enm_session
        return new_enm_session

    def _initialize_internal_enm_session(self):
        try:
            new_enm_session = enmscripting.open()
            if self.url is None:
                self.url = self.get_internal_enm_url()
            return new_enm_session
        except Exception as e:
            print("Cant open internal enm session", e)
            return None

    def _ask_enm_url_login_password(self, ask_new=False):
        if self.url is None or ask_new:
            self.url = raw_input('ENM URL: ')
        if self.login is None or ask_new:
            self.login = raw_input('ENM login: ')
        if self.password is None or ask_new:
            self.password = getpass('ENM password: ')

    def _initialize_external_enm_session(self):
        try:
            s = enmscripting.private.session.ExternalSession(self.url)
            new_enm_session = enmscripting.enmsession.UnauthenticatedEnmSession(s)
            new_enm_session = new_enm_session.with_credentials(
                enmscripting.security.authenticator.UsernameAndPassword(self.login, self.password))
            return new_enm_session
        except Exception as e:
            print("Cant open external enm session", e)
            return None

    def _initialize_shell_config(self):
        """
        This prepare CLI shell configuration - set readline methods and cli_history_file
        :return:
        """
        readline.parse_and_bind('tab: complete')
        readline.set_completer_delims('')
        readline.set_completer(self._cli_completer)
        if "set_completion_display_matches_hook" in dir(readline):
            readline.set_completion_display_matches_hook(self._completion_display_matches)
        else:
            readline.rl.mode.show_all_if_ambiguous = "off"
            readline.rl.bell_style = "audible"
        if not os.path.exists(self.cli_history_file_name):
            cli_history_file = open(self.cli_history_file_name, 'w')
            cli_history_file.close()
        readline.read_history_file(self.cli_history_file_name)
        readline.set_history_length(1000)

    def _infinite_cli_loop(self, cmd='', run_single_cmd=False):
        """
        This is main shell method. This starts infinite raw_input loop, contain commands parser.
        Refer to _conveyor_cmd_executor running cli commands.
        :param first_cmd:
        :param run_single_cmd:
        :return: enm_session close status
        """
        file_out_name = None
        # this is a loop if cmd_string not "quit"
        while cmd not in ['q', 'q ', 'quit', 'quit ']:
            response_text = ''
            cmd = cmd.lstrip()
            # parse and execute cmd_string
            if cmd.startswith("get "):
                try:
                    response = self.topology_browser_get_data(self.rest_session, self.url, cmd[len("get "):])
                    print(str(self.json_parsing(response, 1, "   ")))
                except KeyboardInterrupt:
                    print("\nInterrupted with Ctrl^C.")
            elif cmd in ['h', 'h ', 'help', 'help ']:
                print(self.extended_help)
            elif cmd.startswith('ping '):
                self.ping_ne(cmd)
            elif cmd.startswith('manual') or cmd.startswith('help'):
                self.print_extend_manual(cmd)
            elif cmd.startswith('?'):
                print('Use TAB or "help" or "help <command>" or "manual <command>"!')
            elif cmd.startswith('execute file:'):
                try:
                    self.execute_cmd_file(cmd[13:])
                except KeyboardInterrupt:
                    print("\nInterrupted with Ctrl^C.")
                except Exception as e:
                    print("Error while open file! Check path! Check restrict ' ' symbols!", e)
            elif cmd.startswith('l '):
                response_text = self.subprocess_cmd(cmd[2:])
                print(response_text)
            elif cmd.startswith('l+'):
                if file_out_name is None:
                    file_out_name = 'cli_' + time.strftime('%Y%m%d_%H%M%S') + '.log'
                    if len(cmd.split(' ')) > 1:
                        if len(cmd.split(' ')[1]) > 0:
                            file_out_name = cmd.split(' ')[1]
                    print('set logfile: ' + file_out_name)
                else:
                    print('logfile already set: ' + file_out_name)
            elif cmd.startswith('l-'):
                if file_out_name is not None:
                    print('logfile unset: ' + file_out_name)
                    file_out_name = None
                else:
                    print('logfile already unset')
            elif len(cmd) > 0:
                try:
                    response_text = self._conveyor_cmd_executor(cmd)
                    print(self._utf8_chars_to_space(response_text))
                except KeyboardInterrupt:
                    print("\nInterrupted with Ctrl^C.")
                except Exception as e:
                    print(e)
                    break
            # try to write log&history files
            try:
                if file_out_name is not None and len(response_text) > 0:
                    with open(file_out_name, 'a') as file_out:
                        file_out.write('\n' + self.cli_input_string + cmd + '\n' + response_text)
            except Exception as e:
                print("Cant write logfile! Please, check file permissions! File:" + str(file_out_name), e)
            try:
                readline.write_history_file(self.cli_history_file_name)
            except Exception as e:
                print("Cant write cli history to file: " + self.cli_history_file_name, e)
            if run_single_cmd:
                break
            # start input for next iteration
            try:
                cmd = raw_input(self.cli_input_string)
            except KeyboardInterrupt:
                print "\nExit CLI with Ctrl^C. Bye!"
                break
        return enmscripting.close(self.enm_session)

    def _conveyor_cmd_executor(self, cmd_string):
        """
        This is conveyor, split cmd_string to cmd list, if it is needed,
        then run cmd one-by-one, and send previous response to next cmd
        :param cmd_string:
        :return response_text
        """
        response_text = self.enm_execute(cmd_string.split(self.conveyor_delimiter)[0])
        # if there are conveyor delimiter in cmd_string and first command execution done, start conveyor
        if len(cmd_string.split(self.conveyor_delimiter)) > 1 and len(response_text) > 0:
            conveyor_cmd_list = cmd_string.split(self.conveyor_delimiter)[1:]
            for conveyor_cmd in conveyor_cmd_list:
                if conveyor_cmd.lstrip().startswith(self.conveyor_to_cli_cmd):
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
        response_text = ''
        response = None
        try:
            if len(cmd_string) > 0:
                user_login = os.getlogin() if self.login is None else self.login
                cmd_permission = self._check_cmd_permission(cmd_string, user_login)
                self._add_cmd_to_log(cmd_string, user_login, cmd_permission)
                if cmd_permission == 'permit':
                    if cmd_string.find('file:') > -1:
                        file_to_upload = cmd_string[cmd_string.find('file:') + 5:].split('\n')[0].split(' ')[0]
                        file_to_upload = file_to_upload.replace('"', '')
                        if cmd_string.find('file:/') > -1:
                            cmd_string = \
                                cmd_string.replace(cmd_string[cmd_string.find('/'):cmd_string.rfind('/') + 1], '')
                        if not os.path.exists(file_to_upload):
                            response_text = 'Cant find file for upload: ' + file_to_upload
                        else:
                            file_up = open(file_to_upload, 'rb')
                            cmd_string = cmd_string.replace(file_to_upload, os.path.basename(file_to_upload))
                            response = self.enm_session.terminal().execute(cmd_string, file_up)
                            response_text = '\n'.join(response.get_output())
                    else:
                        response = self.enm_session.terminal().execute(cmd_string)
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
                                if search(line.split(';')[2].replace('\n', '').replace('\r', ''), cmd_string,
                                          IGNORECASE) is not None:
                                    return_value = line.split(';')[1].replace('USERNAME', username)
                else:
                    return_value = 'cant find PolicyFile ' + self.restrict_policy_file_name
            except Exception as e:
                print(e)
                return_value = \
                    'cli.py script error during check permission!'
        return return_value

    def _add_cmd_to_log(self, cmd_string, username, return_value):
        """
        support method, send command to logs
        """
        try:
            if not os.path.exists(self.unsafe_log_dir):
                os.mkdir(self.unsafe_log_dir)
            if os.path.isdir(self.unsafe_log_dir):
                log_filename = self.unsafe_log_dir + 'ssh_cli_' + time.strftime('%Y%m%d') + '.log'
                with open(log_filename, 'a') as log_file:
                    log_file.write(
                        '\n' + time.strftime('%Y%m%d_%H%M%S') + ';' + username + ';' + return_value + ';' + cmd_string)
                try:
                    os.chmod(log_filename, 0o0666)
                except Exception as e:
                    return e
                return True
        except Exception as e:
            print(e)
            print("Cant write log to " + self.unsafe_log_dir)
        return False

    def execute_cmd_file(self, cmd_file_name, out_file_name=''):
        """
        This method using to read command file and send command to enm terminal.
        Commands need to pass enm_execute permission check!
        """
        # prepare sessions and cli options
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
        pass

    def _cli_completer(self, text, state):
        """
        command completion method for readline
        """
        try:
            word_n = len(text.split(' '))
            cmedit_get_flag = False
            if state == 0 and text != self._cli_completer_text:
                if text.startswith("get "):
                    cmedit_get_flag = True
                    fdn = text[len("get "):]
                    new_completer_list = map(lambda x: "get " + x,
                                             self.topology_browser_get_child(self.rest_session, self.url, fdn))
                    if new_completer_list:
                        self.__last_completer_list = new_completer_list
                    else:
                        for i in self.__last_completer_list:
                            if i.find(text) == 0:
                                new_completer_list.append(i)
                        if new_completer_list:
                            self.__last_completer_list = new_completer_list
                elif word_n == 0:
                    self.__last_completer_list = []
                    for line in self._completer_line_list:
                        if len(line.split('@')[0].split(' ')) == 1:
                            self.__last_completer_list.append(line)
                elif word_n > 0:
                    self.__last_completer_list = []
                    for line in self._completer_line_list:
                        if len(line.split('@')[0].split(' ')) == word_n \
                                and line.startswith(text) \
                                and not line.startswith('@'):
                            self.__last_completer_list.append(line)
                self._cli_completer_text = text
            out_line = self.__last_completer_list[state].replace('@', ' ' * (self.completer_lead_space_num -
                                                                             len(self.__last_completer_list[
                                                                                     state].split('@')[0])))
            out_line = out_line.replace('\n', '').replace('\r', '')
            out_line = ' ' * len(self.cli_input_string) + out_line
            sys.stdout.write('\n' + str(out_line))
            sys.stdout.flush()
            if state == len(self.__last_completer_list) - 1:
                sys.stdout.write('\n' + self.cli_input_string + readline.get_line_buffer(), )
                sys.stdout.flush()
            if cmedit_get_flag:
                return self.__last_completer_list[state].split('@')[0].replace('\n', '')
            else:
                return self.__last_completer_list[state].split('@')[0].replace('\n', '') + ' '
        except IndexError:
            return None

    def _extend_cli_completer_list(self, old_list=None):
        """
        support method, get completer_array
        """
        try:
            new_list = []
            if type(old_list) is not list:
                old_list = []
            if os.path.exists(self.completer_file_name):
                with open(self.completer_file_name, 'r') as f:
                    old_list.extend(f.readlines())
            for x in old_list:
                if x.replace('\n', '').replace('\r', '') not in new_list:
                    new_list.append(x.replace('\n', '').replace('\r', ''))
            return new_list
        except Exception as e:
            print(e)
            return [None]

    @staticmethod
    def get_internal_enm_url():
        with session() as s:
            ha_url = ''.join(('https://', gethostbyname('haproxy')))
            redirected_url = s.get(ha_url, verify=False).url
            parsed_url = redirected_url.split("?goto=")[-1]
            return str(parsed_url)

    @staticmethod
    def get_rest_session(url=None, login=None, password=None):
        packages.urllib3.disable_warnings()
        if url is None or login is None or password is None:
            s = session()
            packages.urllib3.disable_warnings()
            cookie_path = os.path.join(os.path.expanduser("~"), '.enm_login')
            with open(cookie_path, 'r') as cookie:
                token = cookie.readline().strip()
            s.cookies['iPlanetDirectoryPro'] = token
            return s
        else:
            s = session()
            resp = s.post(url + '/login?IDToken1=' + login + '&' + 'IDToken2=' + password, verify=False)
            if resp.status_code == 200:
                return s
            else:
                return None

    @staticmethod
    def topology_browser_get_child(s, url="", fdn=""):
        try:
            fdn_temp = fdn
            mo_list = []
            if fdn == '':
                resp = s.get(url + u"/persistentObject/network/-1?relativeDepth=0:-2", verify=False)
                if resp.status_code != 200:
                    return None
                mo_raw = j_loads(resp.content)["treeNodes"]
            else:
                resp = s.get(url + u"/persistentObject/fdn/" + str(fdn_temp), verify=False)
                if resp.status_code != 200:
                    fdn_temp = ",".join(fdn_temp.split(",")[:-1])
                    resp = s.get(url + u"/persistentObject/fdn/" + str(fdn_temp), verify=False)
                if resp.status_code == 200:
                    resp = s.get(url + u"/persistentObject/fdn/" + str(fdn_temp), verify=False)
                    poid = str(j_loads(resp.content)["poId"])
                    resp = s.get(url + u"/persistentObject/network/" + str(poid), verify=False)
                    mo_raw = j_loads(resp.content)["treeNodes"][0]["childrens"]
                    fdn_temp = fdn_temp + ","
                else:
                    return None
            for i in mo_raw:
                fdn_new = fdn_temp + i["moType"] + "=" + i["moName"]
                if fdn_new.startswith(fdn):
                    mo_list.append(fdn_new)
                mo_list.sort()
            return mo_list
        except Exception as e:
            print("topology_browser_get_child", e)
            return None

    @staticmethod
    def topology_browser_get_data(s, url="", fdn=""):
        try:
            if fdn[-1] == ",":
                fdn = fdn[:-1]
            resp = s.get(url + u"/persistentObject/fdn/" + str(fdn), verify=False)
            if resp.status_code == 404:
                return j_loads(resp.content)
            elif resp.status_code != 200:
                return ["Wrong credentials or session expired!"]
            else:
                return j_loads(resp.content)
        except Exception as e:
            print("topology_browser_get_data", e)
            return None

    def ping_ne(self, cmd):
        result = []
        try:
            if len(cmd.split(" ")) > 1:
                ne = cmd.split(" ")[1]
            else:
                return "no NE name"
            ping_args = ["-c", "4"]
            if len(cmd.split(" ")) > 2:
                ping_args.extend(cmd.split(" ")[2:])
            mos = "BscConnectivityInformation.ipaddress;CbpOiConnectivityInformation.ipaddress;" \
                  "ComConnectivityInformation.ipaddress;" \
                  "CppConnectivityInformation.ipaddress;EceeConnectivityInformation.ipaddress" \
                  ";EciConnectivityInformation.ipaddress;EosConnectivityInformation.ipaddress" \
                  ";Er6000ConnectivityInformation.ipaddress;EsaConnectivityInformation.ipaddress" \
                  ";EscConnectivityInformation.ipaddress;ExosConnectivityInformation.ipaddress" \
                  ";FrontHaul6000ConnectivityInformation.ipaddress;FrontHaul6080ConnectivityInformation.ipaddress" \
                  ";GenericFmNodeConnectivityInformation.ipaddress;GenericSnmpNodeConnectivityInformation.ipaddress" \
                  ";HdsConnectivityInformation.ipaddress;HlrFeConnectivityInformation.ipaddress" \
                  ";HttpConnectivityInformation.ipaddress;IposOiConnectivityInformation.ipaddress" \
                  ";IsConnectivityInformation.ipaddress;MINILINKIndoorConnectivityInformation.ipaddress" \
                  ";MINILINKOutdoorConnectivityInformation.ipaddress;MscConnectivityInformation.ipaddress" \
                  ";R8800ConnectivityInformation.ipaddress;SSRConnectivityInformation.ipaddress" \
                  ";STNConnectivityInformation.ipaddress;TspConnectivityInformation.ipaddress;" \
                  "VREConnectivityInformation" \
                  ".ipaddress "
            search_cmd = 'cmedit get ' + ne + ' ' + mos + ' -t -s'
            try:
                response = self.enm_session.terminal().execute(search_cmd)
            except Exception as e:
                print("enm session error! May be session is expired?\n", e)
                return False
            for s in response.get_output():
                if len(s.split("\t")) == 4:
                    node_id, sync_status, connectivity_info, ip_address = s.split("\t")
                    if search(r"\d*\.\d*\.\d*\.\d*", ip_address) is not None:
                        print(node_id)
                        try:
                            cmd = 'ping ' + ip_address + " " + " ".join(ping_args)
                            process = Popen(cmd, stderr=PIPE, shell=True)
                            result.append({node_id: process.communicate('')})
                        except Exception as e:
                            print(e)
        except KeyboardInterrupt:
            print("ping stopped by user")
        return result

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
        ss = ""
        for i in string:
            if ord(i) < 127:
                ss = ss + i
            else:
                ss = ss + " "
        return ss

    @staticmethod
    def json_parsing(json_obj, lvl, w_space=" ", delimiter=" : "):
        txt = ""
        if isinstance(json_obj, dict):
            if "key" in json_obj and "value" in json_obj:
                if isinstance(json_obj["value"], dict):
                    txt = txt + "\n" + w_space * lvl + json_obj["key"] + delimiter
                    txt = txt + "\n" + EnmCli.json_parsing(json_obj["value"], lvl + 1, w_space)
                elif isinstance(json_obj["value"], list):
                    txt = txt + "\n" + w_space * lvl + json_obj["key"] + delimiter
                    txt = txt + "\n" + EnmCli.json_parsing(json_obj["value"], lvl + 1, w_space)
                else:
                    txt = txt + "\n" + str(w_space * lvl) + json_obj["key"] + delimiter + str(
                        json_obj["value"])
            else:
                for i in json_obj:
                    if isinstance(json_obj[i], dict):
                        txt = txt + "\n" + w_space * lvl + i + delimiter
                        txt = txt + "\n" + EnmCli.json_parsing(json_obj[i], lvl + 1, w_space)
                    elif isinstance(json_obj[i], list):
                        txt = txt + "\n" + w_space * lvl + i + delimiter
                        txt = txt + "\n" + EnmCli.json_parsing(json_obj[i], lvl + 1, w_space)
                    else:
                        if i != "datatype":
                            txt = txt + "\n" + str(w_space * lvl) + i + delimiter + str(json_obj[i])
        if isinstance(json_obj, list):
            for i in json_obj:
                if isinstance(i, dict):
                    txt = txt + "\n" + EnmCli.json_parsing(i, lvl + 1, w_space)
                elif isinstance(i, list):
                    txt = txt + "\n" + EnmCli.json_parsing(i, lvl + 1, w_space)
                else:
                    txt = txt + "\n" + str(w_space * lvl) + str(i)
        return txt.replace("\n\n", "\n")

    @staticmethod
    def subprocess_cmd(command, insert_to_stdin=''):
        """
        execute shell command and return response
        """
        process = Popen(command, stdout=PIPE, stdin=PIPE, shell=True)
        proc_stdout = process.communicate(insert_to_stdin)[0].strip()
        return proc_stdout


if __name__ == '__main__':
    e = EnmCli()
    e.unprotected_mode = True
    e.start(sys.argv)
