#!/usr/bin/python
import getopt
import sys
import ipaddress
import random
import tor
import nmap
import time
import pycurl
import io
import os.path
import re
import dns.resolver
import dns.exception

hostlist = []
num_targets = 0
num_hosts = 0
total_targets_and_hosts = 0
targets_scanned = 0
first_run = True
sleep_time = 10

# helper functions
def refine_targetlist(targets):
    """
    Extract host ips from network blocks and randomize host scan order
    """
    global num_hosts
    outputlist = []
    for target_line in targets:
        target_line = target_line.rstrip()
        if "/" in target_line:
            try:
                for address in (ipaddress.ip_network(unicode(target_line)).hosts()):
                    outputlist.append(str(address))
            except ValueError:
                print ("[!] Warning: Invalid address or netmask: '" + target_line + "'")
        else:
            outputlist.append(target_line)
    random.shuffle(outputlist)
    # Use only a certain number of random hosts if user specified -n
    if num_hosts > 0:
        outputlist = outputlist[0:num_hosts]
    return outputlist


def query(url):
    """
    Uses pycurl to fetch a site using the proxy on the SOCKS_PORT.
    """
    socks_port = 9050
    output = io.BytesIO()

    curl_query = pycurl.Curl()
    curl_query.setopt(pycurl.URL, url)
    curl_query.setopt(pycurl.PROXY, 'localhost')
    curl_query.setopt(pycurl.PROXYPORT, socks_port)
    curl_query.setopt(pycurl.PROXYTYPE, pycurl.PROXYTYPE_SOCKS5_HOSTNAME)
    curl_query.setopt(pycurl.WRITEFUNCTION, output.write)

    try:
        curl_query.perform()
        return output.getvalue()
    except pycurl.error as exc:
        print "[*] Exiting check tor service to see if it is started...\n"
        sys.exit("Unable to reach %s (%s)" % (url, exc))


def printhelp():
    print'    USAGE: nmap-tor.py <options>'
    print'    OPTIONS:'
    print'      -h, --help        Display this message'
    print'      -t, --targets     Specify hosts to scan from a file or comma'
    print'                          separated list'
    print'      -p, --ports       Specify file of ports to be used on target'
    print'      -s, --sleep       Specify time in seconds to sleep between Nmap'
    print'                          requests (default:10)'
    print'      -n, --numhosts    Specify number of hosts to be randomly scanned'
    print'                          from the provided list'
    print'    EXAMPLES:'
    print'      Scan google.com and 8.8.8.8 on TCP 80, 443, and 22:'
    print'          nmap-tor.py -t google.com,8.8.8.8 -p 80,443,22\n'
    print'      Scan 50 random hosts from the 4.2.2.0/24 network on TCP 53:'
    print'          nmap-tor.py -t 4.2.2.0/24 -p 53 -n 50\n'
    print'      Scan hosts/networks in hosts.txt on the ports from ports.txt:'
    print'          nmap-tor.py -t hosts.txt -p ports.txt -s 15 -n 50\n'


# System arguments for input and output files
try:
    opts, args = getopt.getopt(sys.argv[1:], "ht:p:s:n:", ["help", "targets=", "ports=", "sleep=", "numhosts="])
except getopt.GetoptError:
    print printhelp()
    sys.exit(2)
if len(opts) == 0:
    printhelp()
    sys.exit("\nError: There were no arguments specified\n")
for opt, arg in opts:
    if opt in ("-h", "--help"):
        print printhelp()
        sys.exit(2)
    elif opt in ("-t", "--targets"):
        inputfile = arg
        if os.path.isfile(inputfile):
            try:
                with open(inputfile) as hostfile:
                    for host in hostfile:
                        hostlist.append(host)
            except:
                sys.exit("Input file for hosts is not valid")
        else:
            for host in inputfile.split(","):
                hostlist.append(host)
        # Check that all hosts are vaild IPs or hostnames
        temp_hostlist = hostlist
        for host in temp_hostlist:
            # Regex matches ip addresses and cidr notation for networks
            if re.match("^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)(/[0-9][0-9]?)?$", host):
                pass
            else:
                try:
                    dns.resolver.query(host, "A")
                except dns.exception.DNSException:
                    print "[!] Warning: unable to resolve host '" + host.rstrip() + "' - Skipping"
                    hostlist.remove(host)
    elif opt in ("-p", "--ports"):
        inputfile = arg
        targetports = []
        if os.path.isfile(inputfile):
            try:
                with open(inputfile) as portfile:
                    for port in portfile:
                        targetports.append(port.strip('\r\n'))
                    num_ports = len(targetports)
            except:
                sys.exit("Input file for ports is not valid")
        else:
            for host in inputfile.split(","):
                try:
                    if int(host.strip()) in range(0,65536):
                        targetports.append(host)
                    else:
                        raise ValueError
                except ValueError:
                    print "[!] Warning: Invalid port specified: '" + str(host) + "'"
    elif opt in ("-n", "--numhosts"):
        num_hosts = int(arg)
    elif opt in ("-s", "--sleep"):
        sleep_time = float(arg)

print "[+] Nmap-Tor-Scanner starting up...\n"
targetlist = refine_targetlist(hostlist)
total_targets_and_hosts = len(targetlist) * len(targetports)

for target in targetlist:
    for dest_port in targetports:
        if not first_run:
            print "[+] Sleeping for " + str(sleep_time) + " seconds..."
            time.sleep(sleep_time)
            tor.changeIP()
        else:
            first_run = False
        print(query("https://www.atagar.com/echo.php"))
        print "Trying {0:s} on TCP {1:s}".format(target, dest_port)
        nmap.print_scan(nmap.do_scan(target, '-sT -p ' + str(dest_port)))
        targets_scanned += 1
        print "\n[+] (" + str(targets_scanned) + "/" + str(total_targets_and_hosts) + ") " + \
              str(round((targets_scanned/float(total_targets_and_hosts))*100, 1)) + "% completed"
print "[+] Nmap-Tor-Scanner exiting"
