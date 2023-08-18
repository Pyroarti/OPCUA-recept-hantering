import sys
import socket
from zeroconf import ServiceBrowser, Zeroconf

class OPCUAServerListener:
    def __init__(self):
        self.found_servers = []

    def remove_service(self, zeroconf, type, name):
        print(f"Service {name} removed")

    def add_service(self, zeroconf, type, name):
        info = zeroconf.get_service_info(type, name)
        address = socket.inet_ntoa(info.addresses[0])
        port = info.port

        server_info = {
            "name": name,
            "address": address,
            "port": port,
        }

        self.found_servers.append(server_info)
        print(f"OPC UA Server found:\nName: {name}\nAddress: {address}\nPort: {port}\n")

    def update_service(self, zeroconf, type, name):
        pass  # This method can be empty if you don't need to handle service updates


if __name__ == "__main__":
    zeroconf = Zeroconf()
    listener = OPCUAServerListener()

    print("Searching for OPC UA servers on local network...\n")
    browser = ServiceBrowser(zeroconf, "_opcua-tcp._tcp.local.", listener)

    try:
        input("Press enter to exit...\n")
    finally:
        browser.cancel()
        zeroconf.close()
