#!/usr/bin/env python3

import shelve
import subprocess
import sys
import json
import requests
import socket
import argparse

def gen_wg_conf(data):
  def gen_peer(peer):
    peer["psk"]=peer["encrypted_psk"]
    
    peer_config=f"""
[Peer]
# peer {peer["id"]}, {peer["hostname"]}
PublicKey={peer["pubkey"]}
PresharedKey={peer["psk"]}
AllowedIPs={", ".join(peer["allowedips"])}
"""
    if peer["endpoint"]:
      peer_config+=f'Endpoint={peer["endpoint"]}\n'
    if peer["keepalive"]:
      peer_config+=f'PersistentKeepalive={peer["keepalive"]}\n'
    peer_config += "\n"
    return peer_config
  
  wgconfig=f"""
[Interface]
# peer {config["id"]}
Address={data["interface"]["address"]}
PrivateKey={config["privkey"]}

"""
  for peer in data["peers"]:
    wgconfig += gen_peer(peer)
  return wgconfig

def gen_vyos_conf(data):
  def gen_peer(peer):
    peer["psk"]=peer["encrypted_psk"]
    
    peer_config=f"""
set peer {peer["hostname"]} public-key {peer["pubkey"]}
set peer {peer["hostname"]} preshared-key {peer["psk"]}
"""
    for ip in peer["allowedips"]:
      peer_config += f'set peer {peer["hostname"]} allowed-ips {ip}\n'
    if peer["endpoint"]:
      peer_config += f'set peer {peer["hostname"]} endpoint {peer["endpoint"]}\n'
    if peer["keepalive"]:
      peer_config += f'set peer {peer["hostname"]} persistent-keepalive {peer["keepalive"]}\n'
    return peer_config
  wgconfig=f"""
set address {data["interface"]["address"]}
set private-key {config["privkey"]}
"""
  for peer in data["peers"]:
    wgconfig += gen_peer(peer)
  return wgconfig
    

def register(config, endpoint, server):
  config["server"]=server
  # Generate WireGuard private key
  privkey = subprocess.check_output(['wg', 'genkey']).strip()
  config['privkey'] = str(privkey)
  pubkey = subprocess.check_output(['wg', 'pubkey'], input=privkey).strip()

  hostname = socket.gethostname()

  data = {
      'hostname': hostname,
      'pubkey': pubkey.decode(),
      'endpoint': endpoint
  }

  r = requests.post(f'{server}/host/register', data=json.dumps(data), headers={'Content-Type': 'application/json'}).json()
  if r["status"] == "pending":
    config["id"]=r["id"]
  else:
    print(r)

parser = argparse.ArgumentParser(description='Wireguard config client')

# Add the subparsers for the different commands
subparsers = parser.add_subparsers(dest='command')

# Add the 'register' command and its arguments
register_parser = subparsers.add_parser('register', help='Register this peer to the Wireguard config server')
register_parser.add_argument('endpoint', type=str, help='The endpoint to be used by other peers, or "NAT" if this host is behind a NAT.')
register_parser.add_argument('--server', type=str, default="http://localhost:5000", help='The server to register this peer with')

# Add the 'genconf' command and its arguments
genconf_parser = subparsers.add_parser('genconf', help='Generate Wireguard configuration')
genconf_parser.add_argument('--format', type=str, choices=['wg', 'vyos'], default='wg', help='The format of the generated configuration')

# Parse the arguments
args = parser.parse_args()

config = shelve.open('wgconf.bin')

# Call the appropriate method based on the command
if args.command == 'register':
    register(config, args.endpoint, args.server)
elif args.command == 'genconf':
    r=requests.get(f"{config['server']}/host/config/{config['id']}").json()
    if r["status"] != "ok":
      print(r)
    elif args.format == 'wg':
        print(gen_wg_conf(r))
    elif args.format == 'vyos':
        print(gen_vyos_conf(r))
  
config.close()
