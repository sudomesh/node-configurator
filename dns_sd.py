#!/usr/bin/env python

import avahi
import dbus

'''

  This is just a simple python script to announce
  a service using DNS-SD by talking to Avahi using D-BUS.

  It needs to be integrated into ssl_server.py


'''

__all__ = ["ZeroconfService"]

class ZeroconfService:

    def __init__(self, name, port, stype="_node-configurator._tcp",
                 domain="", host="", text="http://sudomesh.org"):
        self.name = name
        self.stype = stype
        self.domain = domain
        self.host = host
        self.port = port
        self.text = text

    def publish(self):
        bus = dbus.SystemBus()
        server = dbus.Interface(
                         bus.get_object(
                                 avahi.DBUS_NAME,
                                 avahi.DBUS_PATH_SERVER),
                        avahi.DBUS_INTERFACE_SERVER)

        g = dbus.Interface(
                    bus.get_object(avahi.DBUS_NAME,
                                   server.EntryGroupNew()),
                    avahi.DBUS_INTERFACE_ENTRY_GROUP)

        g.AddService(avahi.IF_UNSPEC, avahi.PROTO_UNSPEC,dbus.UInt32(0),
                     self.name, self.stype, self.domain, self.host,
                     dbus.UInt16(self.port), self.text)

        g.Commit()
        self.group = g

    def unpublish(self):
        self.group.Reset()


def start():
    service = ZeroconfService(name="juul", port=5100)
    service.publish()
    raw_input("Press any key to shut down the node configurator.")
    service.unpublish()


if __name__ == "__main__":
    start()
