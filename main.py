import socket
import os
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
last_packet = -1
is_sending = False
client_info = ('192.168.1.15', 5000)
name_of_file_to_send = 'img.jpeg'
name_of_file_to_save = ''
keep_alive_counter = 0
kill_thread = False


def put_together(packet):
    # to sort packets by number i have to get numbers form packet, therefore i make new packet when i can easily work
    # with numbers, not bytes
    global all_packets
    fragment_size = int.from_bytes(packet[1:3], byteorder='big')
    packet_in_right_form = [packet[0:1], packet[1:3], int.from_bytes(packet[3:5], byteorder='big'),
                            packet[5:5 + fragment_size], packet[5 + fragment_size:]]
    all_packets.append(packet_in_right_form)


def reconstruction_file_from_bytes():
    global all_packets
    all_packets.sort(key=lambda all_packets: all_packets[2])
    path_to_images = '/home/roman/Skola/3semester/PKS/Projekt2/Images'
    os.chdir(path_to_images)
    print(f'Obrazky ukladam {path_to_images} ')
    file2 = open(name_of_file_to_save, 'wb')
    last_packet = -1
    for packet in all_packets:
        if packet[2] == last_packet:
            print("mas tu 2 rovnake bajty")
            continue
        else:
            file2.write(packet[3])  # 3 because it's fourth part in packet and i need data
            last_packet += 1
    all_packets = []
    file2.close()


def reconstruction_message_from_bytes():
    print('idem na rekonstrukciu filu')
    global all_packets
    all_packets.sort(key=lambda all_packets: all_packets[2])
    last_packet = -1
    for packet in all_packets:
        if packet[2] == last_packet:
            print("mas tu 2 rovnake bajty")
            continue
        else:
            print('prijate packety', packet[3])
            print(packet[3].decode())  # 3 because it's fourth part in packet and i need data
            last_packet += 1

    all_packets = []


def control_crc(packet) -> int:
    crc32 = crcmod.mkCrcFun(0x1EDC6F411, rev=False, initCrc=0xFFFFFFFF, xorOut=0x00000000)
    crc_value = crc32(packet)
    return crc_value


def analyze_packet(packet, s_socket):
    global number_packet_in_com, all_packet_number, packet_number_to_simulate_error, is_sending, last_packet, \
        name_of_file_to_save, keep_alive_counter

    type_of_packet = packet[0:1].decode('ascii')

    if type_of_packet == 'I':
        keep_alive_counter = 0
        s_socket.settimeout(15)
        print('Spojenie bolo inicializovane')
        init_packet = pack('!c', 'I'.encode('ascii'))
        s_socket.sendto(init_packet, client_info)

    elif type_of_packet == 'M' or type_of_packet == 'P':
        is_sending = True
        keep_alive_counter = 0
        s_socket.settimeout(15)
        # fist packet with information of file
        if number_packet_in_com == 0:
            all_packet_number = int.from_bytes(packet[3:5], byteorder='big')
            name_of_file_to_save = packet[5:]
        else:
            # control if packet is alright
            if control_crc(packet) != 0:
                print('chyba je v ', number_packet_in_com)
                error_message = pack('!c', 'E'.encode('ascii'))
                s_socket.sendto(error_message, client_info)
                return True
            else:
                if int.from_bytes(packet[3:5], byteorder='big') != last_packet:
                    last_packet += 1
                    put_together(packet)
                else:
                    print('prisiel znova packet')
                    all_packet_number += 1

        # this block run if all packets were sent
        if number_packet_in_com == all_packet_number:
            is_sending = False
            print("Prebehlo poslanie jedneho suboru", number_packet_in_com)

            right_packet = pack('!c', 'O'.encode('ascii'))
            s_socket.sendto(right_packet, client_info)

            if type_of_packet == 'M':
                reconstruction_file_from_bytes()
            elif type_of_packet == 'P':
                reconstruction_message_from_bytes()
            number_packet_in_com = 0
            all_packet_number = 0
            last_packet = -1
            return False

        number_packet_in_com += 1
        # packet is right

        # simulating error, that acknowledgment was lost

        if number_packet_in_com == 3:
            print("neposielam ACK")
            return True

        right_packet = pack('!c', 'O'.encode('ascii'))
        s_socket.sendto(right_packet, client_info)

    elif type_of_packet == 'K':
        right_packet = pack('!c', 'K'.encode('ascii'))
        s_socket.sendto(right_packet, client_info)
        print('prislo keeepalive')
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
                print(is_sending)
                print('prave nepocuvam keepalive')
                pass
            else:
                login = analyze_packet(packet, s_socket)

            if keep_alive_counter > 3:
                print('Nic sa neposiela vypinam server')
                return


        except socket.timeout:
            print('Skoncil server')
            return


### client function

# function to create socket and send first packet to initialize com
def client_init():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    ip_address = input("Zadaj Ip servera")
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
    fragment_size = 512

    if type_of_packet == 'P':
        message = input("Zadaj spravu")
        message = message.encode()
        fragment_count = (len(message) // fragment_size) + 1

        star_of_fragment = 0
        end_of_fragment = fragment_size

        print(f'Bude {fragment_count} fragmentov')

        header = 'P'.encode() + pack('!h', fragment_size) + pack('!h', fragment_count)
        send_info[0].sendto(header, (send_info[1], send_info[2]))

        for fragment_number in range(fragment_count):

            data = message[star_of_fragment:end_of_fragment]

            # if is message smaller than fragment size, is that size recount
            if len(data) <= fragment_size:
                fragment_size = len(data)

            header = 'P'.encode() + pack('!h', fragment_size) + pack('!h', fragment_number)
            data = header + data
            data = create_crc(data)

            # simulating error that one packet is lost
            if fragment_number != 3:
                # add error - data is corupted
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

            star_of_fragment += fragment_size
            end_of_fragment += fragment_size

    elif type_of_packet == 'M':

        file = open(name_of_file_to_send, 'rb')
        fragment_count = (os.path.getsize(
            name_of_file_to_send) // fragment_size) + 1  # add +1, because // round down, you need has more space

        # send first packet with information about file and whole sending
        header = 'M'.encode() + pack('!h', fragment_size) + pack('!h', fragment_count) + name_of_file_to_send.encode()
        send_info[0].sendto(header, (send_info[1], send_info[2]))

        check_packet, address = send_info[0].recvfrom(1500)
        type_of_packet = check_packet[0:1].decode('ascii')

        if type_of_packet == 'O':
            pass

        print(f'Bude {fragment_count} fragmentov')
        
        for fragment_number in range(fragment_count):

            header = 'M'.encode() + pack('!h', fragment_size) + pack('!h', fragment_number)
            data = header + file.read(fragment_size)
            data = create_crc(data)

            # simulating error that one packet is lost
            if fragment_number != 3:
                # add error - data is corupted
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
    global kill_thread
    while True:
        keep_alive_packet = pack('!c', 'K'.encode('ascii'))
        send_info[0].sendto(keep_alive_packet, (send_info[1], send_info[2]))
        if kill_thread:
            return

        while True:

            # if connection throws error that means, server is not connected
            try:
                packet, address = send_info[0].recvfrom(1500)
                type_of_packet = packet[0:1].decode('ascii')
                if type_of_packet == 'K':
                    send_info[0].settimeout(15)
                    break
            except socket.timeout:
                print('Server sa odpojil')
                kill_thread = True
                return

        time.sleep(keep_alive_time)


### main
def main():
    global client_info, kill_thread
    role = int(input("Zadaj 1 pre server: \nZadaj 2 pre clienta: \n3.Odhlasit sa\n:"))
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
                #problem
                type_of_packet = input("Zadaj co chces poslat: ")
                add_error = int(input("Zadaj ci chces pridat chybu: "))
                send_to_server(type_of_packet, send_info, add_error)

            elif choice == 3:
                keep_alive_thread.join()

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
                kill_thread = True
                keep_alive_thread.join()
                client_info = ('192.168.1.15', 9000)
                print("Server ide")
                send_info[0].settimeout(15)
                server_listen(send_info[0])

            elif choice == 2:
                type_of_packet = input("Zadaj co chces poslat: ")
                add_error = int(input("Zadaj ci chces pridat chybu: "))
                send_to_server(type_of_packet, send_info, add_error)

            elif choice == 3:
                kill_thread = True
                keep_alive_thread.join()

    elif role == 3:
        return

main()
