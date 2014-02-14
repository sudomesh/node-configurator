/*

  This is the javascript library for the 
  sudomesh node configuration web app.

  License: AGPL

*/

// TODO move to utils js file
$.fn.serializeObject = function()
{
    var o = {};
    var a = this.serializeArray();
    $.each(a, function() {
        if (o[this.name] !== undefined) {
            if (!o[this.name].push) {
                o[this.name] = [o[this.name]];
            }
            o[this.name].push(this.value || '');
        } else {
            o[this.name] = this.value || '';
        }
    });
    return o;
};


var NodeConf = {

    name: "Node Configurator",
    config_file: 'static/config/server.json',
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

        console.log("Connecting to websocket uri: " + this.websocket_uri);
        this.sock = new WebSocket(this.websocket_uri);
        this.node_template = _.template($('#node_template').html());
        this.node_form_template = _.template($('#node_form_template').html());

        console.log(this.name+" initializing");

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

            case 'node_status':
                this.update_node_status(msg.data);
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
            this.websocket_uri = websocket_protocol + '://' + window.location.hostname + port + this.config.websocket_path;
            this.init_continued();
        }.bind(this));

    },
    
    // generate id from mac address
    mac_to_id: function(mac) {
        return 'node-'+mac.replace(/:/g, '-');
    },

    update_node_status: function(data) {
        if(data.cmd_output) {
            // exit code is appended to output
            // split it here
            var lines = data.cmd_output.split("\n");
            var line = lines.pop();
            if(line == '') {
                line = lines.pop();
            }
            data.exit_code = parseInt(line)
            data.cmd_output = lines.join("\n");
        }

        if(data.status == 'success') {
            $('#flash')[0].innerHTML += "<p>Node successfully configured. Rebooting node.</p>";
        } else {
            $('#flash')[0].innerHTML += "<p>Error running command on node: " + data.cmd_output + "</p>";
            console.log("Exit code: " + data.exit_code);
        }
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
        h = container.find('.node:last-child');
        h.click(this.node_selected.bind(this));
        h[0].node = node;

        this.nodes.push(node);
    },

    node_selected: function(e) {
        var el = $(e.target).closest('.node');
        this.show_form_for_node(el);
        e.stopPropagation();
        e.preventDefault();
        return false;
    },

    show_form_for_node: function(el) {
        if(el.length <= 0) {
            console.log("Could not find node data for element");
            return false;
        }
        $('#node_list .node').removeClass('selected');
        el.addClass('selected');
        var node = el[0].node;
        var saved_conf = $.cookie(node.mac_addr);
        if(saved_conf) {
            node.conf = JSON.parse(saved_conf);
        } else {
            node.conf = node.conf || {};
        }
        var h = this.node_form_template(node)
        $('#right_pane').html(h);
        var form = $('#right_pane .node_info_form');
        form.change(this.form_changed.bind(this));
        form.submit(this.form_submit.bind(this));

        this.stickerGen = new StickerGenerator(336, 873, 'stickerPreview');

        $('#btn_gen_ssid').click(function(e) {
            e.stopPropagation();
            e.preventDefault();
            $.post('/get-ssid', function(data, textStatus) {
                var msg = JSON.parse(data);
                if(msg.status != 'success') {
                    console.log("Error getting SSID: " + data);
                    return;
                }
                $('#private_wifi_ssid').val(msg.ssid);
                this.form_changed();
            }.bind(this));
            return false;
        }.bind(this));

        $('#btn_print_sticker').click(function(e) {
            e.stopPropagation();
            e.preventDefault();
            this.stickerGen.toRotatedDataURL(function(dataURL) {
                var msg = {image: dataURL};
                
				        $.post('/print-sticker',
					             JSON.stringify(msg), 
                       function(data) {
                           console.log("sticker sent to server for printing");
                       }, 
                       'json');

            });
        }.bind(this));
    },

    form_submit: function(e) {
        var form = $(e.target).closest('form');
        
        var msg = {
            type: 'node_config',
            data: form.serializeObject()
        };
        
        $.post('configure', JSON.stringify(msg), this.submit_callback.bind(this));
        $('#loading').css('display', 'block');

        e.stopPropagation();
        e.preventDefault();
        return false;
    },
    
    submit_callback: function(msg_str, textStatus) {
        $('#loading').css('display', 'none');
        // TODO report actual success or failure
        var msg = $.parseJSON(msg_str);
        if(!msg || (msg.status != 'success')) {
            $('#flash').html("<p>Error: " + msg.error + "</p>");
            return false;
        }
        $('#flash').html("<p>Node configuration sent. Node will configure itself and reboot.</p>");

        if(msg.node_config) {
            $('#flash')[0].innerHTML += "<p>Generating sticker.</p>";
            
            this.stickerGen.draw(msg.node_config);
            $('#flash')[0].innerHTML += "<p>root password (not included on sticker) is: "+msg.node_config.root_password+"</p>";
        } else {
            $('#flash')[0].innerHTML += "<p>Node configuration was not received. Cannot generate sticker :(</p>";
        }

    },

    form_changed: function(e) {
        var o = $('#right_pane .node_info_form').serializeObject();
        $.cookie(o.mac_addr, JSON.stringify(o), {expires: 7});
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
    }
};

$(document).ready(NodeConf.init.bind(NodeConf));