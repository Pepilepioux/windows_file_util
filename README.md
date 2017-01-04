# windows_file_util
Python modules to manage files (and file permissions) in windows environment.

### fichiers_permissions_liste

Will walk a directory tree and for each subdirectory lists the access permissions.

Optionally also lists files permissions.

Outputs 2 files, one (.txt) humanly legible, and one (.csv) intended for postprocessing (with a spreadsheet for example)

### fichiers_permissions_suppression

Will walk a directory tree and for each subdirectory and all files within it remove the access permissions of
the uses, the list of which is given as an argument

### surveillance_espace_disque

This program is intended to be launched periodically by windows's tasks scheduler.

The ini file contains the list of disks to be monitored (local disks or network shares) with their alert thresholds.
The threshold can be a value in Gb, Tb, etc, or a percentage of free space.

The program will output its results in a log file, and if the disk occupation threshold is exceeded on any disk it will
send an alert by mail. (mailing parameters also defined in ini file).

## License
This work is licensed under [Creative Commons Attribution-NonCommercial 4.0 International](https://creativecommons.org/licenses/by-nc/4.0/legalcode)

You are free to share and adapt it as long as you give appropriate credit, provide a link to the license and indicate if changes were made.

You may use it as you want as long as it is not for commercial purposes.

# Authors
* Pepilepioux
