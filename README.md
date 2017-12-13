# windows_file_util
Python modules to manage files (and file permissions) in windows environment.

### gipkofileinfo

Lists and handles file security information (owner, permissions).

### gipkofileutil

Miscelaneous windows files utilities :
- a function that creates a shortcut.
- a function that returns the default program used to open files with a given extension

### gipkouserinfo

Retrieves users and groups information from a windows server


### directory tree

Shows an indented view of the sub-directories tree of a given directory. Optionally outputs it to a text file.


### fichiers_permissions_liste

Walks a directory tree and for each subdirectory lists the access permissions.

Optionally also lists files permissions.

Outputs 2 files, one (.txt) humanly legible, and one (.csv) intended for postprocessing (with a spreadsheet for example)

### fichiers_permissions_suppression

Walks a directory tree and for each subdirectory and all files within it removes the access permissions of
the users, the list of which is given as an argument

### fichiers_permissions_par_user

Walks a directory tree and for each file and subdirectory prints the higher authorization level (R or W) granted
to the user passed as an argument. No output if use has no access.

### surveillance_espace_disque

This program is intended to be launched periodically by windows's tasks scheduler.

The ini file contains the list of disks to be monitored (local disks or network shares) with their alert thresholds.
The threshold can be a value in Gb, Tb, etc, or a percentage of free space.

The program will output its results in a log file, and if the disk occupation threshold is exceeded on any disk it will
send an alert by mail. (mailing parameters also defined in ini file).

### fichiers_permissions_redondances

Points out files and directories where a user is granted twice the same acces rights, with individual permissions and due
to his group membership.

### get_file_dates, print_file_dates and set_file_dates

Return, print and set a file's access and modification dates (ISO or timestamp)


## Dependencies
* python 3 (developed and tested with python 3.4)
* (some modules) gipkomail available [here] (https://github.com/Pepilepioux/server_stats/)


## License
This work is licensed under [Creative Commons Attribution-NonCommercial 4.0 International](https://creativecommons.org/licenses/by-nc/4.0/legalcode)

You are free to share and adapt it as long as you give appropriate credit, provide a link to the license and indicate if changes were made.

You may use it as you want as long as it is not for commercial purposes.

# Authors
* Pepilepioux
