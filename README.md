# enm_cli
Allow ti use Ericsson Network Management Command Line Interface via terminal (for example, ssh terminal via putty).

May open internal enm session (when using directly on ENM scripting VM) or external enm session (when using on any Linux system)/

Simple way to start using - copy enmcli/ to you $HOME directory on ENM scripting VM and run cli_start.py.


____________________________________________________
CLI_ENM_* files - additional completers, manuals and user restrction rules.

CLI_ENM_Completer.csv - This file contains command completer for cli terminal

CLI_ENM_help.csv - This file contains help manual pages for command

CLI_ENM_UserGroup.csv - This file contains usernames and their group. If username not in file, user group is "default" 

CLI_ENM_UserRestrictPolicy.csv - This file contains groupname ; message-when-restrict-appears ; regular expression of restricted command. Also, message-when-restrict "permit" will permit command.

cli_save_log.py - aditional utility, will move user logs from unsafe log dirrectory to safe directory. May be croned for each minute.

cli_start.py - contain start shell code.

enmcli.py - contains main code
