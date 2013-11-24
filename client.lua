#!/usr/bin/env lua

require("socket")
require("ssl")
require("string")
json = require("dkjson-min")

config_file_path = "config/common.json"

config = nil

--[[

  This program is in its early stages.

  The idea is that it will be auto-started on nodes
  when they boot after being flashed with the sudomesh
  firmware.

  The purpose of the script is to:

    1. Locate a node configuration server on the LAN
       connected to the ethernet interface using
       DNS-SD (using the mdnsd daemon).

    2. Connect to the node configuration server
       using SSL and verifying that it is trusted.

    3. Announce the node's MAC address to the server

    4. Await configuration from the server in the form
       of one or more ipkg packages.

    5. Verify and install the ipkg packages.

    6. Report install success / failure to the server.

    7. Disable autostart of this script and reboot.

  This script still needs:

    * A separate config file
    * To use DNS-SD to find the node conf server.
    * Ability to receive more than one file
    * To run md5sum to verify recevied files
    * To install packages after they are received.
    * To report status back to server and reboot
    * Sane maximum caps on received files
    * and more...

--]]


function sanitize_filename(filename)
  return string.gsub(filename, "[^-%a%d_\.]", '')
end

function fail(err_msg)
  print("[Error] "..err_msg)
  os.exit(-1);
end

function connect(ip, port)

  -- TLS/SSL client parameters (omitted)
  local params

  local conn = socket.tcp()
  conn:connect(ip, port)

  local params = {
    mode = "client",
    protocol = "tlsv1",
  --  capath = "/etc/ssl/certs",
    cafile = "certs/ca_root.crt",
  -- key = "/etc/certs/clientkey.pem",
  --  certificate = "/etc/certs/client.pem",
    verify = "peer",
    options = "all"
  }

  -- TLS/SSL initialization
  conn = ssl.wrap(conn, params)
  conn:dohandshake()

  return conn
end

function receive_and_write(conn, file_name, file_size)
  local f
  local data, err
  local to_read
  local count = 0

  f, err = io.open(file_name, 'w+b')
  if not f then
    return nil, err
  end

  while count < file_size do
    if (file_size - count) < 4096 then
      to_read = file_size - count
    else
      to_read = 4096
    end

    data, err = conn:receive(to_read)
    if not data then
      return nil, err
    end
    count = count + to_read

    f:write(data)
  end

  io.close(f)
end

function load_config()
  local f = io.open(config_file_path)
  local data = f:read("*all")
  config = json.decode(data)
  io.close()
end

-- called when a configure msg and its associated
-- file has been successfully received
function configure_receive_completed(msg)
  -- TODO implement this
  print("Received the file: " .. msg['data']['file_name'])
end

-- keep receiving and handling received data
function handle_receive(c)
  local state = 'WAITING'
  local line
  local data
  local msg
  local err
  local file = nil
  
  while true do
    if state == 'WAITING' then
      line, err = c:receive("*l")
      if line == nil then
        if err ~= 'closed' then
          io.stderr:write("Socket error: " .. err)
        end
        break
      end

      msg = json.decode(line)
      if msg == nil then
        io.stderr:write("Received invalid json")
        break
      end

      if msg['type'] == 'configure' then
         print("configure message received")
         file, err = io.open(msg['data']['file_name'], 'w+b')
         if not file then
           io.stderr:write("Could not create file: \"" .. msg['data']['file_name'] .. "\" Error: " .. err)
           break
         end
         state = 'RECEIVING_FILE'
      else
        io.stderr.write("Unknown message type")
      end

    elseif state == 'RECEIVING_FILE' then
      data, err, partial = c:receive(8192)
      if data == nil then
         if partial then
           file:write(partial)
         end
         file:close()
         configure_receive_completed(msg)
         return true
      end
      file:write(data)
    else
      io.stderr.write("Got into unknown state")
      return false
    end
  end
end

function begin_connection(ip, port)

  local c

  print("connecting to "..ip..":"..port)
  c = connect(ip, port)

  if not c then
     print("Failed to connect")
     conn:close()
     os.exit(-1);
  end

  -- send node info to server
  local node_info_msg = build_node_info_msg()
  c:send(node_info_msg)

  -- begin handling incoming data
  handle_receive(c)

  c:close()
end

function find_server_and_connect()

  local mdns
  local line
  local hostname
  local ip
  local port

--TODO this is a temporary thing for development
  begin_connection("127.0.0.1", 1337)

--[[
  mdns = io.popen(config.utils.mdnssd_min..' '..config.server.service_type, 'r')

-- TODO support connecting to multiple servers
  while true do
    line = mdns:read("*line")
    if line == nil then
      break
    end
    hostname, ip, port = string.match(line, "(.+)%s+(.+)%s+(.+)")
--    print("host: "..hostname.." | ip: "..ip.." | port: "..port)
    if hostname ~= nil and ip ~= nil and port ~= nil then
      begin_connection(ip, port)
        mdns:close()
      return true
    end
  end
  mdns:close()
  return false
--]]
end

function get_node_mac()

  local f
  local line

  f = io.popen("ip addr show scope link dev wlan0|grep link", 'r')
  line = f:read("*line")
  f:close()
  if line == nil then
    return false
  end

  mac = string.match(line, "(%w%w:%w%w:%w%w:%w%w:%w%w:%w%w)")

  return mac
end


function get_system_type()

  local f
  local line

  f = io.popen("cat /proc/cpuinfo | grep 'system type'", 'r')
  line = f:read("*line")
  f:close()
  if line == nil then
    f = io.popen("cat /proc/cpuinfo | grep 'model name'", 'r')
    line = f:read("*line")
      f:close()
      if line == nil then
         return false
      end
  end

  system_type = string.match(line, ":%s+(.+)")

  -- remove multiple spaces
  system_type = string.gsub(system_type, "%s+", " ")

  return system_type
end

-- build json identifying this node
function build_node_info_msg() 

  local o = {}

  o['type'] = "node_appeared"
  o['data'] = {}
  o['data']['mac_addr'] = get_node_mac()
  o['data']['system_type'] = get_system_type()

  return json.encode(o).."\n"
end


load_config()

--mac_addr = get_node_mac()
--print("MAC: "..mac_addr)

--system_type = get_system_type()
--print("System: "..system_type)

find_server_and_connect()



