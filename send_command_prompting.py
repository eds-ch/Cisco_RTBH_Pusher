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
from getpass import getpass

cisco1 = {
    "host": "XXX.XXX.XXX.XXX",
    "username": "trigger",
    "password": "PASSWORD",
    "device_type": "cisco_ios",
}

net_connect = Netmiko(**cisco1)
command = "copy ftp://XXX.XXX.XXX.XXX/upload/cisco_commands.txt running-config"
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
