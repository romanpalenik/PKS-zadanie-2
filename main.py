import socket
import os
from time import perf_counter
from struct import *
import threading
import time
import crcmod
import copy

all_packets = []
number_packet_in_com = 0
all_packet_number = 0
keep_alive_time = 5
packet_number_to_simulate_error = 0
is_sending = False


def put_together(packet):
    # to sort packets by number i have to get numbers form packet, therefore i make new packet when i can easily work
    # with numbers, not bytes
    global all_packets
    fragment_size = int.from_bytes(packet[1:3], byteorder='big')
    packet_in_right_form = [packet[0:1], packet[1:3], int.from_bytes(packet[3:5], byteorder='big'),
                            packet[5:5 + fragment_size], packet[5 + fragment_size:]]
    all_packets.append(packet_in_right_form)


def reconstruction_from_bytes():
    global all_packets
    all_packets.sort(key=lambda all_packets: all_packets[2])
    file2 = open('img2.jpeg', 'wb')
    last_packet = -1
    for packet in all_packets:
        if packet[2] == last_packet:
            continue
        else:
            file2.write(packet[3])  # 3 because it's fourth part in packet and i need data
            last_packet += 1

    file2.close()


def control_crc(packet) -> int:
    crc32 = crcmod.mkCrcFun(0x1EDC6F411, rev=False, initCrc=0xFFFFFFFF, xorOut=0x00000000)
    crc_value = crc32(packet)
    return crc_value


def analyze_packet(packet, s_socket):
    global number_packet_in_com, all_packet_number, packet_number_to_simulate_error
    type_of_packet = packet[0:1].decode('ascii')

    if type_of_packet == 'I':
        s_socket.settimeout(15)
        print('Spojenie bolo inicializovane')
        init_packet = pack('!c', 'I'.encode('ascii'))
        s_socket.sendto(init_packet, ('192.168.1.15', 5000))

    elif type_of_packet == 'P':
        s_socket.settimeout(15)
        print('Je to porno')
        print('oh Gott, schneller')
        print(packet[1:])
        return False

    elif type_of_packet == 'M':
        s_socket.settimeout(15)
        # fist packet with information of file
        if number_packet_in_com == 0:
            all_packet_number = int.from_bytes(packet[3:5], byteorder='big')
        else:
            # control if packet is alright
            if control_crc(packet) != 0:
                print('chyba je v ', number_packet_in_com)
                error_message = pack('!c', 'E'.encode('ascii'))
                s_socket.sendto(error_message, ('192.168.1.15', 5000))
                return True
            else:
                put_together(packet)

        # this block run if all packets were sent
        if number_packet_in_com == all_packet_number:
            print("Prebehlo poslanie jedneho suboru", number_packet_in_com)

            right_packet = pack('!c', 'O'.encode('ascii'))
            s_socket.sendto(right_packet, ('192.168.1.15', 5000))

            right_packet = pack('!c', 'O'.encode('ascii'))
            s_socket.sendto(right_packet, ('192.168.1.15', 5000))

            reconstruction_from_bytes()
            number_packet_in_com = 0
            return False

        number_packet_in_com += 1
        # packet is right

        # simulating error, that acknowledgment was lost
        if number_packet_in_com == 3:
            print("neposielam ACK")
            return True

        right_packet = pack('!c', 'O'.encode('ascii'))
        s_socket.sendto(right_packet, ('192.168.1.15', 5000))

    elif type_of_packet == 'K':
        s_socket.settimeout(15)

    return True


def server_listen(s_socket):
    login = True
    while login:
        try:
            # if server is in middle sending process ignore keep alive, you need timeout for missing packets
            packet, address = s_socket.recvfrom(1500)
            type_of_packet = packet[0:1].decode('ascii')
            if is_sending == True and type_of_packet == 'K':
                pass
            else:
                login = analyze_packet(packet, s_socket)
        except TimeoutError:
            s_socket.settimeout(15)
            if is_sending:
                error_message = pack('!c', 'E'.encode('ascii'))
                s_socket.sendto(error_message, ('192.168.1.15', 5000))
            print('Skoncil server')
            return


### client function

# function to create socket and send first packet to initialize com
def client_init():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    ip_address = '192.168.1.15'
    port = int(input("Zadaj port servera: "))
    client_port = 5000
    client_socket.bind(('', client_port))
    # send to tam davas ip, port

    # through network you can send only bytes, you have to convert to bytes
    data = pack('!c', 'I'.encode('ascii'))
    client_socket.sendto(data, (ip_address, port))
    check_packet, address = client_socket.recvfrom(1500)

    # check if connection is enable
    type_of_packet = check_packet[0:1].decode('ascii')
    if type_of_packet == 'I':
        print('Server pocuva')
    else:
        print('Niekde nastala chyba')

    return client_socket, ip_address, port


def create_crc(packet) -> list:
    crc16 = crcmod.mkCrcFun(0x1EDC6F411, rev=False, initCrc=0xFFFFFFFF, xorOut=0x00000000)
    crc_value = crc16(packet)
    return packet + pack('!L', crc_value)


def send_to_server(type_of_packet, send_info, add_error):
    if type_of_packet == 'P':
        message = input("Zadaj spravu")
        data = type_of_packet.encode('ascii') + message.encode()
        data = create_crc(data)
        send_info[0].sendto(data, (send_info[1], send_info[2]))

    elif type_of_packet == 'M':

        fragment_size = 512
        file = open('img.jpeg', 'rb')
        fragment_count = (os.path.getsize(
            'img.jpeg') // fragment_size) + 1  # add +1, because // round down, you need has more space
        print(fragment_count)

        # send first packet with information about file and whole sending
        header = 'M'.encode() + pack('!h', fragment_size) + pack('!h', fragment_count)
        send_info[0].sendto(header, (send_info[1], send_info[2]))

        check_packet, address = send_info[0].recvfrom(1500)
        type_of_packet = check_packet[0:1].decode('ascii')

        if type_of_packet == 'O':
            pass

        for fragment_number in range(fragment_count):

            header = 'M'.encode() + pack('!h', fragment_size) + pack('!h', fragment_number)
            data = header + file.read(fragment_size)
            data = create_crc(data)

            # add error
            if fragment_number == 3 and add_error == 1:
                data = bytearray(data)
                corrupted_data = copy.deepcopy(data)
                corrupted_data[2] = data[2] + 1
                send_info[0].sendto(corrupted_data, (send_info[1], send_info[2]))
            else:
                send_info[0].sendto(data, (send_info[1], send_info[2]))

            # waiting if packet is alright
            while True:

                try:
                    send_info[0].settimeout(5)
                    check_packet, address = send_info[0].recvfrom(1500)

                except socket.timeout:
                    print('Neprisiel acknolegment z {}. packetu'.format(fragment_number + 2))
                    send_info[0].sendto(data, (send_info[1], send_info[2]))
                    continue

                # right packet continue, wrong send again

                type_of_packet = check_packet[0:1].decode('ascii')
                if type_of_packet == 'O':
                    break

                elif type_of_packet == 'E':
                    print("Chyba bola v {} packetu".format(fragment_number))
                    send_info[0].sendto(data, (send_info[1], send_info[2]))

        file.close()


def send_keepalive(send_info):
    while True:
        time.sleep(keep_alive_time)
        keep_alive_packet = pack('!c', 'K'.encode('ascii'))
        send_info[0].sendto(keep_alive_packet, (send_info[1], send_info[2]))


### main
def main():
    role = int(input("Zadaj 1 pre server: \nZadaj 2 pre clienta: \n3.Ukoncit\n:"))
    s_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    if role == 1:
        port = int(input("Zadaj server port: "))
        s_socket.settimeout(15)
        s_socket.bind(('', port))
        print("Server ide")
        server_listen(s_socket)

        while True:
            choice = int(input('Chces byt stale server?'))
            if choice == 1:
                server_listen(s_socket)

            elif choice == 2:
                send_info = (s_socket, '192.168.1.15', 5000)

                keep_alive_thread = threading.Thread(target=send_keepalive, args=(send_info,))
                keep_alive_thread.start()

                type_of_packet = input("Zadaj co chces poslat: ")
                add_error = int(input("Zadaj ci chces pridat chybu: "))
                send_to_server(type_of_packet, send_info, add_error)

    elif role == 2:

        send_info = client_init()
        print(send_info)
        keep_alive_thread = threading.Thread(target=send_keepalive, args=(send_info,))
        keep_alive_thread.start()
        type_of_packet = input("Zadaj co chces poslat: ")
        add_error = int(input("Zadaj ci chces pridat chybu: "))
        send_to_server(type_of_packet, send_info, add_error)

        while True:
            choice = int(input('Chces byt stale client?'))
            if choice == 1:
                print("Server ide")
                server_listen(send_info[0])

            elif choice == 2:
                type_of_packet = input("Zadaj co chces poslat: ")
                add_error = int(input("Zadaj ci chces pridat chybu: "))
                send_to_server(type_of_packet, send_info, add_error)


main()
