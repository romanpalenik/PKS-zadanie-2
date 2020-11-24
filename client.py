import socket
from struct import *

client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
ip_address = input('Zadaj ip adresu')
port = int(input("Zadaj port"))
# send to tam davas ip, port

client_socket.bind((ip_address, port))
data = b'ahoj'
client_socket.sendto(data, (ip_address, port-1))
