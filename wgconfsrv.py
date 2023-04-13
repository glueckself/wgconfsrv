#!/usr/bin/env python3

import uuid
import secrets
import base64
import shelve

from flask import Flask, request, jsonify, make_response

config = shelve.open('wgconfsrv.bin')
if "pending_peers" in config:
    pending_peers=config["pending_peers"]
else:
    pending_peers = dict()
    
if "peers" in config:
    peers = config["peers"]
else:
    peers = dict()

app = Flask(__name__)

@app.route('/host/register', methods=["POST"])
def host_register():
    params = request.get_json()
    for param in ["hostname", "pubkey", "endpoint"]:
        if param not in params:
            return make_response(jsonify({"status": "error", "message": f"Missing value {param} in submitted json"}), 400)
    
    host_uuid = str(uuid.uuid4())
    pending_peers[host_uuid] = params
    return jsonify({"status": "pending", "id": host_uuid})

def peer_to_config(uuid, peer_uuid):
    return {
        "id": peer_uuid,
        "hostname": peers[peer_uuid]["hostname"],
        "pubkey": peers[peer_uuid]["pubkey"],
        "encrypted_psk": peers[uuid]["peers"][peer_uuid],
        "endpoint": peers[peer_uuid]["endpoint"],
        "keepalive": 25 if not peers[uuid]["endpoint"] else 0,
        "allowedips": [f'{peers[peer_uuid]["address"]}/32'] + (peers[peer_uuid]["networks"] if peers[peer_uuid]["networks"] else list())
    }

@app.route('/host/config/<uuid>', methods=["GET"])
def host_get_config(uuid):
    if uuid in pending_peers:
        return jsonify({"status": "pending"})
    
    if not uuid in peers:
        return make_response(jsonify({"status": "error", "message": "Unknown host"}), 404)
    
    result = dict()
    result["status"] = "ok"
    result["interface"] = {"address": f'{peers[uuid]["address"]}/24', "mtu": 1500}
    result["peers"] = [peer_to_config(uuid, peer) for peer in peers[uuid]["peers"]]
    return jsonify(result)
    
def peer_to_mgmt(uuid, peer, pending):
    return {
        "id": uuid,
        "status": "pending" if pending else "accepted",
        "address": "" if pending else peer["address"],
        "networks": [] if pending else peer["networks"],
        "hostname": peer["hostname"],
        "endpoint": peer["endpoint"] if peer["endpoint"] else "NAT",
        "peers": list() if pending else [peer_uuid for peer_uuid in peer["peers"]]
    }

@app.route('/mgmt/peers', methods=["GET"])
def mgmt_get_peers():
    result = [peer_to_mgmt(uuid, peer, pending=True) for uuid, peer in pending_peers.items()]
    result += [peer_to_mgmt(uuid, peer, pending=False) for uuid, peer in peers.items()]
    return jsonify({"peers": result})

def gen_psk():
    psk = secrets.token_bytes(32)
    return  base64.b64encode(psk).decode('ascii')

def encrypt_psk(psk, pubkey):
    return psk

def connect_peers(uuid, peers_list):
    failed = list()
    for peer_uuid in peers_list:
        if not peer_uuid in peers:
            failed.append(peer_uuid)
            continue
        if not peer_uuid in peers[uuid]["peers"]:
            psk = gen_psk()
            peers[uuid]["peers"][peer_uuid] = encrypt_psk(psk, peers[uuid]["pubkey"])
            peers[peer_uuid]["peers"][uuid] = encrypt_psk(psk, peers[peer_uuid]["pubkey"])
    
    for peer_uuid in peers[uuid]["peers"]:
        if not peer_uuid in peers_list:
            peer[uuid]["peers"].pop(peer_uuid)
            peer[peer_uuid]["peers"].pop(uuid)

@app.route('/mgmt/<uuid>/connect', methods=["POST"])
def mgmt_connect_peers(uuid):
    params = request.get_json()
    failed = connect_peers(uuid, params["peers"])
    if failed:
        return make_response(jsonify({"status": "error", "message": f"Failed to connect peers: {failed}"}), 400)
    else:
        return jsonify({"status": "ok"})

@app.route('/mgmt/<uuid>', methods=["POST"])
def mgmt_config_peer(uuid):
    params = request.get_json()
    if uuid in pending_peers:
        peer = pending_peers.pop(uuid)
        if params["action"] != "accept":
            return jsonify({"status": "rejected", "id": uuid})
            
        if peer["endpoint"] in ["nat", "NAT"]:
            peer["endpoint"] = None
        
        peer["address"]=params["address"]
        peer["peers"] = dict()
        peer["networks"] = params["networks"] if "networks" in params else list()
        peers[uuid] = peer
        failed = connect_peers(uuid, params["peers"])
        if failed:
            return make_response(jsonify({"status": "error", "message": f"Failed to connect peers: {failed}"}), 400)
        else:
            return jsonify({"status": "ok"})
    
    if uuid in peers:
        if params["action"] == "delete":
            peers.pop(uuid)
            return jsonify({"status": "ok"}) 
        elif params["action"] == "modify":
            if "address" in params:
                peers[uuid]["address"]=params["address"] 
            if "networks" in params:
                peers[uuid]["networks"] = params["networks"]
            if "peers" in params:
                failed = connect_peers(uuid, params["peers"])
                if failed:
                    return make_response(jsonify({"status": "error", "message": f"Failed to connect peers: {failed}"}), 400)
            return jsonify({"status": "ok"})
    
    return make_response(jsonify({"status": "error", "message": "Peer not found"}), 404)

if __name__ == '__main__':
    app.run()
    # FIXME: this doesn't work with gunicorn
    config["peers"]=peers
    config["pending_peers"]=pending_peers
    config.close()
