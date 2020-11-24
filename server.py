import socket


def server_listen(port, s_socket):
    while True:
        print("Server is listening")

        message, addres = s_socket.recvfrom(1500)

        print("Sprava je", message)



host = socket.gethostname()
port = int(input("Zadaj server port: "))

s_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s_socket.bind((host, port))

print("Spojenie bolo nastavene")

server_listen(port, s_socket)