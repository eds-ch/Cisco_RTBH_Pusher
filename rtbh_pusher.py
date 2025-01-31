#!/usr/bin/env python3
"""
Cisco RTBH Automation Main Script

This script combines all RTBH automation functionality:
1. Downloads IP blocklists from configured sources
2. Merges and deduplicates IP lists
3. Applies exclusion rules
4. Generates Cisco IOS commands
5. Uploads and applies configuration to router
"""

import os
import sys
import glob
import argparse
import asyncio
import aiohttp
import ipaddress
import re
import configparser
from aiohttp import ClientTimeout
from urllib.parse import urlparse
from netaddr import IPSet, IPNetwork
import paramiko
from scp import SCPClient
from scrapli.exceptions import ScrapliException
from scrapli.driver.core import IOSXEDriver
from typing import List, Tuple, Dict, Optional

# Constants
CHUNK_SIZE = 8192
DEFAULT_TIMEOUT = 30
USER_AGENT = 'Mozilla/5.0 (compatible; RTBH-Pusher/1.0)'
CONFIG_FILE = 'configs/rtbh.conf'
DEFAULT_CISCO_TAG = '66'
DEFAULT_CISCO_COMMAND_PREFIX = 'ip route'
DEFAULT_CISCO_COMMAND_SUFFIX = 'Null0 tag'

def read_config(section: str) -> Dict[str, str]:
    """Read configuration section from file
    
    Args:
        section: Name of the configuration section to read
    
    Returns:
        Dictionary containing configuration key-value pairs
    """
    config = configparser.ConfigParser(allow_no_value=True, inline_comment_prefixes='#')
    if not config.read(CONFIG_FILE):
        print(f"Error: Config file {CONFIG_FILE} not found")
        sys.exit(1)
    if not config.has_section(section):
        print(f"Error: Missing section '{section}' in config file")
        sys.exit(1)
    return {k.upper(): v for k, v in config[section].items()}

def read_list_config(section: str) -> List[str]:
    """Read configuration section as list of non-empty, non-comment lines
    
    Args:
        section: Name of the configuration section to read
    
    Returns:
        List of active configuration lines
    """
    config = configparser.ConfigParser(allow_no_value=True)
    config.read(CONFIG_FILE)
    if section == 'blocklists':
        return [
            value.strip()
            for key, value in config[section].items()
            if value and not key.startswith('#')
        ]
    else:
        return [
            line.strip() 
            for line in config[section].keys() 
            if line.strip() and not line.startswith('#')
        ]

def ensure_raw_lists_dir() -> None:
    """Create raw_lists directory if it doesn't exist"""
    if not os.path.exists("./raw_lists"):
        print("Creating raw_lists directory...")
        os.makedirs("./raw_lists")

def clean_old_lists() -> None:
    """Delete old lists except .myset files"""
    print("Cleaning up old lists...")
    for f in glob.glob("./raw_lists/*"):
        if not f.endswith('.myset'):
            os.remove(f)

async def download_file(session: aiohttp.ClientSession, url: str) -> Tuple[str, bool]:
    """Download single file asynchronously
    
    Args:
        session: aiohttp client session
        url: URL to download from
    
    Returns:
        Tuple containing (filename, success_status)
    """
    try:
        async with session.get(url) as response:
            if response.status != 200:
                print(f"Error downloading {url}: HTTP {response.status}")
                return "", False
            
            # Get filename from URL or Content-Disposition
            filename: Optional[str] = None
            if "Content-Disposition" in response.headers:
                matches = re.findall(
                    "filename=(.+)",
                    response.headers["Content-Disposition"]
                )
                if matches:
                    filename = matches[0].strip('"')
            
            if not filename:
                filename = os.path.basename(urlparse(url).path)
                if not filename:
                    filename = "ip_list_" + str(hash(url))
            
            output_path = os.path.join("./raw_lists/", filename)
            
            # Download file
            with open(output_path, 'wb') as f:
                while True:
                    chunk = await response.content.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    f.write(chunk)
            
            print(f"Successfully downloaded: {url}")
            return output_path, True
            
    except Exception as e:
        print(f"Error downloading {url}: {str(e)}")
        return "", False

async def download_ip_lists() -> bool:
    """Download IP lists from configured sources"""
    print("\nDownloading IP lists from configuration...")
    
    urls = read_list_config('blocklists')
    
    if not urls:
        print("\nError: No active URLs found in configuration")
        print("Please uncomment or add at least one URL with IP blocklist")
        print("Example: https://feodotracker.abuse.ch/downloads/ipblocklist_recommended.txt")
        return False
    
    print(f"Found {len(urls)} active URLs to process")
    timeout = ClientTimeout(total=DEFAULT_TIMEOUT)
    headers = {'User-Agent': USER_AGENT}
    
    async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
        tasks = [download_file(session, url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check if at least one file was downloaded successfully
        successful_downloads = [r for r in results if isinstance(r, tuple) and r[1]]
        
        if not successful_downloads:
            print("Error: No files were downloaded successfully")
            return False
        
        print(f"Successfully downloaded {len(successful_downloads)} out of {len(urls)} files")
        return True

def check_step(success: bool, step_name: str) -> None:
    """Check if step completed successfully and exit if not
    
    Args:
        success: Result of the step
        step_name: Name of the step for error message
    """
    if not success:
        print(f"\nError: {step_name} failed")
        sys.exit(1)

def merge_ip_ranges(input_glob: str, output_file: str) -> bool:
    """Merge IP lists and apply exclusions
    
    Args:
        input_glob: Glob pattern for input files
        output_file: Path to output file
    
    Returns:
        bool: True if merge completed successfully
    """
    print("\nMerging lists into ip_list.txt...")
    
    files = glob.glob(input_glob)
    if not files:
        print(f"Warning: No files found matching pattern {input_glob}")
        return False
    
    # Merge networks from input files
    merged_set = IPSet()
    success = False
    for filename in files:
        with open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    try:
                        network = IPNetwork(line)
                        merged_set.add(network)
                        success = True
                    except Exception as e:
                        print(f"Skipping invalid network: {line}")
    
    if not success:
        print("Error: No valid networks found in input files")
        return False
    
    # Read exclusions
    exclude_networks = read_list_config('exclude_networks')
    exclude_set = IPSet()
    for network in exclude_networks:
        try:
            exclude_set.add(IPNetwork(network))
        except Exception as e:
            print(f"Skipping invalid exclusion: {network}")
    
    # Apply exclusions and save
    final_set = merged_set - exclude_set
    if not final_set:
        print("Error: No networks left after applying exclusions")
        return False

    with open(output_file, 'w', encoding='utf-8') as f:
        for network in final_set.iter_cidrs():
            f.write(f"{network}\n")
    return True

def calculate_mask(cidr: int) -> List[int]:
    """Calculate subnet mask from CIDR notation
    
    Args:
        cidr: CIDR prefix length (0-32)
    
    Returns:
        List of four integers representing IPv4 mask octets
    """
    mask = [0, 0, 0, 0]
    for i in range(cidr):
        mask[i // 8] += 1 << (7 - i % 8)
    return mask

def generate_cisco_commands(
    config: dict,
    first_command: str,
    second_command: str
) -> bool:
    """Generate Cisco IOS commands for RTBH filtering
    
    Args:
        config: Configuration dictionary
        first_command: First part of Cisco command (e.g. 'ip route')
        second_command: Second part of Cisco command (e.g. 'Null0 tag 66')
    
    Returns:
        bool: True if commands were generated successfully
    
    Example:
        >>> generate_cisco_commands(config, 'ip route', 'Null0 tag 66')
        True
    """
    if os.stat(config['INPUT_IP_LIST']).st_size == 0:
        print("Error: IP list file is empty")
        return False

    with (
        open(config['INPUT_IP_LIST'], 'r', encoding='utf-8') as f,
        open(config['OUTPUT_COMMANDS_FILE'], 'w', encoding='utf-8') as fw
    ):
        
        commands = []
        for line in f:
            if '#' in line:
                continue

            try:
                ipaddress.ip_network(line.strip(), strict=False)
            except ValueError as e:
                print(f"Skipping invalid IP/CIDR: {line.strip()} ({str(e)})")
                continue

            line = line.strip()
            if '/' not in line:
                continue

            (addrString, cidrString) = line.split('/')
            
            try:
                cidr = int(cidrString)
            except ValueError:
                print(f"Invalid CIDR: {cidrString}")
                continue

            mask = calculate_mask(cidr)
            test = f"{first_command} {addrString} {'.'.join(map(str, mask))} {second_command}"
            commands.append(test)

        output_content = '\n'.join(commands) if commands else ''
        output_content += '\nend' if commands else 'end'
        fw.write(output_content)
    
    # Post-process commands file
    with open(config['OUTPUT_COMMANDS_FILE'], 'r+') as f:
        content = f.read()
        f.seek(0)
        f.write(f"no ip route *\n{content}")
        f.truncate()
    
    return True

def upload_file(config: dict) -> None:
    """Upload generated commands file to Cisco router using SCP protocol.
    
    Args:
        config: Configuration parameters from cisco_config.conf
    """
    required_keys = ['CISCO_HOST', 'CISCO_USERNAME', 'CISCO_PASSWORD', 'SCP_DESTINATION']
    for key in required_keys:
        if key not in config:
            print(f"Error: Missing required configuration key: {key}")
            sys.exit(1)
    
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

def apply_config(config: dict) -> None:
    """Apply configuration to router using SSH
    
    Args:
        config: Configuration parameters from cisco_config.conf
    
    Raises:
        ScrapliException: If there's an error during configuration
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
                    (
                        f"copy {config['SCP_DESTINATION']} running-config",
                        "Destination filename [running-config]?",
                        True
                    ),
                ],
                failed_when_contains=["%Error", "Invalid"],
                timeout_ops=300
            )
            
            print("\nCommand execution result:")
            print(response.result)
            
    except ScrapliException as e:
        print(f"Execution error: {str(e)}")
        sys.exit(1)

def main() -> None:
    """Main function that orchestrates the RTBH automation process"""
    try:
        parser = argparse.ArgumentParser(description='Cisco RTBH Automation Tool')
        parser.add_argument(
            '--no-upload',
            action='store_true',
            help='Run without uploading to router'
        )
        args = parser.parse_args()

        print("Starting IP lists processing...")

        # Initialize
        ensure_raw_lists_dir()
        clean_old_lists()
        
        # Download lists
        check_step(
            asyncio.run(download_ip_lists()),
            "Downloading IP lists"
        )
        
        # List downloaded files
        print("\nFiles downloaded and ready for processing:")
        for f in glob.glob("./raw_lists/*"):
            print(f"- {os.path.basename(f)}")
        
        # Merge lists
        check_step(
            merge_ip_ranges("./raw_lists/*", "ip_list.txt"),
            "Merging IP lists"
        )
        
        print("\nFinal IP list created: ip_list.txt")
        with open("ip_list.txt", 'r', encoding='utf-8') as f:
            ip_count = sum(1 for line in f)
            print(f"Total unique IPs: {ip_count}")
            check_step(ip_count > 0, "IP list generation")
        
        # Generate commands
        config = read_config('router')
        check_step(
            generate_cisco_commands(
                config,
                DEFAULT_CISCO_COMMAND_PREFIX,
                f"{DEFAULT_CISCO_COMMAND_SUFFIX} {DEFAULT_CISCO_TAG}"
            ),
            "Generating Cisco commands"
        )
        
        # Upload if enabled
        if not args.no_upload:
            print("\nUploading commands to Cisco router...")
            try:
                upload_file(config)
                apply_config(config)
                print("Router configuration completed successfully")
            except Exception as e:
                check_step(False, f"Router configuration: {str(e)}")
        else:
            print("\nSkipping router upload")
        
        print("\nIP lists processing completed.")
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"\nUnexpected error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 