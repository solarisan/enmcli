# enm_cli
Ericsson Network Management CLI for terminal (for example, when you use direct ssh connect to ENM).
Simple way to start - copy enmcli/ to you own directory and run cli_start.py.


____________________________________________________

CLI_ENM_Completer.csv - This file contains command completer for cli terminal

CLI_ENM_help.csv - This file contains help manual pages for command

CLI_ENM_UserGroup.csv - This file contains usernames and their group. If username not in file, user group is "default" 

CLI_ENM_UserRestrictPolicy.csv - This file contains groupname ; message-when-restrict-appears ; regular expression of restricted command. Also, message-when-restrict "permit" will permit command.

cli_save_log.py - aditional utility, will move user logs from unsafe log dirrectory to safe directory. May be croned for each minute.

cli_start.py - contain start shell code.

enmcli.py - contains main code
