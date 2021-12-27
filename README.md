# enm_cli
Allows to use Ericsson Network Management Command Line Interface via shell (for example, ssh terminal via putty).

May open internal enm session (when runnig directly on ENM scripting VM) or external enm session (when running on any other system, need import enmscripting module from ENM)

Easy way to start it:

    $ python enmcli.py
  
____________________________________________________

For work you need just one file:

- enmcli.py - it's contains main code and may by runed alone


Next is additional scripts with logging, comand restrictions and ruming on multiply systems:

- cli_start.py - contain improved start shell code (with logging, command restriction and other).
  python cli_start.py

- cli_save_log.py - aditional utility, will move user logs from unsafe log dirrectory to safe directory. May be croned for each minute.

- cli_cmd_all.py - utility will run single cli command from arguments on several external ENM (list inside .py code)


Next is additional .csv files - provides additional completers, manuals and user restrictions rules:

- CLI_ENM_Completer.csv - This file contains <TAB> command completer for cli, may extended by user

- CLI_ENM_help.csv - This file contains help manual pages for command

- CLI_ENM_UserGroup.csv - This file contains usernames and their group. If username not in file, user group is "default" 

- CLI_ENM_UserRestrictPolicy.csv - This file contains groupname ; message-when-restrict-appears ; regular expression of restricted command. Also, message-when-restrict "permit" will permit command.


____________________________________________________

    $ python enmcli.py
    CLI> help
    Type q or quit for exit from cli.
    Type h or help for short help.
    Use TAB for command completion.
    For start cli command by one string - "cli <command>"
    For start cli command file from bash - "cli -c <commandFile> <logFile>".
    For start logging type "l+" or "l+ logfile.txt" (default logfile "cli_DATE_TIME.log").
    For start bash cmd from cli use l, for example "l cat set.xml" )
    Use bash conveyor " | " for start text processing sequence or write to file. Example:
     cmedit get * NetworkElement | grep MOSCOW | tee result.txt
    Use "cli>" in bash conveyor for send output to next cli command. Example:
     cmedit get R* UtranRelation=C* | grep FDN | awk '{print "cmedit get ",$3}' | cli>
    For more info about cli command use web-help, TAB or "manual "!
    For question about cli.py contact or innightwolfsleep@yandex.ru
  
