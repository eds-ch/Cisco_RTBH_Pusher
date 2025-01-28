#!/bin/bash
# This is the main script. You need execute it via CRON job.

echo "Starting IP lists processing..."

# Delete old lists except .myset files
echo "Cleaning old files in raw_lists directory..."
find ./raw_lists/ -type f ! -name "*.myset" -delete

# Change to raw_lists directory
cd ./raw_lists/

# Download IP lists from configured sources
echo -e "\nDownloading IP lists from sources defined in configs/ip_lists.conf..."

# Read active URLs from config file and download them
echo -e "\nReading IP lists from configs/ip_lists.conf..."
while IFS= read -r line || [[ -n "$line" ]]; do
    # Skip empty lines and comments
    [[ -z "$line" ]] && continue
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    
    # Download the file and show progress
    echo "Downloading: $line"
    wget -q "$line"
done < ../configs/ip_lists.conf

# back to folder
cd ..

# List all downloaded files
echo -e "\nFiles downloaded and ready for processing:"
ls -1 ./raw_lists/* | while read file; do
    echo "- $(basename "$file")"
done

# use iprange tool to merge all lists in one
echo -e "\nMerging all lists into ip_list.txt..."
iprange ./raw_lists/*.* --merge > ip_list.txt

# Exclude networks from the list using exclude_networks.conf
echo -e "\nProcessing exclusions from configs/exclude_networks.conf:"
while IFS= read -r line || [[ -n "$line" ]]; do
    # Skip empty lines and comments
    [[ -z "$line" ]] && continue
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    
    # Remove IP from the list and show progress
    echo "Excluding: $line"
    sed -i "/${line}/d" ip_list.txt
done < configs/exclude_networks.conf

echo -e "\nFinal IP list created: ip_list.txt"
echo "Total unique IPs in final list: $(wc -l < ip_list.txt)"

# create Cisco router commands list by adding 'prifix' and 'suffix' and convert CIDR to cisco mask format
# See description in cisco_commands.py 
python scripts/cisco_commands.py 'ip route' 'Null0 tag 66'

# Add first line to cisco_commands.txt to remove all old static routes from Cisco ( no ip route * )

sed -i '1s/^/no ip route *\n/' cisco_commands.txt

# Copy Cisco commands file to local FTP server folder. Cisco router will download this command set from FTP and execute it locally.
# Add local user to Ftp group: usermod -a -G ftp exampleusername
# Please change it according to your configuration

cp cisco_commands.txt /srv/ftp/upload

# Execute command on Cisco IOS remotely. 
# Command will download config from local FTP server and put it to Cisco router running-config
# Script is based on Netmico lib
# https://github.com/ktbyers/netmiko
# you must install netmico lib from user who whill execute the script!

echo -e "\nExecuting command on Cisco IOS remotely..."
python3 scripts/send_command_prompting.py

echo "IP lists processing completed."
