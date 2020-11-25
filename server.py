import socket
from binascii import hexlify

all_packets = []
number_packet_in_com = 0


def put_together(packet):
    global all_packets
    all_packets.append(packet)


def analyze_packet(packet):
    global number_packet_in_com
    type_of_packet = packet[0:1].decode('ascii')
    if type_of_packet == 'I':
        print('Spojenie bolo inicializovane')
    elif type_of_packet == 'P':
        print('Je to porno')
        print('oh Gott, schneller')
        print(packet[1:])
    elif type_of_packet == 'M':
        # fist packet with information of file

        if number_packet_in_com == 0:
            all_packet_number = packet[1:10]
            print(packet)
            print(all_packet_number)
            print(int.from_bytes(all_packet_number, byteorder='big'))
        else:
            put_together(packet)

        number_packet_in_com += 1


def server_listen(port, s_socket):
    while True:
        print("Server is listening")

        packet, address = s_socket.recvfrom(1500)
        analyze_packet(packet)


port = int(input("Zadaj server port: "))

s_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s_socket.bind(('', port))

print("Spojenie bolo nastavene")

server_listen(port, s_socket)
