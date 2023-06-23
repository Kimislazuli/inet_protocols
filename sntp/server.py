import socket

import packet

PORT = 123
SNTP_SERVER = 'time.windows.com'
MY_SERVER = ('localhost', 5000)


def ask_server():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.settimeout(5)

    sntp_request = packet.SNTPPacket()
    sntp_request = sntp_request.to_bytes()

    try:
        sock.sendto(sntp_request, (SNTP_SERVER, PORT))

        response, address = sock.recvfrom(1024)

        return response

    except socket.timeout:
        print('Превышено время ожидания. Не удалось получить ответ от сервера.')

    finally:
        sock.close()

    return None


def get_answer():
    bytes_packet = ask_server()
    response = packet.SNTPPacket.from_bytes(bytes_packet)

    # Извлекаем время из ответа
    if len(bytes_packet) >= 48:
        transmit_timestamp = response._transmit_timestamp
        real_time = transmit_timestamp - 2208988800  # SNTP/NTP timestamp offset

    with open('config.txt', 'r') as f:
        offset = int(f.read())

    fake_time = real_time + int(offset)

    return packet.SNTPPacket(
        mode=4,
        stratum=response._stratum + 1,
        reference_id=response._reference_id,
        reference_timestamp=fake_time,
        originate_timestamp=0,
        receive_timestamp=fake_time,
        transmit_timestamp=fake_time
    )


def run_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(MY_SERVER)

    print('Сервер запущен')

    while True:
        data, address = server_socket.recvfrom(1024)
        print(f'Новое подключение от {address}')
        print(f'От {address} получен пакет: {packet.SNTPPacket.from_bytes(data)}')

        response = get_answer().to_bytes()

        server_socket.sendto(response, address)


def main():
    run_server()


if __name__ == "__main__":
    main()
