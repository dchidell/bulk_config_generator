# bulk_config_generator
Generates bulk configuration for Cisco configurations

# Description:
This script will take an excel file along with any number of template configuration files and generate a single bulk configuration file which can be manually or automatically (via SSH) loaded into a box.

# Important Notes:
An example file is included in this project, there are a few key components:

1) Excel top row is cosmetic. Use this to give a human readable name to your columns
2) Excel second row is the variable names used in the template file. E.g. a field called 'vlan' will be referred to in the template as '{vlan}'.
3) All subsequent excel rows should contain data.
4) If a field is in the spreadsheet but not referred to in the template - this is fine. It's just ignored
5) If a field is in the template but doesn't exist in the spreadsheet an error will be raised. Either remove the entry in the template or populate the spreadsheet correctly.
6) Multiple templates can be generated simultaneously, if SSH is used these templates will ALL be applied. If generating a configuration & and undo configuration do not use SSH! The configuration will be applied then immediately removed! Run two instances, or do not use SSH.

# Usage:
```
dchidell@dchidell-mac:bulk config generator$ python3 config_generator.py  -h
usage: config_generator.py [-h] [--push-config] [-i ipaddr] [-p portnumber]
                           [-u username] [-pw password] [-t device_type]
                           [-s sheetname] [-o filename] [-f]
                           spreadsheet.xlsx template.txt [template.txt ...]

Processes an excel file and uses excel entries to substitute configuration
templates.

positional arguments:
  spreadsheet.xlsx      This is the excel file containing the data we wish to
                        parse
  template.txt          This is the template file to use. As many template
                        files as you like can be used.

optional arguments:
  -h, --help            show this help message and exit
  --push-config         If this option is set we will attempt to push config
                        to a specified switch
  -i ipaddr, --ip-address ipaddr
                        This is the IP / hostname of the switch you want to
                        push the config to.
  -p portnumber, --port portnumber
                        The SSH port number.
  -u username, --username username
                        The SSH username.
  -pw password, --password password
                        The SSH password.
  -t device_type, --device-type device_type
                        The type of device. Choices: cisco_ios, cisco_nxos,
                        cisco_xr, cisco_asa, cisco_xe, cisco_tp, cisco_s300
  -s sheetname, --sheet sheetname
                        Sets the sheet name to use (defaults to active sheet
                        if not specified)
  -o filename, --once filename
                        Reads the specified file and runs the commands once
                        only for each SSH session. (Only applicable when using
                        SSH to a box)
  -f, --feedback        Displays the result of pushing commands to a router.

Written by David Chidell (dchidell@cisco.com)
```
