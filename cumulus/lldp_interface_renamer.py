#!/usr/bin/env python
#
#  SCRIPT NAME:
#    lldp_interface_renamer.py
#  PURPOSE:
#    This script renames physical interfaces with their current lldp neighbor
#  METHOD:
#    The script will: 
#      - Delete all pending changes in the config vis 'net abort' for safety
#      - Get a list of all physical ints, and delete any current aliases on them
#      - Get a list of lldp neighbors, and set the alias on the respective port
#      - Do a 'net commit'
#    This script should probably be called via a cron job by a user that has netedit access.

import subprocess
import json

# Do a 'net abort' to clear out all pending config changes, for safety
subprocess.call(["net", "abort"])

# Get a list of all the interfaces on this switch in json format
iflistcmd = ["net", "show", "interface", "alias", "json"]
iflist_retout = subprocess.check_output(iflistcmd)
iflist_json_out = json.loads(iflist_retout)

# Remove the bridge, lo, uplink, peerlink, mgmt, and interfaces from the list
ignore_these = ['bridge', 'lo', 'uplink', 'uplinks', 'peerlink', 'mgmt']
[iflist_json_out.pop(key, None) for key in ignore_these]

# Remove any manually configured interfaces that start with the word 'host' or 'peer' from the blanking list
for key in iflist_json_out.keys():
    if key.startswith('host') or key.startswith('peer'):
        iflist_json_out.pop(key, None)

# Delete aliases from all remaining interfaces (should only be swp's now)
for key in iflist_json_out.keys():
    subprocess.call(["net", "del", "interface", key, "alias"])

# Get all the lldp neighbor info in json format
lldpcmd = ["/usr/bin/net", "show", "lldp", "json"]
lldp_retout = subprocess.check_output(lldpcmd)
lldp_json_out = json.loads(lldp_retout)

# Step through the LLDP json and set a new alias for ports that have lldp neighbors
lldp_ifs = [i for i in lldp_json_out["lldp"][0]["interface"]]
for interface in lldp_ifs:
    neighbor = interface["chassis"][0]["name"][0]["value"]
    local_interface = interface["name"]
    neighbor_interface = interface["port"][0]["id"][0]["value"]
    subprocess.call(["net", "add", "interface", local_interface, "alias", '"to', neighbor, "- port", neighbor_interface + '"'])

# Commit the changes if there are any actual alias changes. If not, abort for good measure.
pending = subprocess.Popen(["/usr/bin/net", "pending"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
stdout, stderr = pending.communicate()
if ("+++ /run/nclu/ifupdown2/interfaces.tmp" in stdout):
    subprocess.call(["/usr/bin/net", "commit"])
else:
    subprocess.call(["/usr/bin/net", "abort"])
