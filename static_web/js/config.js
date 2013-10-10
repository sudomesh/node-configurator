$(document).ready(function() {
  console.log("mesh the planet!");
  
  var sock = null;
  var wsuri = "ws://localhost:9000";
  
  sock = new WebSocket(wsuri);
  
  function send(msg) {
    sock.send(msg);
  };
  
  sock.onopen = function() {
    console.log("connected to " + wsuri);
  }
 
  sock.onclose = function(e) {
    console.log("connection closed (" + e.code + ")");
  }
  
  sock.onmessage = function(e) {
    console.log("message received: " + e.data);
  }
});