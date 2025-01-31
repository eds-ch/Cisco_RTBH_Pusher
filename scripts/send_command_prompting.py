#!/usr/bin/env python3

"""
Cisco Router Configuration Uploader

This script uploads and applies configuration commands to a Cisco router.
It performs two main tasks:
1. Uploads the generated commands file to router using SCP
2. Applies the configuration using 'copy' command via SSH

The script uses Scrapli for SSH connectivity and Paramiko for SCP file transfer.
All connection parameters are read from cisco_config.conf file.
"""

import paramiko
from scp import SCPClient
from scrapli import Scrapli
from scrapli.exceptions import ScrapliException
from scrapli.driver.core import IOSXEDriver

def read_config(filename):
    """Read configuration from file.
    
    Args:
        filename (str): Path to configuration file
        
    Returns:
        dict: Configuration parameters
    """
    config = {}
    with open(filename, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip() and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                config[key] = value
    return config

def upload_file(config):
    """Upload generated commands file to Cisco router using SCP protocol.
    
    Args:
        config (dict): Configuration parameters from cisco_config.conf
    """
    dest = config['SCP_DESTINATION']
    if ":/" not in dest:
        dest = dest.replace(":", ":/", 1)
    
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(
            hostname=config['CISCO_HOST'],
            username=config['CISCO_USERNAME'],
            password=config['CISCO_PASSWORD'],
            allow_agent=False,
            look_for_keys=False,
        )
        
        with SCPClient(client.get_transport()) as scp:
            print(f"Started uploading file to {config['CISCO_HOST']} ({dest})...")
            scp.put(config['OUTPUT_COMMANDS_FILE'], dest)
            print("File uploaded successfully")
            
    finally:
        client.close()

def apply_config(config):
    """Apply configuration from uploaded file to router.
    
    Args:
        config (dict): Configuration parameters from cisco_config.conf
    """
    device = {
        "host": config['CISCO_HOST'],
        "auth_username": config['CISCO_USERNAME'],
        "auth_password": config['CISCO_PASSWORD'],
        "auth_strict_key": False,
        "timeout_socket": 60,
        "timeout_transport": 120,
    }

    try:
        print(f"Connecting to {device['host']}...")
        with IOSXEDriver(**device) as conn:
            print("Initiating configuration copy...")
            
            response = conn.send_interactive(
                [
                    (f"copy {config['SCP_DESTINATION']} running-config", "Destination filename [running-config]?", True),
                ],
                failed_when_contains=["%Error", "Invalid"],
                timeout_ops=300
            )
            
            print("\nCommand execution result:")
            print(response.result)
            
    except ScrapliException as e:
        print(f"Execution error: {str(e)}")
        exit(1)

if __name__ == "__main__":
    config = read_config('configs/cisco_config.conf')
    upload_file(config)
    apply_config(config)
