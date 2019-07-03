#!/bin/bash
# This is the main script. You need execute it via CRON job.
#
# Delete old lists
rm ./raw_lists/*.netset
rm ./raw_lists/*.ipset

# Download needed lists from https://iplists.firehol.org/ 
# See description of each list inside 'raw_lists' directory
cd ./raw_lists/

wget https://raw.githubusercontent.com/ktsaou/blocklist-ipsets/master/firehol_level1.netset
wget https://raw.githubusercontent.com/ktsaou/blocklist-ipsets/master/firehol_level2.netset
wget https://raw.githubusercontent.com/ktsaou/blocklist-ipsets/master/firehol_level3.netset
wget https://raw.githubusercontent.com/ktsaou/blocklist-ipsets/master/voipbl.netset
wget https://raw.githubusercontent.com/ktsaou/blocklist-ipsets/master/firehol_level4.netset
wget https://raw.githubusercontent.com/ktsaou/blocklist-ipsets/master/bi_any_0_1d.ipset
#VERY BIG LIST! wget https://raw.githubusercontent.com/ktsaou/blocklist-ipsets/master/firehol_anonymous.netset
wget https://raw.githubusercontent.com/ktsaou/blocklist-ipsets/master/normshield_all_attack.ipset
wget https://raw.githubusercontent.com/ktsaou/blocklist-ipsets/master/dshield.netset
wget https://raw.githubusercontent.com/ktsaou/blocklist-ipsets/master/snort_ipfilter.ipset
wget https://raw.githubusercontent.com/ktsaou/blocklist-ipsets/master/et_compromised.ipset

# back to folder

cd ..

# use iprange tool to merge all lists in one. See iprange manual

iprange ./raw_lists/*.*set --merge > ip_list.txt

# Exclude LAN networks and multicast from the list. Do it only if you have private LAN networks configured on your Edge routers

sed -i '/10.0.0.0/d' ip_list.txt
sed -i '/192.168.0.0/d' ip_list.txt
sed -i '/172.16.0.0/d' ip_list.txt
sed -i '/127.0.0.0/d' ip_list.txt
sed -i '/224.0.0.0/d' ip_list.txt

# create Cisco router commands list by adding 'prifix' and 'suffix' and convert CIDR to cisco mask format
# See description in cisco_commands.py 

python cisco_commands.py 'ip route' 'Null0 tag 66'

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

python send_command_prompting.py

