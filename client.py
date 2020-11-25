import socket
import os
from struct import *


# function to create socket and send first packet to inicializate com
def client_init():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    ip_address = '192.168.1.15'
    port = int(input("Zadaj port"))
    # send to tam davas ip, port

    # through network you can send only bytes, you have to convert to bytes
    data = pack('!c', 'I'.encode('ascii'))
    client_socket.sendto(data, (ip_address, port))
    return client_socket, ip_address, port


def send_to_server(type_of_packet, send_info):
    if type_of_packet == 'P':
        messege = input("Zadaj spravu")
        # data = pack('c', type_of_packet.encode('ascii')) + messege.encode()
        data = type_of_packet.encode('ascii') + messege.encode()
        send_info[0].sendto(data, (send_info[1], send_info[2]))

    elif type_of_packet == 'M':
        fragment_size = 512
        file = open('img.jpeg', 'rb')
        print(os.path.getsize('img.jpeg'))
        fragment_count = (os.path.getsize('img.jpeg') // 512) + 1  # add +1, becouse // round down, you need has more space
        print(fragment_count)
        start_of_fragment = 0
        end_of_fragment = 512
        # send first packet with information about file and whole sending
        header = 'M'.encode() + pack('!h', fragment_count)
        send_info[0].sendto(header, (send_info[1], send_info[2]))

        for fragment_number in range(fragment_count):

            header = 'M'.encode() + pack('!h', fragment_size) + pack('!h', fragment_number)
            data = header + file.read(fragment_size)
            send_info[0].sendto(data, (send_info[1], send_info[2]))
            start_of_fragment += fragment_size
            end_of_fragment += fragment_size






send_info = client_init()

type_of_packet = input("Zadaj co chces poslat: ")
send_to_server(type_of_packet, send_info)
