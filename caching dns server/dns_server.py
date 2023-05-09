from socket import AF_INET, SOCK_DGRAM, SOL_SOCKET, SO_REUSEADDR
from socket import socket
from collections import defaultdict
from typing import Optional
import time
import pickle
import os

from dnslib import DNSRecord, RCODE

ROOT_SERVER = '77.88.8.1'  # yandex


class Server:
    def __init__(self):
        self.cache = self.initialize_cache()

    @staticmethod
    def initialize_cache() -> dict:
        try:
            with open('.server.pickle', 'rb') as handle:
                data = pickle.load(handle)
                for key, (records, expiration_time) in list(data.items()):
                    if time.time() >= expiration_time:
                        del data[key]

            os.remove('.server.pickle')

            return data

        except FileNotFoundError:
            return dict()

    def save_cache(self):
        with open('.server.pickle', 'wb') as handle:
            pickle.dump(self.cache, handle)

    def add_record_to_cache(self, key: tuple, records: list, ttl: int):
        expiration_time = time.time() + ttl
        self.cache[key] = (records, expiration_time)

    def get_records_from_cache(self, query: DNSRecord) -> Optional[list]:
        key = (query.q.qtype, query.q.qname)
        records_data = self.cache.get(key)

        if records_data:
            records, expiration_time = records_data
            if time.time() < expiration_time:
                return records
            del self.cache[key]

        return None

    def save_response_to_cache(self, response_record: DNSRecord):
        records = defaultdict(list)

        for rr_section in (response_record.rr, response_record.auth, response_record.ar):
            for rr in rr_section:
                records[(rr.rtype, rr.rname)].append(rr)
                print(f'Record from cache: \n{rr}', end='\n\n')
                self.add_record_to_cache((rr.rtype, rr.rname), records[(rr.rtype, rr.rname)], rr.ttl)

    @staticmethod
    def make_response_from_cache(query: DNSRecord, data: bytes) -> DNSRecord:
        response = DNSRecord(header=query.header)
        response.add_question(query.q)
        response.rr += data
        print(f'This rr\'s from cache:\n{response}', end='\n\n')
        return response.pack()

    def parse_query(self, query_data: bytes) -> DNSRecord:
        query = DNSRecord.parse(query_data)
        if extracted_from_cache := self.get_records_from_cache(query):
            return self.make_response_from_cache(query, extracted_from_cache)

        print('No information in cache. I\'ll try ask.')

        response = query.send(ROOT_SERVER, 53, timeout=5)
        response_record = DNSRecord.parse(response)

        print(f'Authorative response drom root server: {response_record}', end='\n\n')

        if response_record.header.rcode == RCODE.NOERROR:  # save to cache if no error
            self.save_response_to_cache(response_record)

        return response


def main():
    dns_server = Server()

    server_socket = socket(AF_INET, SOCK_DGRAM)
    server_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    server_socket.bind(('127.0.0.1', 8000))
    print('Server is up')

    try:
        while True:
            data, addr = server_socket.recvfrom(512)
            response_data = dns_server.parse_query(data)
            if response_data:
                server_socket.sendto(response_data, addr)

    except KeyboardInterrupt:
        print('Work ended')
        dns_server.save_cache()
        print('Cache saved')
        server_socket.close()


if __name__ == '__main__':
    main()
