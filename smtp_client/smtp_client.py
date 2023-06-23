import base64
import ssl
from configparser import ConfigParser
from socket import socket

PORT = 465
TIME_OUT = 1


def parse_config() -> tuple:
    config_parser = ConfigParser(allow_no_value=True)
    with open('config.cfg', 'r', encoding='utf-8') as f:
        config_parser.read_file(f)

    return config_parser['Server']['Address'], config_parser['Client'], config_parser['Letter']


def fix_text(text: str) -> str:
    if text.startswith('.'):
        return '.' + text.replace('\n.\n', '\n..\n')

    return text.replace('\n.\n', '\n..\n')


def request(sock, request):
    sock.send((request + '\n').encode())

    recv_data = ''
    while True:
        chunk = sock.recv(1024).decode('utf-8')
        if len(chunk) == 0:
            break
        recv_data += chunk

    print(recv_data)

    return recv_data


def message_prepare(user_name_from, user_name_to, subject_msg):
    with open('msg.txt') as file_msg:
        boundary_msg = "bound.40629"
        headers = f'from: {user_name_from}\n'
        headers += f'to: {user_name_to}\n'  # пока получатель один
        headers += f'subject: {subject_msg}\n'  # короткая тема на латинице
        headers += 'MIME-Version: 1.0\n'
        headers += 'Content-Type: multipart/mixed;\n' \
                   f'    boundary={boundary_msg}\n'

        # тело сообщения
        message_body = f'--{boundary_msg}\n'
        message_body += 'Content-Type: text/plain; charset=utf-8\n\n'
        msg = file_msg.read()
        message_body += msg + '\n'

        message_body += f'--{boundary_msg}\n'
        message_body += 'Content-Disposition: attachment;\n' \
                        '   filename="test_picture.png"\n'
        message_body += 'Content-Transfer-Encoding: base64\n'
        message_body += 'Content-Type: image/png;\n\n'

        with open('test_picture.png', 'rb') as picture_file:
            picture = base64.b64encode(picture_file.read()).decode("UTF-8")
        message_body += picture + '\n'

        message_body += f'--{boundary_msg}--'

        message = headers + '\n' + message_body + '\n.\n'
        print(message)
        return message


host_addr, client, letter = parse_config()

user_name_from = client['Login']
password = client['Password']
user_name_to = letter['Recipients'].strip().split('\n')

with open('text.txt', 'r', encoding='utf-8') as f:
    text = fix_text(f.read()) + '\n.\n'
    print(text)

ssl_contex = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
ssl_contex.check_hostname = False
ssl_contex.verify_mode = ssl.CERT_NONE

with socket.create_connection((host_addr, PORT)) as sock:
    with ssl_contex.wrap_socket(sock, server_hostname=host_addr) as client:
        print(client.recv(1024))  # в smpt сервер первый говорит
        print(request(client, f'ehlo {user_name_from}'))
        base64login = base64.b64encode(user_name_from.encode()).decode()

        base64password = base64.b64encode(password.encode()).decode()
        print(request(client, 'AUTH LOGIN'))
        print(request(client, base64login))
        print(request(client, base64password))
        print(request(client, f'MAIL FROM:{user_name_from}'))
        print(request(client, f'RCPT TO:{user_name_to}'))
        print(request(client, 'DATA'))
        print(request(client, message_prepare()))
