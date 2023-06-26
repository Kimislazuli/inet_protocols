import base64
import quopri
import ssl
from configparser import ConfigParser
from socket import create_connection
import re

PORT = 995


def parse_config() -> tuple:
    config_parser = ConfigParser(allow_no_value=True)
    with open('config.cfg', 'r', encoding='utf-8') as f:
        config_parser.read_file(f)

    return config_parser['Server']['Address'], config_parser['Client']['Login'], config_parser['Client']['Password']


def request(sock, request):
    sock.send((request + '\n').encode())

    recv_data = ''
    while True:
        chunk = sock.recv(1024).decode('utf-8')
        recv_data += chunk
        if len(chunk) < 1024 or not chunk:
            break

    return recv_data


def load_letter(client, message_number):
    letter = ''
    request(client, f'RETR {message_number}\n')

    while '\r\n.\r\n' not in letter:
        letter += client.recv(1024).decode('utf-8')

    return letter


def get_subject(letter):
    letter_lines = letter.split('\r\n')

    result = ''
    for i in range(len(letter_lines)):
        line = letter_lines[i]
        if line.startswith('Subject: '):
            line = re.findall(r'Subject: (.*)', line)[0]
            if 'utf-8' not in str.lower(line):
                result = line
                break
            if str.lower(line[8]) == 'b':
                line = base64.b64decode(line[10:-2]).decode()
            elif str.lower(line[8]) == 'q':
                line = quopri.decodestring(line[10:-2]).decode()
            result += line
            i += 1
            while letter_lines[i].startswith(' ') or letter_lines[i].startswith('\t='):
                line = letter_lines[i]

                if str.lower(line[9]) == 'b':
                    line = base64.b64decode(letter_lines[i][11:-1]).decode()
                elif str.lower(line[9]) == 'q':
                    line = quopri.decodestring(letter_lines[i][11:-1]).decode()
                result += line
                i += 1
            break
    print(result)


def get_date(letter):
    letter_lines = letter.split('\r\n')

    for i in range(len(letter_lines)):
        date = letter_lines[i]
        if date.startswith('Date: '):
            date = re.findall(r'Date: (.*)', date)[0]
            print(date)


def get_sender(letter):
    letter_lines = letter.split('\r\n')

    for i in range(len(letter_lines)):
        sender = letter_lines[i]
        if sender.startswith('From: '):
            sender = re.findall(r'From: (.*)', sender)[0]
            print(sender)


def get_top(client, message_number, n):
    top = ''
    print(request(client, f'TOP {message_number} {n}\r\n'))
    while '\r\n.\r\n' not in top:
        top += client.recv(1024).decode('utf-8')
    print(top)


def multypart_related_handler(letter, content_types, boundary):
    if content_types[0] == 'text/html':
        with open('text.html', 'w', encoding='utf-8') as f:
            f.write(letter.split(boundary[1]))
        if len(content_types) > 1:
            handle_attachments(letter, content_types, boundary)


def handle_attachments(letter, content_types, boundary):
    if len(boundary) == 1:
        bound = boundary[0]
    else:
        bound = boundary[1]

    counter = 0
    for attachment in content_types[1:]:
        counter += 1
        start = letter.find(attachment) + len(attachment) + 3
        end = letter[start:].find(bound)
        print(letter[start:end])

        bytes_attachment = letter[start:end]
        print(bytes_attachment)
        bytes_attachment = base64.b64decode(bytes_attachment)
        ext = attachment.split()[0].split('/')[1]
        with open(f'{counter}.{ext}', 'wb') as f:
            f.write(bytes_attachment)


def multypart_mixed_handler(letter, boundary):
    content_types = re.findall(r'Content-Type: (.*)', letter)[1:]
    content_types = [x.replace('\r', '').replace(';', '') for x in content_types]

    if 'multipart/related' in content_types[0]:
        multypart_related_handler(letter, content_types, boundary)
    elif 'text/html' in content_types[0]:
        with open('text.html', 'w', encoding='utf-8') as f:
            f.write(letter.split(boundary[0])[2])
        if len(content_types) > 1:
            handle_attachments(letter, content_types, boundary)
    elif 'text/plain' in content_types[0]:
        with open('text.txt', 'w', encoding='utf-8') as f:
            text = letter.split(boundary[0])[2]
            f.write(text)
        if len(content_types) > 1:
            handle_attachments(letter, content_types, boundary)


def download(letter):
    letter_lines = letter.split('\r\n')
    print(letter)

    boundary = re.findall(r'boundary="?(.*)"?', letter)

    content_type = re.findall(r'Content-Type: (.*);', letter)
    print(content_type)

    if content_type[0] == 'multipart/mixed':
        multypart_mixed_handler(letter, boundary)
    elif 'text/html' in content_type[0]:
        with open('text.html', 'w', encoding='utf-8') as f:
            pass
            start = letter.find('<div>')
            end = letter.find('\r\n.\r\n')
            text = letter[start:end]
            f.write(text)
    elif 'text/plain' in content_type[0]:
        with open('text.txt', 'w', encoding='utf-8') as f:
            text = letter.split(boundary[0])[2]
            f.write(text)


COMMANDS = {
    1: get_subject,
    2: get_date,
    3: get_sender,
    4: get_top,
    5: download
}


def main():
    host_addr, login, password = parse_config()

    ssl_contex = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ssl_contex.check_hostname = False
    ssl_contex.verify_mode = ssl.CERT_NONE

    with create_connection((host_addr, PORT)) as sock:
        with ssl_contex.wrap_socket(sock, server_hostname=host_addr) as client:
            print(client.recv(1024).decode())

            print(request(client, f'USER {login}'))

            response = request(client, f'PASS {password}')

            letters_amount = int(response.split()[1])

            print(f'На Вашем ящике {letters_amount} писем.\n')

            while True:
                message_number = input('Введите номер письма, которое хотите посмотреть или q, если хотите выйти из POP3 клиента: ')

                if message_number == 'q':
                    break

                if not message_number.isdigit():
                    print('Вы ввели некорректное значение')
                    continue
                elif int(message_number) > letters_amount:
                    print('На Вашем ящике нет такого количества писем')
                    continue

                letter = load_letter(client, message_number)

                print('''Какую информацию Вы хотите получить?
                1. Тема письма;
                2. Дата получения;
                3. Отправитель;
                4. Первые n строк;
                5. Скачать письмо с вложениями.''')

                command = int(input('Введите номер команды: '))

                while command not in range(1, 6):
                    print('Такая команда отвутствует. Выберите число от 1 до 5.')
                    command = int(input('Введите номер команды: '))

                if command == 4:
                    n = int(input('Введите n: '))
                    COMMANDS[command](client, message_number, n)
                else:
                    COMMANDS[command](letter)


if __name__ == '__main__':
    main()
