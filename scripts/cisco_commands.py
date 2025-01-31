#!/usr/bin/env python3
"""
Cisco RTBH Commands Generator

This script generates Cisco IOS commands for RTBH filtering:
1. Reads IP addresses from the merged IP list
2. Converts each IP/CIDR to proper Cisco route command format
3. Adds null routing and tag parameters
4. Generates a complete configuration file with 'end' command

The script validates IP addresses and CIDR notation before processing.
Command format: ip route <network> <mask> Null0 tag <number>
"""

import sys
import ipaddress
import os

def read_config(filename):
    """Read configuration from file"""
    config = {}
    with open(filename, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip() and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                config[key] = value
    return config

def calculate_mask(cidr: int) -> list:
    """Calculate subnet mask from CIDR notation"""
    mask = [0, 0, 0, 0]
    for i in range(cidr):
        mask[i // 8] += 1 << (7 - i % 8)
    return mask

def main():
    """Main processing function"""
    config = read_config('configs/cisco_config.conf')

    if len(sys.argv) != 3:
        print("Usage: script.py <command1> <command2>")
        exit(1)

    if os.stat(config['INPUT_IP_LIST']).st_size == 0:
        print("Error: IP list file is empty")
        exit(1)

    with open(config['INPUT_IP_LIST'], 'r', encoding='utf-8') as f, \
         open(config['OUTPUT_COMMANDS_FILE'], 'w', encoding='utf-8') as fw:

        commands = []
        for line in f:
            if '#' in line:
                continue

            try:
                ipaddress.ip_network(line.strip(), strict=False)
            except ValueError as e:
                print(f"Skipping invalid IP/CIDR: {line.strip()} ({str(e)})")
                continue

            # Get address string and CIDR string from command line
            haveMask = line.find('/')
            firstCommand = sys.argv[1]
            secondCommand = sys.argv[2]

            # Automatically add /32 mask if missing
            line = line.strip()
            if '/' not in line:
                continue

            (addrString, cidrString) = line.split('/')

            # Split address into octets and turn CIDR into int
            addr = addrString.split('.')
            try:
                cidr = int(cidrString)
            except ValueError:
                print(f"Invalid CIDR: {cidrString}")
                continue

            # Initialize the netmask and calculate based on CIDR mask
            mask = calculate_mask(cidr)

            # Initialize net and binary and netmask with addr to get network
            net = []
            for i in range(4):
                net.append(int(addr[i]) & mask[i])

            # Duplicate net into broad array, gather host bits, and generate broadcast
            broad = list(net)
            brange = 32 - cidr
            for i in range(brange):
                broad[3 - i//8] = broad[3 - i//8] + (1 << (i % 8))

            # Print information, mapping integer lists to strings for easy printing
            test = f"{firstCommand} {addrString} {'.'.join(map(str, mask))} {secondCommand}\n"
            commands.append(test.strip())  # Add command without trailing \n

        # After collecting all commands
        if commands:
            pass  # Removed end addition here
        else:
            print("Warning: command list is empty")

        output_content = '\n'.join(commands) if commands else ''
        output_content += '\nend' if commands else 'end'
        fw.write(output_content.strip())

if __name__ == "__main__":
    main()


