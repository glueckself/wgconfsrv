# wgconfsrv
Wireguard config server

This is a flask service, that allows managing Wireguard configurations for multiple peers from a single web application/API.

Right now the code is very bare-bones ("proof of concept"), before any serious usage, this needs at least authentication and better storage (at least a sqlite db on the server). Also, see security discussion below.

The reason of this project is to reduce the amount of copying/pasting config snippets, pubkeys and preshared keys when adding a new peer to a fully/partially meshed Wireguard network.

## Server
The server is in wgconfsrv.py. (TODO: start via gunicorn). No further configuration necessary.
The server provides an API for the peers and for management. See brainstorming.txt for the API.
It also provides a simple web interface at `/static/index.html`, where peers can be viewed and accepted/deleted.

Peer configuration is partially possible (only when accepting a pending peer).

Peer's can only be paired via the API right now, not via the interface.

## Client
The client is in wgconfclient.py. This is run on each Wireguard peer that should be managed.

1) The peer needs to be registered: `./wgconfclient.py register --server <wgconfsrv address> <endpoint>`, where `<endpoint>` is either "ip/hostname:port", that other peers should use in their configs, or "nat" if this peer has no public IP address.
2) The peer needs to be accepted on the server (either via web interface or via raw API).
3) The peer needs to be paired with other peers (this step can only be done from two peers onwards and currently only via raw API).
4) `./wgconfclient.py genconf` on the peer generates the config and prints it on stdout. It needs to be scripted to update the conf file in /etc/wireguard and reload the interface.

# Security discussion
If this service is used automatically (e.g. genconf via crontab), it becomes the weakest link in the chain. If someone can modify the stored peers (right now, anyone with TCP/IP access can!), they can inject their pubkey/endpoint and MITM the Wireguard connection.

The only way to mitigate this, is to review the changes on the peers before syncing the wireguard conf.
