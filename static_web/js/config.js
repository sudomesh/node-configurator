/*

  This is the javascript library for the 
  sudomesh node configuration web app.

  License: AGPL

*/


var NodeConf = {

    config_file: 'static/config/common.json',
    websocket_uri: null,
    last_timer: null,
    CONST_INTERVAL_MS: 5000,
    sock: null,
    node_template: null,
    nodes: [], // connected nodes

    init: function() {
        this.load_config();
    },

    init_continued: function() {

        this.sock = new WebSocket(this.websocket_uri);
        this.node_template = _.template($('#node_template').html());

        console.log("mesh the planet!");
  
        this.sock.onopen = function() {
            console.log("connected to " + this.websocket_uri);
        }.bind(this);
 
        this.sock.onclose = function(e) {
            console.log("connection closed (" + e.code + ")");
        }.bind(this);
  
        this.sock.onmessage = function(e) {
            console.log("message received: " + e.data);
            var msg = $.parseJSON(e.data);
            if(!msg) {
                return false;
            }
            switch(msg.type) {
                
            case 'node_appeared':
                if(!msg.data) {
                    return false;
                }
                this.add_node(msg.data);
                break;
                
            case 'node_disappeared':
                this.remove_node(msg.data);
                break;
            default:
                console.log("unknown message type received: "+ msg.type);
            }
        }.bind(this);
    },

    load_config: function() {
        $.get(this.config_file, '', function(data, status) {
            console.log("data: " + data.protocol);
            this.config = data;
            var port = '';
            // if non-standard port
            // specify port in websocket uri
            if(((window.location.protocol == 'http:') && (parseInt(window.location.port) != 80)) || ((window.location.protocol == 'https:') && (parseInt(window.location.port) != 443))) {
                port = ':'+window.location.port;
            }
            // use ssl for websockets if using https
            var websocket_protocol = 'ws';
            if(window.location.protocol == 'https:') {
                websocket_protocol = 'wss';                
            };

            // build websocket uri
            this.websocket_uri = websocket_protocol + '://' + window.location.hostname + port + this.config.server.websocket_path;
            this.init_continued();
        }.bind(this));

    },
    
    // generate id from mac address
    mac_to_id: function(mac) {
        return 'node-'+mac.replace(/:/g, '-');
    },

    add_node: function(node) {
        node.id = this.mac_to_id(node.mac_addr);
        node.title = node.system_type;
        node.status = 'unconfigured';


        var h = this.node_template(node)
        var container = $('#node_list');
        if(this.nodes.length <= 0) {
            container.html('');
        }
        container.append(h);
        this.nodes.push(node);
    },

    remove_node: function(node) {
        console.log("removing node: #" + node.mac_addr);
        $('#'+this.mac_to_id(node.mac_addr)).remove();
        var i, cur;
        // remove from node array
        for(i=0; i < this.nodes.length; i++) {
            cur = this.nodes[i];
            if(cur.mac_addr == node.mac_addr) {
                this.nodes.splice(i, 1);
                break;
            }
        }
        if(this.nodes.length <= 0) {
            $('#node_list').html("<p>No nodes connected.<p>");
        }
    },

    // TODO unused
    update_node_list: function(nodes) {

        var container = $('#node_list');
        if(nodes.length <= 0) {
            container.html("<p>No nodes connected.<p>");
        } else {
            container.html('');
        }
        var i, h;
        for(i=0; i < nodes.length; i++) {
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