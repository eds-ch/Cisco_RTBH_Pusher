#!/bin/bash
#
# Cisco RTBH Automation Main Script
#
# This script orchestrates the entire RTBH process:
# 1. Downloads IP blocklists from configured sources
# 2. Merges and deduplicates IP lists
# 3. Applies exclusion rules
# 4. Generates Cisco IOS commands
# 5. Uploads and applies configuration to router
#
# Usage: 
# - Execute directly: ./start_pusher.sh
# - Execute without router upload: ./start_pusher.sh --no-upload
# - Schedule via cron for automatic updates
#
# Requirements:
# - Python 3 with netaddr library
# - wget for downloading lists
# - Scrapli and Paramiko for router communication

UPLOAD_ENABLED=true
if [[ "${1:-}" == "--no-upload" ]]; then
    UPLOAD_ENABLED=false
    printf "No-upload mode enabled\n"
fi

printf "Starting IP lists processing...\n"

# Check if raw_lists directory exists, create if not
if [ ! -d "./raw_lists" ]; then
    printf "Creating raw_lists directory...\n"
    mkdir -p "./raw_lists"
fi

# Delete old lists except .myset files
printf "Cleaning up old lists...\n"
find "./raw_lists/" -type f ! -name "*.myset" -delete

# Change to raw_lists directory
cd "./raw_lists/" || exit 1

# Download IP lists from configured sources
printf "\nDownloading IP lists from configs/ip_lists.conf...\n"

# Read active URLs from config file and download them
printf "\nReading IP lists from configs/ip_lists.conf...\n"
while IFS= read -r line || [[ -n "${line}" ]]; do
    # Skip empty lines and comments
    [[ -z "${line}" ]] && continue
    [[ "${line}" =~ ^[[:space:]]*# ]] && continue
    
    # Download the file and show progress
    printf "Downloading: %s\n" "${line}"
    wget -q "${line}"
done < "../configs/ip_lists.conf"

# back to folder
cd .. || exit 1

# List all downloaded files
printf "\nFiles downloaded and ready for processing:\n"
find "./raw_lists/" -type f -print0 | while IFS= read -r -d '' file; do
    printf "%s%s\n" "- " "$(basename "${file}")"
done

# Use Python and netaddr to merge lists
printf "\nMerging lists into ip_list.txt...\n"
python3 scripts/merge_ip_ranges.py "./raw_lists/*" "configs/exclude_networks.conf" "ip_list.txt"

printf "\nFinal IP list created: ip_list.txt\n"
printf "Total unique IPs: %s\n" "$(wc -l < ip_list.txt)"

# Generate Cisco commands list
python3 scripts/cisco_commands.py 'ip route' 'Null0 tag 66'

# Post-process commands file
sed -i '/^$/d' "cisco_commands.txt"  # Remove empty lines
sed -i '1s/^/no ip route *\n/' "cisco_commands.txt"  # Add cleanup routes command at the beginning

if "${UPLOAD_ENABLED}"; then
    printf "\nUploading commands to Cisco router...\n"
    python3 scripts/send_command_prompting.py
else
    printf "\nSkipping router upload\n"
fi

printf "\nIP lists processing completed.\n"
