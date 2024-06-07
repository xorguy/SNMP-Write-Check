#!/usr/bin/env python3

import sys
import re
import shlex
import subprocess
from subprocess import PIPE

# Debug flag
debug = False
show_tested_oids = False

# Display help 
if len(sys.argv) == 1 or sys.argv[1].lower() == "-h" or sys.argv[1].lower() == "--help":
    usage = {}
    usage["desc"] = """Returns the number of writable OIDs and lists them.
Parses the output of 'snmpwalk' and determines all elements that are readable. The return code of 'snmpset' is used to determine if an element's value can be written, by performing a write with the exact actual value.
"""
    usage["cmd"] = f"Syntax:\t{sys.argv[0]} [OPTIONS] AGENT [BASE_OID] [--show-tested-oids] #see man snmpcmd"
    usage["example"] = f"Example: {sys.argv[0]} -v 2c -c public 192.168.0.3 .1.3.6.1.2.1 --show-tested-oids"
    usage["disclaimer"] = """
DISCLAIMAR: The script might change the value of the writable or cause other effects. Use with care.
"""
    print("\n".join(usage.values()))
    sys.exit(0)

# Parse the command line arguments
options_agent = ' '.join(arg for arg in sys.argv[1:] if not arg.startswith('--'))
show_tested_oids = '--show-tested-oids' in sys.argv

# Optional base OID
base_oid = sys.argv[-1] if sys.argv[-1].startswith('.') else ''

cmd = f"snmpwalk -ObentU {options_agent} {base_oid}"
args = shlex.split(cmd)
proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
out = proc.stdout.read().decode()

if(debug):
    print(f"{cmd}\n{out}\n\n")

# Map between snmpwalk output and expected type by snmpset
type_map = {
    "INTEGER": 'i', "unsigned INTEGER": 'u', "UNSIGNED": 'u', "TIMETICKS": 't', 
    "Timeticks": 't', "IPADDRESS": 'a', "OBJID": 'o', "OID": 'o', "STRING": 's', 
    "HEX STRING": 'x', "Hex-STRING": 'x', "DECIMAL STRING": 'd', "BITS": 'b', 
    "unsigned int64": 'U', "signed int64": 'I', "float": 'F', "double": 'D', 
    "NULLOBJ": 'n'
}

# Count how many OIDs are writable
count = 0

# Iterate and parse each OID
for line in out.splitlines():
    try:
        oid = line.split(" = ")[0]
        type_value = line.split(" = ")[1]
        type_ = type_map[type_value.split(": ")[0]]  # ex: STRING: "abc"
        value = type_value.split(": ")[1]

        # Display the OID being tested if the flag is set
        if show_tested_oids:
            print(f"Testing OID: {oid}")

        # For TIMETICKS extract only the numeric value
        if type_ == 't':
            match = re.search(r'\((.+?)\)', value)
            if match:
                value = match.group(1)
            else:
                continue
        # For HEX STRING put the value in quotes
        if type_ == 'x':
            value = f'"{value}"'

        # Try to write the existing value once again        
        cmd = f"snmpset {options_agent} {oid} {type_} {value}"
        args = shlex.split(cmd)
        if(debug):
            print(cmd)
            retcode = subprocess.call(args)
        else:
            retcode = subprocess.call(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
        if retcode == 0:
            cmd_get = f"snmpget {options_agent} {oid}"
            args_get = shlex.split(cmd_get)
            oidtype = subprocess.run(args_get, stdout=subprocess.PIPE).stdout.decode('utf-8')
            m = re.search('=', oidtype)
            oidtype_s = oidtype[m.end():]
            print(f"{oid} is writable - {oidtype_s.strip()}")
            count += 1
    except Exception as e:
        if debug:
            print(f"Error processing {line}: {e}")

# Return code is the number of found OIDs
sys.exit(count)