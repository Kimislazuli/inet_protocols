import datetime
import socket

import packet


SERVER = ('localhost', 5000)


def main():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    request_to_server = packet.SNTPPacket()
    client_socket.sendto(request_to_server.to_bytes(), SERVER)

    response, _ = client_socket.recvfrom(1024)

    response = packet.SNTPPacket.from_bytes(response)
    print(f'Received response: {response}\n')

    time = datetime.datetime.fromtimestamp(response._transmit_timestamp)
    print(time)


if __name__ == "__main__":
    main()
