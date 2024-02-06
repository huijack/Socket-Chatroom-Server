import socket
import threading

HEADER = 64
PORT = 5050
SERVER = socket.gethostbyname(socket.gethostname())
ADDR = (SERVER, PORT)
FORMAT = 'utf-8'
DISCONNECT_MESSAGE = "!DISCONNECT"

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(ADDR)
server.listen()
clients = []
aliases = []


def broadcast(message):
    for client in clients:
        client.send(message)

# Function to handle clients' connections
def handle_client(client):
    while True:
        try:
            message = client.recv(2048)
            broadcast(message)
        except:
            index = clients.index(client)
            clients.remove(client)
            client.close()
            alias = aliases[index]
            broadcast(f'{alias} has left the chat room!'.encode(FORMAT))
            aliases.remove(alias)
            break


# Main function to receive the clients' connections
def receive():
    while True:
        print("Server is running and listening...")
        client, address = server.accept()
        print(f"Connection is established with {str(address)}")

        client.send('alias?'.encode(FORMAT))
        alias = client.recv(2048)
        aliases.append(alias)
        clients.append(client)

        print(f"The alias of this client is {alias}".encode(FORMAT))
        broadcast(f"{alias} has connected to the chat room".encode(FORMAT))
        client.send('You are now connected!'.encode(FORMAT))

        thread = threading.Thread(target=handle_client, args=(client,))
        thread.start()
        print(f"[ACTIVE CONNECTIONS] {threading.active_count() - 1}")

if __name__ == "__main__":
    receive()
