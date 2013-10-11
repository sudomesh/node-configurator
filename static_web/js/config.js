var CONST_INTERVAL_MS = 5000;

var last_timer;
var wsuri = "ws://localhost:9000";
var sock = new WebSocket(wsuri);
  
function send_action() {
  fakeNode = {
    "hardware_model"   : "Ubiquity nano-station",
    "firmware_version" : "SudoNode v0.5",
    "geo_location"     : "Oakland, CA",
    "op_name"          : "A Cool Person",
    "op_email"         : "coolpeer@idk.org",
    "op_phone"         : "1-555-555-1337"
  };
  
  fakeAction = {
    "action"   : "node::set_config",
    "node_id"  : Math.floor(Math.random() * 100),
    "node_obj" : fakeNode
  };
  
  sock.send(JSON.stringify(fakeAction));
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
    send_action();
  }
});