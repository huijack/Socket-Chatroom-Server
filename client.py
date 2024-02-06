import threading
import socket

alias = input("Choose an alias >>> ")

HEADER = 64
PORT = 5050
FORMAT = 'utf-8'
DISCONNECT_MESSAGE = "!DISCONNECT"
SERVER = "192.168.1.112"
ADDR = (SERVER, PORT)


client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect(ADDR)


def client_receive():
    while True:
        try:
            message = client.recv(2048).decode(FORMAT)
            if message == 'alias?':
                client.send(alias.encode(FORMAT))
            else:
                print(message)
        except:
            print("An error occurred!")
            client.close()
            break


def client_send():
    while True:
        message = f'{alias}: {input("")}'
        client.send(message.encode(FORMAT))


receive_thread = threading.Thread(target=client_receive)
receive_thread.start()

send_thread = threading.Thread(target=client_send)
send_thread.start()