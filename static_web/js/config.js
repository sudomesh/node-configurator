var CONST_INTERVAL_MS = 5000;

var last_timer;
var wsuri = "wss://localhost:8080/websocket";
var sock = new WebSocket(wsuri);

function update_node_list(data) {
    var node = data.node_obj;
    var outer = document.createElement('DIV');
    outer.id = 'node_0';
    outer.className = 'node';
    var sub = document.createElement('DIV');
    sub.className = 'title';
    sub.innerHTML = node.hardware_model || "Unknown";
    outer.appendChild(sub);

    sub = document.createElement('DIV');
    sub.className = 'MAC';    
    var subsub = document.createElement('SPAN');
    subsub.className = 'label';
    subsub.innerHTML = "MAC:";
    sub.appendChild(subsub);
    subsub = document.createElement('SPAN');
    subsub.className = 'text';
    subsub.innerHTML = "C0:DE:CA:FE:C0:CA:FE";
    sub.appendChild(subsub);
    outer.appendChild(sub);

    sub = document.createElement('DIV');
    sub.className = 'status';    
    var subsub = document.createElement('SPAN');
    subsub.className = 'label';
    subsub.innerHTML = "Status::";
    sub.appendChild(subsub);
    subsub = document.createElement('SPAN');
    subsub.className = 'text';
    subsub.innerHTML = "Unconfigured";
    sub.appendChild(subsub);
    outer.appendChild(sub);

    $('#node_list').html('');
    $('#node_list')[0].appendChild(outer);
}
  
function send_command() {
  fakeNode = {
    "hardware_model"   : "Ubiquity nano-station",
    "firmware_version" : "SudoNode v0.5",
    "geo_location"     : "Oakland, CA",
    "op_name"          : "A Cool Person",
    "op_email"         : "coolpeer@idk.org",
    "op_phone"         : "1-555-555-1337"
  };
  
  fakeCommand = {
    "command"   : "node::set_config",
    "socket_id" : Math.floor(Math.random() * 100),
    "node_obj"  : fakeNode
  };
  
  sock.send(JSON.stringify(fakeCommand));
}

$(document).ready(function() {
  console.log("mesh the planet!");
  
  sock.onopen = function() {
    console.log("connected to " + wsuri);
  }
 
  sock.onclose = function(e) {
    console.log("connection closed (" + e.code + ")");
  }
  
  sock.onmessage = function(e) {
    console.log("message received: " + e.data);
      var data = $.parseJSON(e.data);
    update_node_list(data);

//    send_command();
  }
});