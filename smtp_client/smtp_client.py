import base64
import datetime
import os
import ssl
from configparser import ConfigParser
from socket import create_connection

PORT = 465
TIME_OUT = 1

MIME_TYPES = {
    'jpeg': 'image/jpeg',
    'mp4': 'video/mp4',
    'webm': 'audio/webm',
    'gif': 'image/gif',
    'png': 'image/png',
    'pdf': 'application/pdf'
}


def parse_config() -> tuple:
    config_parser = ConfigParser(allow_no_value=True)
    with open('config.cfg', 'r', encoding='utf-8') as f:
        config_parser.read_file(f)

    return config_parser['Server']['Address'], config_parser['Client'], config_parser['Letter']


def request(sock, request):
    sock.send((request + '\n').encode())

    recv_data = ''
    while True:
        chunk = sock.recv(1024).decode('utf-8')
        recv_data += chunk
        if len(chunk) < 1024 or not chunk:
            break

    return recv_data


def fix_text(text: str) -> str:
    if text.startswith('.'):
        return '.' + text.replace('\n.', '\n..')

    return text.replace('\n.', '\n..')


def attachment_handler(attachment_name):
    extension = attachment_name.split('.')[-1]
    mime = MIME_TYPES[extension]

    attachment = ''

    filename = attachment_name.split(r'/')[-1]

    attachment += f'Content-Disposition: attachment;\n' \
                  f'   filename="{filename}"\n'
    attachment += 'Content-Transfer-Encoding: base64\n'
    attachment += f'Content-Type: {mime};\n\n'

    with open(attachment_name, 'rb') as f:
        encoded_attachment = base64.b64encode(f.read()).decode("UTF-8")
    attachment += encoded_attachment + '\n'

    return attachment


def recipient_handler(recipients):
    formatted_recipients = ''
    for recipient in recipients:
        formatted_recipients += f'<{recipient}>,\n\t'
    print(formatted_recipients[:-3])
    return formatted_recipients[:-3]


def subject_handler(subject):
    formatted_subject = ''
    while len(subject) > 40:
        formatted_subject += f'=?UTF-8?B?{base64.b64encode(subject[:40].encode()).decode()}?=\n\t'
        subject = subject[40:]

    if subject:
        formatted_subject += f'=?UTF-8?B?{base64.b64encode(subject.encode()).decode()}?=\n\t'

    return formatted_subject


def message_prepare(send_from, send_to, subject_msg, attachments, filename):
    with open(filename, 'r', encoding='utf-8') as file_msg:
        boundary_msg = '----=-bound.40629'
        headers = f'From: {send_from}\n'
        headers += f'To: {send_to}\n'
        headers += f'Subject: {subject_handler(subject_msg)}\n'
        headers += 'MIME-Version: 1.0\n'
        headers += 'Content-Type: multipart/mixed;\n' \
                   f'    boundary={boundary_msg}\n'

        # тело сообщения
        message_body = f'--{boundary_msg}\n'
        message_body += 'Content-Type: text/plain; charset=utf-8\n\n'
        msg = fix_text(file_msg.read())
        message_body += msg + '\n'

        for attachment in attachments:
            message_body += f'--{boundary_msg}\n'
            message_body += attachment_handler(attachment)

        message_body += f'--{boundary_msg}--'

        message = headers + '\n' + message_body + '\n.\n'

        print(message)
        return message


def send_all(client, recipients):
    for recipient in recipients:
        print(request(client, f'RCPT TO:{recipient}'))


def main():
    host_addr, client, letter = parse_config()

    user_name_from = client['Login']
    password = client['Password']

    recipients_list = letter['Recipients'].strip().split('\n')
    recipients = recipient_handler(recipients_list)

    subject = letter['Subject']

    attachments_folder = letter['Attachments']
    attachments = os.listdir(attachments_folder)
    attachments = [attachments_folder + '/' + x for x in attachments]

    text_file_name = letter['Text']

    ssl_contex = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ssl_contex.check_hostname = False
    ssl_contex.verify_mode = ssl.CERT_NONE

    with create_connection((host_addr, PORT)) as sock:
        with ssl_contex.wrap_socket(sock, server_hostname=host_addr) as client:
            print(client.recv(1024).decode())  # в smpt сервер первый говорит

            start = datetime.datetime.now()

            print(request(client, f'EHLO {user_name_from}'))
            finish = datetime.datetime.now()
            print(finish - start)

            base64login = base64.b64encode(user_name_from.encode()).decode()

            base64password = base64.b64encode(password.encode()).decode()

            print(request(client, 'AUTH LOGIN'))

            print(request(client, base64login))

            print(request(client, base64password))

            print(request(client, f'MAIL FROM:{user_name_from}'))

            send_all(client, recipients_list)

            print(request(client, 'DATA'))

            print(request(client, message_prepare(user_name_from, recipients, subject, attachments, text_file_name)))


if __name__ == '__main__':
    main()
