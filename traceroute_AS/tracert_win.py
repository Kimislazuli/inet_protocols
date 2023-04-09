"""
Windows script to parse traceroute and check AS for every router.
"""

import re
from subprocess import check_output
from argparse import ArgumentParser

MISSMATCH = r'\* {8}\* {8}\*'
IP = r'\d{1,3}\.\d{1,3}.\d{1,3}\.\d{1,3}'
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


def process_output_line(line: str) -> str:
    """
    Processing tracert output line to result table line with extraction of IP and checks for missmatch/grey IP.

    :param line: decoded line from $tracert [destination]
    :return: processed row for the results table
    """
    # check is unreachable
    if re.findall(MISSMATCH, line):
        return '***'

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
