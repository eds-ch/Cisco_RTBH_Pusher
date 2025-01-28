#!/usr/bin/env python
#
# This script is used to execute remote command with a prompt in a Cisco router.
# Is based on Netmico script https://github.com/ktbyers/netmiko/tree/develop/examples/use_cases
#
# This script will run a command on a TRIGGER Cisco router to download routes from FTP and deploy them in to running-config
# 
# To execute this script you need to install Netmico lib first. See https://github.com/ktbyers/netmiko#Installation
#
# Please make changes to the file with your settings
#
from netmiko import Netmiko
from netmiko import ConnectHandler
from getpass import getpass

def read_config(filename):
    config = {}
    with open(filename, 'r') as f:
        for line in f:
            # Skip comments and empty lines
            if line.strip() and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                config[key] = value
    return config

# Read configuration
config = read_config('configs/cisco_config.conf')

cisco1 = {
    "host": config['CISCO_HOST'],
    "username": config['CISCO_USERNAME'],
    "password": config['CISCO_PASSWORD'],
    "device_type": config['CISCO_DEVICE_TYPE'],
}

#net_connect = Netmiko(**cisco1)
net_connect = ConnectHandler(**cisco1)
command = f"copy ftp://{config['FTP_SERVER']}{config['FTP_PATH']} running-config"
print()
print(net_connect.find_prompt())
output = net_connect.send_command_timing(command)
if "running-config" in output:
    output += net_connect.send_command_timing(
        "running-config", strip_prompt=False, strip_command=False
    )
net_connect.disconnect()
print(output)
print()
