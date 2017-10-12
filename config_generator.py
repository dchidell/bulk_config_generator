#!/usr/bin/python3
# Author: David Chidell (dchidell)

#################################
# This script uses an excel template file in conjunction to .txt based configuration templates to produce bulk config.
#################################
# The following is performed as a result of this script:
# * Excel file read to obtain data relating to the configuration of network devices
# * Variables from excel file are combined with a template configuration file containing keywords
# * This script currently generates the configuration and outputs to a single text file
# * Optional functionality to push the generated configuration to a Cisco box.
##################################
# Usage: 'python3 config_generator.py [-h] [--push-config] [-i ipaddr] [-p portnumber] [-u username]
#               [-pw password] [-t device_type] [-s sheetname] [-f]
#               spreadsheet.xlsx template.txt [template.txt ...]'
##################################
# Requirements:
# * 'openpyxl', 'argparse' and 'netmiko' python packages
# * File read & write access to the current directory
##################################
# Notes:
# !WARNING!: If generating configuration + undo configuration:
#   Do NOT attempt to push to SSH if using both templates simultaneously, it will add the config then instantly undo it!
#   Solution 1 (preferred): Run the program twice - one for configuration and again to undo it.
#   Solution 2: Omit SSH parameters and generate the raw configuration outputs and manually enter config to devices.
##################################

import openpyxl
import argparse


# import netmiko # We actually import this within the push config file to save this dependency

def parse_args():
    # Add all of our CLI arguments here, optional and otherwise.
    parser = argparse.ArgumentParser(
        description='Processes an excel file and uses excel entries to substitute configuration templates.',
        epilog='Written by David Chidell (dchidell@cisco.com)')

    parser.add_argument('definition', metavar='spreadsheet.xlsx',
                        help='This is the excel file containing the data we wish to parse')
    parser.add_argument('template', nargs='+', metavar='template.txt',
                        help='This is the template file to use. As many template files as you like can be used.')
    parser.add_argument('--push-config', action='store_true',
                        help='If this option is set we will attempt to push config to a specified switch')
    parser.add_argument('-i', '--ip-address', metavar='ipaddr',
                        help='This is the IP / hostname of the switch you want to push the config to.', default=None)
    parser.add_argument('-p', '--port', metavar='portnumber',
                        help='The SSH port number.', default=22)
    parser.add_argument('-u', '--username', metavar='username',
                        help='The SSH username.', default='admin')
    parser.add_argument('-pw', '--password', metavar='password',
                        help='The SSH password.', default='password')
    parser.add_argument('-t', '--device-type', metavar='device_type', default='cisco_ios',
                        help='The type of device.', choices=['cisco_ios', 'cisco_nxos', 'cisco_xr', 'cisco_asa', 'cisco_xe','cisco_tp','cisco_s300'])
    parser.add_argument('-s', '--sheet', metavar='sheetname',
                        help='Sets the sheet name to use (defaults to active sheet if not specified)', default=None)
    parser.add_argument('-f', '--feedback', action='store_true',
                        help='Displays the result of pushing commands to a router.')
    return parser.parse_args()


def generate_master_list(file_name, sheet_name):
    # This is where we generate the primary list containing multiple dictionaries (one for each excel row)
    try:
        workbook = openpyxl.load_workbook(file_name)
    except FileNotFoundError:
        print('Error: Unable to find excel file: {}'.format(file_name))
        exit(1)

    # Get the first (active) sheet, or use the name specified via CLI args.
    if sheet_name is None:
        sheet = workbook.get_active_sheet()
    else:
        try:
            sheet = workbook.get_sheet_by_name(sheet_name)
        except KeyError:
            print('Error: Unable to find sheet: {} inside spreadsheet'.format(sheet_name))
            exit(2)

    # Generate our empty lists

    # This is what we'll return and the whole point in this function.
    master_list = []

    # This list will be retrieved from the second row of the spreadsheet and used as the dict keys later on
    keys = []

    # This dictionary is a metadata dictionary containing the keys and column positions for data retrieval.
    order_dict = {}

    # Iterate over each row in the excel sheet
    for row_count, row in enumerate(sheet.rows):
        # First row is heading titles, let's ignore it.
        if row_count == 0:
            continue
        # Second row contains field names. Let's index them to the order_dict dictionary.
        if row_count == 1:
            for field_count, field in enumerate(row):
                if field.value == '':
                    continue
                keys.append(field.value)
                order_dict[field.value] = field_count
        # All other rows contain data, time to process.
        else:
            # If the first field in a row is blank we're done.
            if len(row) > 0:

                if row[0].value == None:
                    break

            # This list is a list of values contained within each row.
            row_list = []
            for field in row:
                # Row ends when we hit a blank entry, otherwise add it to the dict.
                if field.value == '':
                    continue
                row_list.append(field.value)

            # Create our new dictionary from the keys we've indexed. Then make sure each entry is added to the dict.
            row_dict = dict.fromkeys(keys)
            for key in keys:
                row_dict[key] = row_list[order_dict[key]]

            # By default an empty entry will be set to the string value 'None' - we'd prefer a blank variable.
            for entry in row_dict:
                if row_dict[entry] is None:
                    row_dict[entry] = ''

            # Add our current row to the master list
            master_list.append(row_dict)
    return master_list


def generate_config(master_list, template_input, output):
    # This function takes the master_list and a template file and generates the configuration output file from those two
    # First, open and read our entire template to a string
    try:
        with open(template_input, 'r') as f:
            content = f.read()
            f.close()
    except FileNotFoundError:
        print('Error: Unable to open template file: {}'.format(template_input))
        exit(3)

    # Now open a new file (the output file)
    with open(output, 'w') as f:
        complete_output = []
        # Iterate over the master list and add each template instance to the output file.
        for entry in master_list:
            try:
                # This is the really clever bit, we take the dictionary entry and push the entire dictionary to the format function.
                out_content = content.format(**entry)
                f.write(out_content)
                complete_output.append((out_content + '\n\n'))
            except KeyError as e:
                print(
                    'Error: found key: {} in template file {} but not in excel spreadsheet. Remove the key in the template or add it to the excel file.'.format(
                        str(e), template_input))
                f.close()
                exit(4)
            except ValueError as e:
                print('Error: Could not read template file. There is probably a curly bracket missing!')
                for line_no,line in enumerate(content.split('\n'),1):
                    left_count = line.count('{')
                    right_count = line.count('}')
                    if left_count != right_count:
                        print('Error: Found curly bracket mismatch on line {}. Line: {}'.format(line_no,line))
                exit(1)
            # Put some seperators in the file to keep it readable.
            #f.write('\n\n!********************\n\n\n') #This breaks non-cisco config. We'll stick to newlines
            f.write('\n\n\n')
        f.close()
    # Return the raw output as a list, we'll need it if we're pushing config to devices.
    return complete_output


def push_config(ip_addr, port, user, password, device_type, config_list, feedback):
    # This function takes various router parameters and a config file and pushes the config to the box.
    # First we import the netmiko library. It's better to import at the top - but if we're not using the script to push config we don't want to depend on it
    import netmiko
    device_info = {
        'device_type': device_type,
        'ip': ip_addr,
        'port': port,
        'username': user,
        'password': password,
        'verbose': False,
    }
    if ip_addr is None:
        print('Error: You must specify an IP, use -i <address> or --ip-address <address>')
        exit(6)
    try:
        # This is where all the hard work is cone, the connection is made and config is pushed.
        connection = netmiko.ConnectHandler(**device_info)
    except netmiko.ssh_exception.NetMikoAuthenticationException:
        print('Error: Unable to authenticate to {} using specified credentials.'.format(ip_addr))
        exit(5)
    except netmiko.ssh_exception.NetMikoTimeoutException:
        print('Error: SSH Timeout occurred. Ensure that the specified IP is available via SSH at {} on port {}'.format(
            ip_addr, port))
        exit(7)

    full_cli_output = ''
    for entry_count, entry in enumerate(config_list):
        print('***Pushing configuration element {} of {}'.format(entry_count,len(config_list)))
        output = connection.send_config_set([entry])
        full_cli_output += output
    # If the feedback is set to true we'll display the entire configuration process.
    # We can see if errors occurred when pushing. Recommended for small configs only!
    if feedback is True:
        print(full_cli_output)


def main():
    # The standard main function, which acts as the entry point to the program.

    # Parse all of our args.
    args = parse_args()

    # Read and generate our master list index.
    print('***Reading Master Excel spreadsheet {}...'.format(args.definition))
    master_list = generate_master_list(args.definition, args.sheet)
    print('***Read {} entries from master list...'.format(len(master_list)))

    # Read through all the template files we recieved from the CLI and generate config for each one.
    for template in args.template:
        output_file = '{}.output'.format(template)
        print('***Generating configuration template file: {} output file: {} ...'.format(template, output_file))
        raw_output = generate_config(master_list, template, output_file)

        # If we wanted to push config to devices, set up a new connection for each template we're pushing.
        if args.push_config is True:
            print('***Attempting to push configuration to device...')
            push_config(args.ip_address, args.port, args.username, args.password, args.device_type, raw_output,
                        args.feedback)

    print('***Complete! Exiting...')

# Needed to define entry point.
if __name__ == '__main__':
    main()
