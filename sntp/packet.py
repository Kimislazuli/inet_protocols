import struct
import time


class SNTPPacket:
    def __init__(self,
                 leap_indicator=0,
                 version_number=3,
                 mode=3,
                 stratum=0,
                 poll=0,
                 precision=0,
                 root_delay=0,
                 root_dispersion=0,
                 reference_id=0,
                 reference_timestamp=0,
                 originate_timestamp=0,
                 receive_timestamp=0,
                 transmit_timestamp=0
                 ):
        self._leap_indicator = leap_indicator
        self._version_number = version_number
        self._mode = mode
        self._stratum = stratum
        self._poll = poll
        self._precision = precision
        self._root_delay = root_delay
        self._root_dispersion = root_dispersion
        self._reference_id = reference_id
        self._reference_timestamp = reference_timestamp
        self._originate_timestamp = originate_timestamp
        self._receive_timestamp = receive_timestamp
        self._transmit_timestamp = transmit_timestamp

    def to_bytes(self):
        return struct.pack('!B B B b 11I',
                           (self._leap_indicator << 6 | self._version_number << 3 | self._mode),
                           self._stratum,
                           self._poll,
                           self._precision,
                           self._root_delay,
                           self._root_dispersion,
                           self._reference_id,
                           int(self._reference_timestamp),
                           self._frac(self._reference_timestamp),
                           int(self._originate_timestamp),
                           self._frac(self._originate_timestamp),
                           int(self._receive_timestamp),
                           self._frac(self._receive_timestamp),
                           int(self._transmit_timestamp),
                           self._frac(self._transmit_timestamp))

    @classmethod
    def from_bytes(cls, byte_data):
        values = struct.unpack('!B B B b 11I', byte_data)

        # Разбор значений и создание объекта класса SNTPPacket
        packet = cls()
        packet._leap_indicator = (values[0] >> 6) & 0x03
        packet._version_number = (values[0] >> 3) & 0x07
        packet._mode = values[0] & 0x07
        packet._stratum = values[1]
        packet._poll = values[2]
        packet._precision = values[3]
        packet._root_delay = values[4]
        packet._root_dispersion = values[5]
        packet._reference_id = values[6]
        packet._reference_timestamp = values[7] + packet._frac(values[8])
        packet._originate_timestamp = values[9] + packet._frac(values[10])
        packet._receive_timestamp = values[11] + packet._frac(values[12])
        packet._transmit_timestamp = values[13] + packet._frac(values[14])

        return packet

    @staticmethod
    def _frac(timestamp):
        return int(abs(timestamp - timestamp) * 2 ** 32)

    @staticmethod
    def current_timestamp():
        timestamp = int(
            time.time()) + 2208988800
        return timestamp >> 32, timestamp & 0xFFFFFFFF

    def __str__(self):
        return f"""
        leap indicator: {self._leap_indicator}, 
        version number: {self._version_number}, 
        mode: {self._mode}, 
        stratum: {self._stratum}, 
        poll: {self._poll}, 
        precision: {self._precision}, 
        root delay: {self._root_delay}, 
        root dispersion: {self._root_dispersion}, 
        reference id: {self._reference_id}, 
        reference timestamp: {self._reference_timestamp}, 
        originate timestamp: {self._originate_timestamp}, 
        receive timestamp: {self._receive_timestamp}, 
        transmit timestamp: {self._transmit_timestamp}
        """
