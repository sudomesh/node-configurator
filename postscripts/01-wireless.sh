
# For UCI docs see:
# http://wiki.openwrt.org/doc/uci
# http://wiki.openwrt.org/doc/uci/wireless

HWMODE=$(uci get wireless.radio0.hwmode)

if [ HWMODE = "11na" ] then
  # set 40 mhz channel starting at 157 for 5 ghz 802.11n gear
  uci set wireless.@wifi-device[0].htmode='HT40+'
  uci set wireless.@wifi-device[0].channel=157
elif [ HWMODE = "11a" ] then
  # set channel 3 for 2.4 ghz gear
  uci set wireless.@wifi-device[0].channel=157
else
  # set channel 3 for 2.4 ghz gear
  uci set wireless.@wifi-device[0].channel=3
fi

uci delete wireless.@wifi-device[0].disabled

uci delete wireless.@wifi-iface[0]
uci add wireless wifi-iface
uci set wireless.@wifi-iface[0].device='radio0'
uci set wireless.@wifi-iface[0].ifname='open0'
uci set wireless.@wifi-iface[0].encryption='none'
uci set wireless.@wifi-iface[0].network='openmesh'
uci set wireless.@wifi-iface[0].mode='ap'
uci set wireless.@wifi-iface[0].ssid='peoplesopen.net'

uci add wireless wifi-iface
uci set wireless.@wifi-iface[1].device='radio0'
uci set wireless.@wifi-iface[1].ifname='adhoc0'
uci set wireless.@wifi-iface[1].encryption='none'
uci set wireless.@wifi-iface[1].network='mesh'
uci set wireless.@wifi-iface[1].mode='adhoc'
uci set wireless.@wifi-iface[1].bssid='CA:FE:C0:DE:F0:0D'
uci set wireless.@wifi-iface[1].ssid='pplsopen.net-node2node'

uci add wireless wifi-iface
uci set wireless.@wifi-iface[2].device='radio0'
uci set wireless.@wifi-iface[2].ifname='priv0'
uci set wireless.@wifi-iface[2].encryption='psk2'
uci set wireless.@wifi-iface[2].key='<private_wifi_key>'
uci set wireless.@wifi-iface[2].network='priv'
uci set wireless.@wifi-iface[2].mode='ap'
uci set wireless.@wifi-iface[2].ssid='<private_wifi_ssid>'

uci commit wireless
