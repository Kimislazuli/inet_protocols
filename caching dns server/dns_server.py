from socket import AF_INET, SOCK_DGRAM, SOL_SOCKET, SO_REUSEADDR
from socket import socket
from dnslib import DNSRecord, RCODE

ROOT_SERVER = "77.88.8.1"


def parse_transaction_id(transaction_id):
    result = ''
    for byte in transaction_id:
        result += hex(byte)[2:]

    return result

def build_flags(flags):
    QR = '1'
    OPCODE = ''

    first_byte_of_flags = flags[:1]

    for bit in range(1, 5):
        bit_mask = (1 << bit)
        OPCODE += str(ord(first_byte_of_flags) & bit_mask)

    AA = '1'
    TC = '0'
    RD = '0'
    RA = '0'
    Z = '000'
    RCODE = '0000'

    first_byte_result = int(QR + OPCODE + AA + TC + RD, 2)
    second_byte_result = int(RA + Z + RCODE, 2)
    return first_byte_result.to_bytes(1, byteorder='big') + second_byte_result.to_bytes(1, byteorder='big')


def identify_query_type(query_type):
    if query_type == b'\x00\x01':
        return 'A'


def parse_query(query):
    part_len = 0
    part_pointer = 0
    general_query_pointer = 0
    part = ''
    domain_name = []
    build_part = False
    for byte in query:
        if not build_part:
            part_len = byte
            build_part = True
            continue

        part += chr(byte)
        part_pointer += 1
        general_query_pointer += 1
        if part_pointer == part_len:
            part_pointer = 0
            domain_name.append(part)
            build_part = False
            part = ''
        if byte == 0:
            # domain_name.append(part)
            break

    type_of_request = identify_query_type(query[general_query_pointer + 1: general_query_pointer + 3])

    return domain_name, type_of_request


def create_response(recieved_data):
    # now make header
    transaction_id = parse_transaction_id(recieved_data[0:2])  # parse transaction id from request
    flags = build_flags(recieved_data[2:4])  # parse flags + change some
    QDCOUNT = b'\x00\x01'

    # and then query
    domain_name, type_of_request = parse_query(recieved_data[12:])


def main():
    server_socket = socket(AF_INET, SOCK_DGRAM)  # IPv4 UDP socket
    server_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)  # 'clean' every time
    server_socket.bind(('127.0.0.1', 5353))
    print('server is up')
    while True:
        data, addr = server_socket.recvfrom(512)  # recieve request from client
        print(f'connection from {addr}')
        print(f'recieved data: {data}')
        response = create_response(data)


if __name__ == '__main__':
    main()
