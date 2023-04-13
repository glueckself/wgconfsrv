var peersData;

function buildTable(data) {
  var table = $('#peersTable tbody');
  table.empty();
  for (var i = 0; i < data.length; i++) {
    var peer = data[i];
    var networks = peer.networks.join(", ");
    var peers = peer.peers.map(function(id) { return findPeer(id).hostname; }).join(", ");
    var row = '<tr>' +
      '<td>' + peer.hostname + '</td>' +
      '<td>' + peer.endpoint + '</td>' +
      '<td><input type="text" id="address_' + peer.id +'" value="' + peer.address + '"/></td>' +
      '<td><input type="text" id="networks_' + peer.id + '" value="' + networks + '"/></td>' +
      '<td>' + peers + '</td>' +
      '<td>' + peer.status + '</td>' +
      '<td>' +
        '<button onclick="acceptPeer(\'' + peer.id + '\')">Accept</button>' +
        '<button onclick="deletePeer(\'' + peer.id + '\')">Delete</button>' +
      '</td>' +
      '</tr>';
    table.append(row);
  }
}

function findPeer(id) {
  for (var i = 0; i < peersData.length; i++) {
    if (peersData[i].id === id) {
      return peersData[i];
    }
  }
  return null;
}

function getPeers() {
  $.ajax({
    url: '/mgmt/peers',
    method: 'GET',
    success: function(data) {
      peersData = data.peers;
      buildTable(peersData);
    },
    error: function() {
      alert('Failed to get peers');
    }
  });
}

function acceptPeer(id) {
  $.ajax({
    url: '/mgmt/' + id,
    method: 'POST',
    data: JSON.stringify({
      action: 'accept',
      networks: $('#networks_'+id).val().split(","),
      address: $('#address_'+id).val(),
      peers: []
    }),
    contentType: 'application/json',
    success: function() {
      getPeers();
    },
    error: function() {
      alert('Failed to accept peer');
    }
  });
}

function deletePeer(id) {
  $.ajax({
    url: '/mgmt/' + id,
    method: 'POST',
    data: JSON.stringify({ action: 'delete' }),
    contentType: 'application/json',
    success: function() {
      getPeers();
    },
    error: function() {
      alert('Failed to delete peer');
    }
  });
}

$(document).ready(function() {
  getPeers();
});
