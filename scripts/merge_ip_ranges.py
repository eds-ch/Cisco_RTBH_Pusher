#!/usr/bin/env python3
"""
IP Networks Merger and Exclusion Processor

This script processes multiple IP lists and exclusion rules:
1. Reads IP networks from multiple input files
2. Merges them into a single set removing duplicates
3. Applies exclusion rules from exclude_networks.conf
4. Outputs the final list in CIDR format

Uses netaddr library for IP network operations.
"""
from netaddr import IPSet, IPNetwork
import glob
import sys

def main():
    if len(sys.argv) != 4:  # Check number of arguments
        print("Usage: python3 merge_ip_ranges.py <input_glob> <exclude_file> <output_file>")
        exit(1)
    
    input_glob = sys.argv[1]
    exclude_file = sys.argv[2]
    output_file = sys.argv[3]
    
    # Merge networks from input files
    merged_set = IPSet()
    for filename in glob.glob(input_glob):
        with open(filename) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    try:
                        network = IPNetwork(line)
                        merged_set.add(network)
                    except Exception as e:
                        print(f"Skipping invalid network: {line}")
    
    # Read exclusions
    exclude_set = IPSet()
    with open(exclude_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                try:
                    exclude_set.add(IPNetwork(line))
                except Exception as e:
                    print(f"Skipping invalid exclusion: {line}")
    
    # Apply exclusions
    final_set = merged_set - exclude_set
    
    # Save result
    with open(output_file, 'w') as f:
        for network in final_set.iter_cidrs():  # Iterate through CIDR
            f.write(f"{network}\n")

if __name__ == "__main__":
    main() 