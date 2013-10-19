/*

  This is the javascript library for the 
  sudomesh node configuration web app.

  License: AGPL

*/


var NodeConf = {

    wsuri: "wss://localhost:8080/websocket",
    last_timer: null,
    CONST_INTERVAL_MS: 5000,
    sock: null,
    node_template: null,

    init: function() {

        this.sock = new WebSocket(this.wsuri);
        this.node_template = _.template($('#node_template').html());

        console.log("mesh the planet!");
  
        this.sock.onopen = function() {
            console.log("connected to " + this.wsuri);
        }.bind(this);
 
        this.sock.onclose = function(e) {
            console.log("connection closed (" + e.code + ")");
        }.bind(this);
  
        this.sock.onmessage = function(e) {
            console.log("message received: " + e.data);
            var data = $.parseJSON(e.data);
            // TODO fix
            data = [data];
            this.update_node_list(data);
        }.bind(this);
    },
    
    update_node_list: function(nodes) {

        var container = $('#node_list');
        var i, h;
        for(i=0; i < nodes.length; i++) {
            // TODO fix
            nodes[i].id = 'node_'+i;
            nodes[i].title = nodes[i].hardware_model;
            nodes[i].status = 'unconfigured';
            nodes[i].mac = 'C0:DE:CA:FE:C0:DE:CA:FE';
            h = this.node_template(nodes[i]);
            container.append(h);
        }
    },

    send_command: function() {
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
};

$(document).ready(NodeConf.init.bind(NodeConf));