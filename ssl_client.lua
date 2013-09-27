#!/usr/bin/env lua

require("socket")
require("ssl")
require("string")

--[[

  This program is in the early stages.

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

function connect()

  -- TLS/SSL client parameters (omitted)
  local params

  local conn = socket.tcp()
  conn:connect("nodeconf.local", 8000)


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

--[[

File data has the following format:

FILE:<filename_length>:<filename>:<md5_checksum_of_file>:<file_length_in_bytes>\n<file_data>

Lengths are decimal values encoded as ascii strings.
Yes this is not optimal but we'd need additional
lua libraries if we wanted to decode and encode
bytes into numbers and we wan to keep the firmware
size as small as possible + these lua libraries
are not part of the default OpenWRT distro.

--]]

function receive_file(conn)

  -- number of bytes encoding the file_size field
  local file_name_size_length = 4
  local file_name_size
  local file_name
  -- number of bytes encoding md5 checksum field
  local md5_checksum_length = 32
  local md5_checksum
  -- number of bytes encoding file field
  local file_size_length = 16
  local file_size
  local data
  local err
  local partial -- partial data received

  data, err, partial = conn:receive('*l')

  if not data then
     print("Error: "..err)
     return false
  end
  
  local i
  local j
  i, j = string.find(data, "FILE:")
  if not i == 1 then
     print("Error: Got invalid response. Expecting 'FILE' got: "..data)
     return false
  end 

  -- cut off the "FILE:" part
  data = string.sub(data, j+1) 

--  print("[" .. data .. "]")

  -- read the file name size
  file_name_size = string.sub(data, 1, file_name_size_length)
  file_name_size = tonumber(file_name_size)
  data = string.sub(data, file_name_size_length + 2)

  -- read the file name
  file_name = string.sub(data, 1, file_name_size)
  file_name = sanitize_filename(file_name)

  -- TODO TESTING ONLY! REMOVE!
  file_name = file_name .. ".receive"

  data = string.sub(data, file_name_size + 2)

  -- read the md5 checksum
  md5_checksum = string.sub(data, 1, md5_checksum_length)
  data = string.sub(data, md5_checksum_length + 2)
  
  -- read the file size
  file_size = string.sub(data, 1, file_size_length)
  file_size = tonumber(file_size)
--  data = string.sub(data, file_size_length + 2)
  
  -- receive the file
  return receive_and_write(conn, file_name, file_size)
end

--[[

  Config responses have the following format:

    CONFIG:<number_of_files>\n
    <file_response(s)>

--]]

function receive_config(conn)

  local data
  local err
  local partial -- partial data received

  data, err, partial = conn:receive('*l')

  if not data then
     print("Error: "..err)
     return false
  end
  
  -- TODO allow more than one file
  if not string.find(data, "CONFIG:1") == 1 then
     print("Error: Got invalid response. Expecting 'CONFIG' got: "..data)
     return false
  end

  return receive_file(conn)
end

function get_config(conn)
  conn:send("GIMME_CONFIG\n")
  return receive_config(conn)
end


local c
c = connect()

if not c then
   print("Failed to connect")
   conn:close()
   os.exit(-1);
end
-- receive the configuration from the server
get_config(c)


c:close()