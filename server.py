# server.py
import socket
import threading
import json
import os
import random
import ssl
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

with open('users.json', 'r') as f:
    USERS = json.load(f)
with open('messages.json', 'r') as f:
    MESSAGES = json.load(f)

# A dictionary mapping user_id to a dict: {'socket': client_socket, 'username': username}
CLIENTS = {}
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
    Sends the given JSON message to all connected clients.
    If target_user is provided, it will check if client's username matches target_user 
    or if the client is the sender, and send only to those.
    (Used in our initial implementation for direct messaging.)
    """
    with lock:
        for uid, client in CLIENTS.items():
            # In our refresh approach we want all clients to update.
            try:
                client['socket'].send(json.dumps(message).encode('utf-8'))
            except Exception as e:
                print(f"Error sending message to {client['username']}: {e}")

def broadcast_refresh():
    """
    Broadcasts a refresh event to all clients.
    The refresh event includes the full messages list.
    """
    refresh_event = {
        "action": "REFRESH",
        "messages": MESSAGES
    }
    broadcast_message(refresh_event)

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
        # Send login confirmation.
        client_socket.send(json.dumps({"status": "SUCCESS", "user_id": user_id}).encode('utf-8'))
        # Immediately send a refresh event with all past messages.
        client_socket.send(json.dumps({"action": "REFRESH", "messages": MESSAGES}).encode('utf-8'))

        while True:
            data = json.loads(client_socket.recv(HEADER_LENGTH).decode('utf-8'))
            action = data.get('action')
            if action == 'MESSAGE':
                message_id = generate_message_id()
                receiver = data.get('receiver')
                msg_content = data.get('content')
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
                # For both broadcast and direct messages, we refresh every client.
                broadcast_refresh()
            elif action == "DELETE":
                message_id = data.get("id")
                sender_from_client = data.get("sender")
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                with lock:
                    message_to_delete = None
                    for msg in MESSAGES:
                        if msg.get("id") == message_id:
                            message_to_delete = msg
                            break
                    if not message_to_delete:
                        client_socket.send(json.dumps({"error": f"Message ID {message_id} not found."}).encode('utf-8'))
                        continue
                    if message_to_delete.get("sender") != sender_from_client:
                        client_socket.send(json.dumps({"error": "You are not authorized to delete this message."}).encode('utf-8'))
                        continue
                    MESSAGES.remove(message_to_delete)
                    save_messages()
                # Broadcast a refresh event after deletion.
                broadcast_refresh()
            elif action == "EXIT":
                print(f"{username} requested disconnect.")
                with lock:
                    if user_id in CLIENTS:
                        del CLIENTS[user_id]
                # Optionally, broadcast a refresh here, though messages list remains unchanged.
                broadcast_refresh()
                break
    except Exception as e:
        print(f"Error with client {client_address}: {e}")
    finally:
        client_socket.close()

def main():

    #TLS/SSL
    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    context.load_cert_chain(certfile='cert.pem', keyfile='key.pem')

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((IP, PORT))
    server_socket.listen(BACK_LOG)
    print(f"Server listening on {IP}:{PORT}")

    with context.wrap_socket(server_socket, server_side=True) as tls_server:
        while True:
            client_socket, client_address = tls_server.accept()
            threading.Thread(target=handle_client, args=(client_socket, client_address), daemon=True).start()

if __name__ == "__main__":
    main()