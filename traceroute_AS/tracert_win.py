"""
Windows script to parse traceroute and check AS for every router.
"""
import json
import re
import sys
from subprocess import check_output
from argparse import ArgumentParser
from urllib.request import urlopen

from prettytable import PrettyTable

MISSMATCH = r'\* {8}\* {8}\*'
IP = r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}'
GREY_NETWORKS_RANGE = [
    r'172\.(1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3}',
    r'10\.\d{1,3}\.\d{1,3}\.\d{1,3}',
    r'192\.168\.\d{1,3}\.\d{1,3}',
    r'127\.\d{1,3}\.\d{1,3}\.\d{1,3}',
]


class Args:
    """
    Args parser to extract args from command line.
    """

    def __init__(self):
        self.destination = self._parse_args()

    @staticmethod
    def _parse_args() -> str:
        parser = ArgumentParser(description='Traceroute for autonomous system.')

        parser.add_argument('destination', type=str, help='IP address or domain name of destination')

        args = parser.parse_args()

        return args.destination


def parse_info_by_ip(ip_address: str) -> list[str, str, str, str]:
    """
    Check if ip grey and parse info about it if not.

    :param ip_address: address to check info
    :return: parsing results
    """
    # check is IP address grey
    for regex in GREY_NETWORKS_RANGE:
        temp_match = re.match(regex, ip_address)
        if temp_match:
            return [ip_address, 'grey ip address', '', '']

    # parse json
    url = 'https://api.incolumitas.com/?q=' + ip_address
    data_from_link = urlopen(url)
    data_from_json = json.load(data_from_link)
    return [
        ip_address,
        data_from_json['asn']['asn'],
        data_from_json['location']['country'],
        data_from_json['location']['city']
    ]


def process_output_line(line: str) -> list:
    """
    Processing tracert output line to result table line with extraction of IP and check for missmatch.

    :param line: decoded line from $tracert [destination]
    :return: processed row for the results table
    """
    # check is unreachable
    if re.findall(MISSMATCH, line):
        sys.exit(0)

    # extract IP address
    router_ip = re.findall(IP, line)

    # check is IP address grey
    for regex in GREY_NETWORKS_RANGE:
        temp_match = re.findall(regex, line)
        if temp_match:
            return f'IP: {router_ip[0]}, grey IP address'

    # check IP in line
    if router_ip:
        return f'IP: {router_ip[0]}'

    return ''


def traceroute(dest):
    # tracert call
    output = check_output(['tracert', dest]).splitlines()
    for line in output:
        print(process_output_line(line.decode('CP866')))


def main():
    args = Args()
    traceroute(args.destination)


if __name__ == '__main__':
    main()
