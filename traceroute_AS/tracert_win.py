"""
Windows script to parse traceroute and check AS for every router.
"""
import json
import re
import socket
from subprocess import check_output
from argparse import ArgumentParser
from typing import Optional
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
ARIN_AS = r'<originAS>AS(\d{5})</originAS>'


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


def parse_json(url: str) -> Optional[dict[str]]:
    """
    Try open json and extract data.

    :param url: link
    :return: result or None if there's no result
    """
    try:
        with urlopen(url) as handle:
            return json.load(handle)
    except AttributeError:
        return None


def regional_whois(ip_address: str, zone: str, regex: str) -> Optional[str]:
    """
    Ask specific regional whois.

    :param ip_address: target address
    :param zone: registrar
    :param regex: regex for this registrar's whois response
    :return: result or None if there's no result
    """
    # open socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(('whois.' + zone + '.net', 43))
    sock.sendall(f'{ip_address}\n'.encode('utf-8'))

    response = b''

    # load data
    while True:
        chunk = sock.recv(1024)
        if not chunk:
            break
        response += chunk

    # close socket
    sock.close()

    # check asn
    as_number = re.findall(regex, response.decode('utf-8'))

    if len(as_number):
        return as_number[0]

    return None


def ask_regional_registrars(ip_address: str) -> Optional[str]:
    """
    Ask all regional registrars.

    :param ip_address: target address
    :return: result or None if there's no result
    """
    as_number = regional_whois(ip_address, 'ripe', r'origin:\s+AS(\d+)')

    if as_number is None:
        as_number = regional_whois(ip_address, 'lacnic', r'aut-num:\s+AS(\d+)')

    if as_number is None:
        as_number = regional_whois(ip_address, 'apnic', r'origin:\s+AS(\d+)')

    if as_number is None:
        as_number = regional_whois(ip_address, 'arin', r'OriginAS:\s+AS(\d+)')

    if as_number is None:
        as_number = regional_whois(ip_address, 'afrinic', r'(AS\d+)')

    return as_number


def ask_ip_info(ip_address: str) -> Optional[str]:
    """
    Ask ipinfo if regional registrars don't know.

    :param ip_address: target address
    :return: result or None if there's no result
    """
    data_from_json = parse_json('https://ipinfo.io/' + ip_address)

    if data_from_json is None:
        return None

    try:
        data = data_from_json['org']
    except KeyError:
        data = ''

    as_number = re.findall(r'AS(\d+)', data)

    if len(as_number):
        return as_number[0]

    return None


def check_if_ip_is_grey(ip_address: str) -> bool:
    """
    Check if specific ip address is from grey range.

    :param ip_address: target address
    :return: bool: True if yes and False if no
    """
    for regex in GREY_NETWORKS_RANGE:
        temp_match = re.match(regex, ip_address)

        if temp_match is None:
            continue

        return True

    return False


def parse_info_by_ip(ip_address: str) -> list[str, str, str, str]:
    """
    Check if ip grey and parse info about it if not.

    :param ip_address: address to check info
    :return: parsing results
    """
    # check is IP address grey
    if check_if_ip_is_grey(ip_address):
        return [ip_address, 'grey ip address', '', '']

    # parse json
    data_from_json = parse_json('https://api.incolumitas.com/?q=' + ip_address)

    if data_from_json is not None:
        asn = data_from_json['asn']
    else:
        asn = None

    # is there's no asn
    if isinstance(asn, dict):
        asn = asn['asn']
    elif asn is None:
        asn = ask_regional_registrars(ip_address)
        if asn is None:
            asn = ask_ip_info(ip_address)
            if asn is None:
                asn = ''

    # other data
    country = data_from_json['location']['country']
    city = data_from_json['location']['city']

    return [
        ip_address,
        asn,
        country,
        city
    ]


def process_output_line(line: str) -> list:
    """
    Processing tracert output line to result table line with extraction of IP and check for missmatch.

    :param line: decoded line from $ tracert [destination]
    :return: processed row for the results table
    """

    # check is unreachable
    if re.findall(MISSMATCH, line):
        return ['*']

    # extract IP address
    router_ip = re.findall(IP, line)

    # check IP in line
    if router_ip:
        return parse_info_by_ip(router_ip[0])

    return []


def create_table(data: list) -> PrettyTable:
    """
    Create table with results of tracert and country + city validation.

    :param data: parsed tracert lines
    :return: table with results
    """

    traceroute_table = PrettyTable()
    traceroute_table.field_names = ['IP', 'ASN', 'Country', 'City']

    for line in data:
        processing_result = process_output_line(line.decode('CP866'))
        if len(processing_result) == 1:
            break
        elif len(processing_result) > 1:
            traceroute_table.add_row(processing_result)

    return traceroute_table


def main():
    args = Args()
    output = check_output(['tracert', args.destination]).splitlines()

    ptr = 0
    while ptr < len(output):
        line = output[ptr]
        processing_result = process_output_line(line.decode('CP866'))

        if len(processing_result) > 1:
            destination = ', '.join(list(map(str, processing_result)))
            print(f'Destination: {destination}')
            ptr += 1
            break

        ptr += 1

    print(create_table(output[ptr:]))


if __name__ == '__main__':
    main()
