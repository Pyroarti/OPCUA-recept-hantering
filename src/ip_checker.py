import json
from pathlib import Path

from ping3 import ping


def check_ip(retries=2):
    """
    Checks the IP addresses of nearby units to see if they are alive.
    Place the IP addresses in the configs/ip_addresses.json file.
    """

    results = []

    output_path = Path(__file__).parent.parent

    with open (output_path / "configs" / "ip_addresses.json",encoding="UTF8") as addresses:
        data:dict = json.load(addresses)
        for name, ips in data.items():
            ip_address, _ = ips.split(":")
            success_count = 0
            for _ in range(retries):
                response_time = ping(ip_address)
                if response_time is not None:
                    success_count += 1
            status = success_count == 2
            results.append((name, ip_address, status))
        return results

if __name__ == "__main__":
    check_ip()
