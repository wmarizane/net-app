# server.py
import socket
import threading
import json
import os
import random
from datetime import datetime


# Configuration
IP = '127.0.0.1'
PORT = 65432
HEADER_LENGTH = 2048
BACK_LOG = 100

# Ensure persistence files exist.
if not os.path.exists('users.json'):
    with open('users.json', 'w') as f:
        json.dump({}, f)
if not os.path.exists('messages.json'):
    with open('messages.json', 'w') as f:
        json.dump([], f)

# Load stored data.
with open('users.json', 'r') as f:
    USERS = json.load(f)
with open('messages.json', 'r') as f:
    MESSAGES = json.load(f)

CLIENTS = {}  # Maps user_id to a dictionary with keys 'socket' and 'username'
lock = threading.Lock()

def save_users():
    with open('users.json', 'w') as f:
        json.dump(USERS, f, indent=4)

def save_messages():
    with open('messages.json', 'w') as f:
        json.dump(MESSAGES, f, indent=4)

def generate_user_id(username):
    while True:
        user_id = f"{username}_{random.randint(1000, 9999)}"
        if user_id not in USERS:
            return user_id

def generate_message_id():
    return f"msg_{random.randint(100000, 999999)}"

def broadcast_message(message, target_user=None):
    """
    If target_user is None, broadcast to all.
    Otherwise, send only to the client whose username matches target_user.
    """
    with lock:
        for uid, client in CLIENTS.items():
            if target_user is None or client['username'] == target_user or uid == message.get("sender"):
                try:
                    client['socket'].send(json.dumps(message).encode('utf-8'))
                except Exception as e:
                    print(f"Error sending message to {client['username']}: {e}")

def handle_client(client_socket, client_address):
    try:
        # Send initial login prompt.
        client_socket.send(json.dumps({"action": "LOGIN"}).encode('utf-8'))
        data = json.loads(client_socket.recv(HEADER_LENGTH).decode('utf-8'))
        username = data.get("username")
        user_id = data.get("user_id", "")
        with lock:
            if user_id in USERS and USERS[user_id]['username'] == username:
                print(f"{username} reconnected with ID {user_id}")
            else:
                user_id = generate_user_id(username)
                USERS[user_id] = {"username": username}
                save_users()
                print(f"New user created: {username} with ID {user_id}")
            CLIENTS[user_id] = {"socket": client_socket, "username": username}

        client_socket.send(json.dumps({"status": "SUCCESS", "user_id": user_id}).encode('utf-8'))

        while True:
            data = json.loads(client_socket.recv(HEADER_LENGTH).decode('utf-8'))
            action = data.get('action')
            if action == 'MESSAGE':
                message_id = generate_message_id()
                receiver = data.get('receiver')
                msg_content = data.get('content')
                # Generate a timestamp.
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                message = {
                    "id": message_id,
                    "sender": user_id,
                    "receiver": receiver,
                    "content": msg_content,
                    "time": timestamp
                }
                with lock:
                    MESSAGES.append(message)
                    save_messages()
                # Then broadcast or send directly as before.
                if receiver.lower() == "all":
                    broadcast_message(message)
                else:
                    broadcast_message(message, target_user=receiver)
            elif action == "EXIT":
                print(f"{username} requested disconnect.")
                with lock:
                    if user_id in CLIENTS:
                        del CLIENTS[user_id]
                break
    except Exception as e:
        print(f"Error with client {client_address}: {e}")
    finally:
        client_socket.close()

def main():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((IP, PORT))
    server_socket.listen(BACK_LOG)
    print(f"Server listening on {IP}:{PORT}")
    while True:
        client_socket, client_address = server_socket.accept()
        threading.Thread(target=handle_client, args=(client_socket, client_address), daemon=True).start()

if __name__ == "__main__":
    main()