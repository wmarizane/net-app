import socket
import threading
import random

# Server configuration
IP = '127.0.0.1'
PORT = 65432
HEADER_LENGTH = 2048
BACK_LOG = 100

# Dictionary to store clients and groups
clients = {}
groups = {"general": set()}

# Create a lock with 2 statuses: locked and unlocked
lock = threading.Lock()

def receive_message(client_socket):
    try:
        message_header = client_socket.recv(HEADER_LENGTH)
        if not len(message_header):
            return False
        
        message_length = int(message_header.decode('utf-8').strip())
        return {'header': message_header, 'data': client_socket.recv(message_length)}
    except:
        return False

def broadcast_message(sender_socket, message):
    with lock:
        user = clients[sender_socket]
        for client_socket in clients.keys():
            if client_socket != sender_socket:
                try:
                    client_socket.send(user['header'] + user['data'] + message['header'] + message['data'])
                except:
                    remove_connection(client_socket)

def generate_unique_id(name):
    while True:
        random_number = random.randint(1000, 9999)
        uid = f"{name}_{random_number}"
        isDuplicate = any(user['data'].decode('utf-8') == uid for user in clients.values())
        if not isDuplicate:
            return uid

def remove_connection(removed_socket):
    with lock:
        if removed_socket in clients:
            user_data = clients[removed_socket]['data'].decode('utf-8')
            del clients[removed_socket]
            print(f"{user_data} disconnected")
    removed_socket.close()

def add_new_client(client_socket):
    prompt = "Please enter a username: ".encode('utf-8')
    prompt_header = f"{len(prompt):<{HEADER_LENGTH}}".encode('utf-8')
    client_socket.send(prompt_header + prompt)

    reply = receive_message(client_socket)
    if not reply:
        print("Client disconnected or sent invalid data.")
        return None

    user_name = reply['data'].decode('utf-8')
    uid = generate_unique_id(user_name)

    user_data = uid.encode('utf-8')
    user_header = f"{len(user_data):<{HEADER_LENGTH}}".encode('utf-8')
    user = {'header': user_header, 'data': user_data}

    return user

def handle_client(client_socket, client_address):
    user = add_new_client(client_socket)
    if not user:
        return

    with lock:
        clients[client_socket] = user
        groups['general'].add(client_socket)
    print(f"New connection from {client_address}, username: {user['data'].decode('utf-8')}")

    while True:
        message = receive_message(client_socket)
        if not message:
            return

        msg_data = message['data'].decode('utf-8').strip()
        if ':' in msg_data:
            recipient, msg_text = msg_data.split(':', 1)
            msg_text = msg_text.strip()

            with lock:
                if recipient == 'group':
                    print(f"[Group] {user['data'].decode('utf-8')}: {msg_text}")
                    broadcast_message(client_socket, message)
                elif recipient in [u['data'].decode('utf-8') for u in clients.values()]:
                    print(f"[DM] {user['data'].decode('utf-8')} -> {recipient}: {msg_text}")
                    for sock, u in clients.items():
                        if u['data'].decode('utf-8') == recipient:
                            try:
                                sock.send(user['header'] + user['data'] + message['header'] + message['data'])
                            except:
                                remove_connection(sock)
                else:
                    print(f"User {recipient} not found.")
                    error_message = "User not found.".encode('utf-8')
                    client_socket.send(f"{len(error_message):<{HEADER_LENGTH}}".encode('utf-8') + error_message)
        else:
            print(f"Invalid message format from {user['data'].decode('utf-8')}.")

def main():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((IP, PORT))
    server_socket.listen(BACK_LOG)

    print(f"Server running on {IP}:{PORT}")

    while True:
        client_socket, client_address = server_socket.accept()
        client_handler = threading.Thread(target=handle_client, args=(client_socket, client_address), daemon=True)
        client_handler.start()

if __name__ == '__main__':
    main()
