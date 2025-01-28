#!/usr/bin/env python
# 
# This script is used to convert IP lists from FireHOL to Cisco routers "ip route" command
# to execute this command please use: python cisco_command.py 'firstCommandPrefix' 'secondCommandSuffix'
# The list from FireHOL must be in the same directory with a name defined in config
#
# This script is based on subnet.py script from https://gist.github.com/nboubakr/4344773

import sys
import re

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

f = open(config['INPUT_IP_LIST'], 'r')
fw = open(config['OUTPUT_COMMANDS_FILE'], 'w')
for line in f:

	comment = line.find('#')
	if comment != -1:
		continue


	# Get address string and CIDR string from command line
	haveMask = line.find('/')
	firstCommand = sys.argv[1]
	secondCommand = sys.argv[2]

	if haveMask < 0:
		line = line + "/32"
		line = re.sub("^\s+|\n|\r|\s+$", '', line)

	(addrString, cidrString) = line.split('/')

	# Split address into octets and turn CIDR into int
	addr = addrString.split('.')
	cidr = int(cidrString)

	# Initialize the netmask and calculate based on CIDR mask
	mask = [0, 0, 0, 0]
	for i in range(cidr):
		mask[i/8] = mask[i/8] + (1 << (7 - i % 8))

	# Initialize net and binary and netmask with addr to get network
	net = []
	for i in range(4):
		net.append(int(addr[i]) & mask[i])

	# Duplicate net into broad array, gather host bits, and generate broadcast
	broad = list(net)
	brange = 32 - cidr
	for i in range(brange):
		broad[3 - i/8] = broad[3 - i/8] + (1 << (i % 8))

	# Print information, mapping integer lists to strings for easy printing
	test = firstCommand + " " + addrString + " " + "." .join(map(str, mask)) + " " + secondCommand + "\n"
	fw.write(test)


