import ssl
import sys
from argparse import ArgumentParser
from concurrent.futures import ThreadPoolExecutor, as_completed
import socket
from struct import pack

PACKET = b'\x13' + b'\x00' * 39 + b'\x6f\x89\xe9\x1a\xb6\xd5\x3b\xd3'


class Args:
    def __init__(self):
        self.host, self.start, self.end = self._parse_args()

    @staticmethod
    def _parse_args() -> tuple[str, int, int]:
        parser = ArgumentParser(description='TCP port scanner.')
        parser.add_argument('-p', '--ports', type=int, nargs=2, dest='ports',
                            help='port or range of ports example: 1 100')
        parser.add_argument('--host', type=str, dest='host',
                            default='localhost', help='host to scan')

        args = parser.parse_args()
        try:
            start, end = args.ports[0], args.ports[1]
        except ValueError:
            print('В качестве порта необходимо вводить целое число')
            sys.exit(1)
        if end > 65535:
            print('Номер порта не должен превышать 65535')
            sys.exit(1)
        if start > end:
            print('Invalid arguments')
            sys.exit(1)
        try:
            socket.gethostbyname(args.host)
        except socket.gaierror:
            print(f'Некорректный адрес хоста {args.host}')
            sys.exit(1)
        return args.host, start, end


def scan_tcp(host, port):
    socket.setdefaulttimeout(0.5)
    result = ''
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as scanner:
        try:
            scanner.connect((host, port))
            result = f'TCP {port}'
        except (socket.timeout, TimeoutError, OSError):
            pass

        if result:
            try:
                result = check_tcp_protocol(host, port, result)
            except socket.error:
                pass

    return result


def check_tcp_protocol(host, port, result):
    if is_dns(host, port, True):
        return f'{result} DNS'

    if is_http(host, port):
        return f'{result} HTTP'

    if is_smtp(host, port):
        return f'{result} SMTP'

    if is_pop3(host, port):
        return f'{result} POP3'

    return result


def scan_udp(host, port):
    socket.setdefaulttimeout(3)
    result = ''
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as scanner:
        try:
            scanner.sendto(PACKET, (host, port))
            data, _ = scanner.recvfrom(1024)
            result = f'UDP {port}'
            if result:
                result = check_udp_protocol(host, port, data, result)
        except socket.error:
            pass
    return result


def check_udp_protocol(host, port, data, result):
    if is_dns(host, port, False):
        return f'{result} DNS'

    if is_sntp(data):
        return f'{result} SNTP'


def scan_port(host, port):
    result = scan_tcp(host, port)
    if result:
        return result

    result = scan_udp(host, port)
    return result


def is_http(host, port):
    request = "GET / HTTP/1.1\r\nHost: ya.ru\r\n\r\n"

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((host, port))

        sock.sendall(request.encode())

        response = sock.recv(4096)

    return b'HTTP' in response


def is_smtp(host, port):
    ssl_contex = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ssl_contex.check_hostname = False
    ssl_contex.verify_mode = ssl.CERT_NONE

    with socket.create_connection((host, port)) as sock:
        with ssl_contex.wrap_socket(sock, server_hostname=host) as client:
            data = client.recv(1024).decode()
            return data[:3].isdigit()


def is_pop3(host, port):
    ssl_contex = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ssl_contex.check_hostname = False
    ssl_contex.verify_mode = ssl.CERT_NONE

    with socket.create_connection((host, port)) as sock:
        with ssl_contex.wrap_socket(sock, server_hostname=host) as client:
            response = client.recv(1024)
    return response.startswith(b'+')


def is_dns(host, port, tcp):
    data = b''
    if tcp:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as scanner:
            try:
                scanner.connect((host, port))
                scanner.send(pack('!H', len(PACKET)) + PACKET)
                data = scanner.recv(1024)
            except (socket.timeout, TimeoutError, OSError, socket.error):
                pass

    else:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as scanner:
            try:
                scanner.sendto(PACKET, (host, port))
                data, _ = scanner.recvfrom(1024)
            except socket.error:
                pass

    transaction_id = PACKET[:2]
    return transaction_id in data


def is_sntp(data):
    transmit_timestamp = PACKET[-8:]
    reference_timestamp = data[24:32]
    is_packet_from_server = 7 & data[0] == 4
    return len(data) >= 48 and is_packet_from_server and reference_timestamp == transmit_timestamp


def print_results(res):
    if not res:
        print('Нет открытых портов.')
        return
    udps = [port for port in res if port.startswith('UDP')]
    tcps = [port for port in res if port.startswith('TCP')]

    if udps:
        print('UDP\'s:')
        for udp in udps:
            print(udp)

        print('\n')

    if tcps:
        print('TCP\'s:')
        for tcp in tcps:
            print(tcp)


def main():
    args = Args()

    futures = []

    with ThreadPoolExecutor(max_workers=300) as executor:
        for port in range(args.start, args.end):
            future = executor.submit(scan_port, args.host, port)
            futures.append(future)

        res = []
        for future in as_completed(futures):
            result = future.result()
            if result:
                res.append(result)

    print_results(res)


if __name__ == '__main__':
    main()
