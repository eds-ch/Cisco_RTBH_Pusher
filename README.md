# Cisco_RTBH_Pusher
Toolset for remotely triggered black hole (RTBH) filtering technique implementation based on Cisco routers and https://iplists.firehol.org/ IP lists.

If you did not setup RTBH already - you need to configure it according to this manual:
https://www.cisco.com/c/dam/en_us/about/security/intelligence/blackhole.pdf

You will need a Cisco router with at least 2Gb of RAM to be used as a TRIGGER router.

Then you can use this tool to convert FireHOL IP lists (or any other lists in CIDR format) to Cisco IOS commands and deploy it as static Null0 routes to your TRIGGER Cisco router.

What this tool does:
1) Download IP lists from any source. In my case it is https://iplists.firehol.org/
2) Group and merge this lists in one file
3) Convert grouped file in Cisco IOS commands list
4) Execute remote command on Cisco TRIGGER router to download command list file from FTP and push it to a running-config (I found that way is the fastest)

All IP lists used for RTBH are taken from https://iplists.firehol.org/
If you need any other lists - just add it to the script.

If you want to permanently add some IP addresses to the list - please add it to '1_local_list.myset' in CIDR format.

To use this tool you need to install:

1) IPrange. It is used for merging IP ranges from different lists. https://github.com/firehol/iprange
2) Netmico library. It is used to execute remote commands on a Cisco  TRIGGER router. Do not needed if you choose another way to deploy routes. Install this library from a user that whill execute the script!  https://github.com/ktbyers/netmiko
3) you need FTP server on local machine, or change script to your FTP server if you plan to use it on different server


Please also read description inside scripts
