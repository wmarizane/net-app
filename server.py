# server.py
import socket
import threading
import json
import os
import random
import ssl
import time
from datetime import datetime

# Configuration
IP = '127.0.0.1'
PORT = 65432
HEADER_LENGTH = 2048
BACK_LOG = 100
TIME_TO_LIVE = 10
INTERVAL = 5
USED_MSSG_ID = set()
# A dictionary mapping user_id to a dict: {'socket': client_socket, 'username': username}
CLIENTS = {}
MESSAGES = {}

lock = threading.Lock()

# Ensure persistence files exist.
if not os.path.exists('users.json'):
    with open('users.json', 'w') as f:
        json.dump({}, f)

# Create directories for storing user message
if not os.path.exists('message_db'):
    os.makedirs('message_db')

    # with open('messages.json', 'w') as f:
    #     json.dump([], f)

with open('users.json', 'r') as f:
    USERS = json.load(f)
# with open('messages.json', 'r') as f:
#     MESSAGES = json.load(f)

def create_client_message_folder(user_id):
    data = {
        'send': [],
        'receive': []
    }
    with open(f'./message_db/{user_id}.json', 'w') as f:
        json.dump(data, f, indent=4)

def save_users():
    with open('users.json', 'w') as f:
        json.dump(USERS, f, indent=4)

def save_messages():
    with open('messages.json', 'w') as f:
        json.dump(MESSAGES, f, indent=4)

def generate_user_id(username):
    return f"{username}_{random.randint(1000, 9999)}"

def generate_message_id():
    return f"{random.randint(100000, 999999)}"



def broadcast_message(user,message):
    try:
        user['socket'].send(json.dumps(message).encode('utf-8'))
    except Exception as e:
                print(f"Error sending message to {user['username']}: {e}")

def remove_connection(client_id):
    with lock:
        if client_id in CLIENTS:
            client_socket = CLIENTS[client_id]['socket']
            print(f"Removing client: {client_id}")
            del CLIENTS[client_id]
            try:
                client_socket.close()
            except Exception as e:
                print(f"Error closing client socket {client_id}: {e}")

def update_active_client_list():
    data = {
            "id": None,
            "action": 'ACTIVE_CLIENT',
            "sender": None,
            "receiver": None,
            "content": None,
            "time": None,
            "private": False,
    }
        
    for client_id in list(CLIENTS.keys()):
        sending_list = [id for id in list(CLIENTS.keys()) if id != client_id]
        data['receiver'] = sending_list #Assign active client list for receiver to make it easier
        broadcast_message(CLIENTS[client_id],data)


def clean_expired_message(ttl = TIME_TO_LIVE):
    now = time.time()
    global MESSAGES
    with lock:
        for client_msg in MESSAGES:

            for msg in MESSAGES[client_msg]['send']:
                mssg_timestamp = datetime.strptime(msg['time'],"%Y-%m-%d %H:%M:%S").timestamp()

                if msg['action'] == 'TEMPORARY' and (now - mssg_timestamp) > ttl:
                    msg_id = msg['id']
                    receiver_list = msg['receiver'][:]
                    sending_list = receiver_list + [msg['sender']]

                    data = {
                        "id": None,
                        "action": 'OUTDATED',
                        "sender": None,
                        "receiver": None,
                        "content": msg['id'],
                        "time": None,
                        "private": False,
                    }

                    for msg_receiver in receiver_list:
                        if msg_receiver in MESSAGES:
                            for m in MESSAGES[msg_receiver]['receive']:
                                if m['id'] == msg_id:
                                    msg['content'] = 'THIS MESSAGE IS EXPIRED.'
                                    msg['action'] = 'DELETE'
                                    

                    for client_id in sending_list:
                        if client_id in CLIENTS:
                            broadcast_message(CLIENTS[client_id],data)

                    



def cleanup_loop(interval=INTERVAL, ttl=TIME_TO_LIVE):
    while True:
        clean_expired_message(ttl=ttl)
        time.sleep(interval)  # Wait before running again
                        

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
                # Check unique user_id
                # Generrate client's ID until the client's ID is unique
                while True:
                    user_id = generate_user_id(username)
                    if user_id not in CLIENTS:
                        break
            
                USERS[user_id] = {"username": username}
                save_users()
                print(f"New user created: {username} with ID {user_id}")
            CLIENTS[user_id] = {"socket": client_socket, "username": username}
            MESSAGES[user_id] = {
                'send' : [],
                'receive' : []
            }
            create_client_message_folder(user_id=user_id)

        # Send login confirmation.
        client_socket.send(json.dumps({"status": "SUCCESS", "user_id": user_id}).encode('utf-8'))
        
        update_active_client_list()
        

        while True:
            data = json.loads(client_socket.recv(HEADER_LENGTH).decode('utf-8'))
            action = data.get('action')
            #TEST DATA
            #print(data)
            if not data:    
                print("Client {client_address} disconnected")
                remove_connection(user_id)
                update_active_client_list()
                break

            #HANDLE RECEIVING MESSAGE
            if action == 'MESSAGE' or action == 'TEMPORARY':
                
                # Check unique message_id
                # Generate ID until the message ID is unique
                message_id = None
                with lock:
                    while(True):
                        message_id = generate_message_id()
                        if message_id not in USED_MSSG_ID:
                            USED_MSSG_ID.add(message_id)
                            break

                receiver = data.get('receiver')
                
                
                data['id'] = message_id
                sending_list = []
                if "all" in receiver:
                    sending_list =list(CLIENTS.keys())
                    data['receiver'] = [uid for uid in sending_list if uid != user_id]
                else:
                    #Send toward ACTIVE user
                    sending_list = list(set(receiver) & set(CLIENTS.keys())) + [user_id]


                with lock:
                    for client_id in sending_list:
                        if client_id == user_id:
                            MESSAGES[user_id]['send'].append(data)
                        else:
                            MESSAGES[client_id]['receive'].append(data)
                
                for client_id in sending_list:
                    broadcast_message(CLIENTS[client_id],message=data)
            elif action == "REPLY":
                
                message_id = None

                with lock:
                    while(True):
                        message_id = generate_message_id()
                        if message_id not in USED_MSSG_ID:
                            USED_MSSG_ID.add(message_id)
                            break
                
                # data = {
                #         "id": None,
                #         "action": 'REPLY',
                #         "sender": sender_id,
                #         "receiver": receivers,
                #         "content": msg_content,
                #         "time": None,
                #         "private": False,
                #         "optional": msg_id_replied
                # }

                data['id'] = message_id
                
                sending_list = data["receiver"]

                with lock:
                    for client_id in sending_list:
                        if client_id == user_id:
                            MESSAGES[user_id]['send'].append(data)
                        else:
                            MESSAGES[client_id]['receive'].append(data)

                for client_id in sending_list:
                    
                    broadcast_message(CLIENTS[client_id],message=data)
                    


            elif action == "DELETE":
                message_id = data['content']
                sender_id = data['sender']
                
                with lock:
                    message_to_delete = False
                    for msg in MESSAGES[sender_id]['send']:
                        if message_id == msg['id']:
                            msg['content'] = 'THIS MESSAGE IS REMOVED'
                            sending_list = msg['receiver'][:] + [sender_id]
                            for client_id in sending_list:
                                broadcast_message(CLIENTS[client_id],message=data)
                            message_to_delete = True
                            break

                    if message_to_delete == False:
                        client_socket.send(json.dumps({"error": f"Message ID {message_id} not found or belong to the user."}).encode('utf-8'))
                        continue


            elif action == "EXIT":
                print(f"{username} requested disconnect.")
                remove_connection(user_id)
                update_active_client_list()
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
        threading.Thread(target=cleanup_loop, daemon=True).start()
        while True:
            client_socket, client_address = tls_server.accept()
            threading.Thread(target=handle_client, args=(client_socket, client_address), daemon=True).start()

if __name__ == "__main__":
    main()