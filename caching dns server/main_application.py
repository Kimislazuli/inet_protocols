from socket import socket, AF_INET, SOCK_DGRAM, SOMAXCONN, SOL_SOCKET, SO_REUSEADDR


def handle_input(conn, addr):
    with conn:
        while True:
            data = conn.recv(1024)
            if data:
                pass  # TODO: parse input
            else:
                print('connection closed')
                break


def main():
    server_socket = socket(AF_INET, SOCK_DGRAM)
    server_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    server_socket.bind(('localhost', 53))
    server_socket.listen(SOMAXCONN)

    while True:
        conn, addr = server_socket.accept()
        print(f'connection from {addr}')


if __name__ == '__main__':
    main()
