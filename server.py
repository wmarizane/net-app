import socket
import select
import json
from _thread import *
import threading
import time
import random

'''
MESSAGE FORMAT
    {
        'sender'
        'receiver'
        'content'
        'ID'
        'method' {
            'action'
            'ID'
        }
    }
'''

# A simple code to get the host name of local machine and its IP address
# host_name = socket.gethostname()
# ip_address = socket.gethostbyname(host_name)
# print(ip_address)

IP = '127.0.0.1'
PORT = 12000
HEADER_LENGTH = 2048
BACK_LOG = 100

##Dictionary to store clients
CLIENTS = {}
IS_CLIENTS_CHANGED = True

#create a lock with 2 status: locked and unlocked
lock = threading.Lock()

def receive_message(socket):
    try:
        data = socket.recv(HEADER_LENGTH).decode('utf-8')
        if not data:
            # No data received means the client has disconnected
            return None
        return json.loads(data)
    except (ConnectionResetError, ConnectionAbortedError, OSError):
        # Handle when the client disconnects abruptly
        return None

def broadcast_message(socket,message):
    """
        socket: socket of receiver
    """
    socket.send(json.dumps(message).encode('utf-8'))

def broadcast_client_list():
    """
    Broadcast the updated client list to all connected clients as a string.
    """
    # Create a string representation of the client list
    client_list = ", ".join(CLIENTS.keys())  # Comma-separated client IDs
    print(client_list)
    message = {
        'sender': 'server',
        'receiver': None,
        'content': client_list,  # Convert the client list to a single string
        'ID': None,
        'method': {
            'action': 'UPDATE_CLIENT_LIST',
            'ID': None
        }
    }
    for client in CLIENTS.values():
        try:
            broadcast_message(client['socket'], message)
            print("Broadcast sucessfully")
        except Exception as e:
            print(f"Error broadcasting to client {client['action']}: {e}")

def generate_client_ID(name):
    while True:
        # Generate a random number between 1000 and 9999
        random_number = random.randint(1000, 9999)
        
        # Create a unique ID by combining name and random number
        uid = f"{name}_{random_number}"
        
        # Check if the ID is unique in the clients dictionary
        if uid not in CLIENTS:
            return uid
        

def create_new_client(client_socket):
    message = {
        'sender' : 'server',
        'receiver': None,
        'content': 'Please enter your user name',
        'ID': None,
        'method': {
            'action' : 'NEW',
            'ID' : None,
        }
    }
    broadcast_message(client_socket,message=message)

    message = receive_message(client_socket)

    client_name = message.get('sender')
    method_action = message.get('method',{}).get('action')

    if client_name and method_action == 'NEW':
        client_ID = generate_client_ID(client_name)

    message = {
        'sender' : 'server',
        'receiver': [client_ID],
        'content': client_ID,
        'ID': None,
        'method': {
            'action' : 'NEW',
            'ID' : None,
        }
    }

    #Broad cast the assign ID back for the client
    broadcast_message(client_socket,message=message)
    return client_ID, client_name

def remove_connection(client_ID):
    with lock:
        if client_ID in CLIENTS:
            client_socket = CLIENTS[client_ID]['socket']
            print(f"Removing client: {client_ID}")
            del CLIENTS[client_ID]
            try:
                client_socket.close()
            except Exception as e:
                print(f"Error closing client socket {client_ID}: {e}")

def handle_client_message(message):


    sender = message.get("sender")
    receivers = message.get("receiver")
    mssg_ID = message.get("ID")
    method = message.get("method", {})
    action = method.get("action")
    opt_ID = method.get("ID")

    if action == 'POST' or action == 'REPLY' or action == 'DELETE':
        #Send message to all available client in the server
        if receivers[0] == 'all':
            for client in CLIENTS:
                broadcast_message(CLIENTS[client]['socket'],message=message)
        else:
            print(receivers)
            for client in CLIENTS:
                if client in receivers:
                    broadcast_message(CLIENTS[client]['socket'],message=message)
            
        return False
    elif action == 'EXIT':
        print("Client {} disconnected".format(CLIENTS[sender]['address']))
        remove_connection(sender)
        broadcast_client_list()
        return True
    


    

    



def handle_client(client_socket, client_address):
    # GENERATE UNIQUE ID FOR CLIENT
    client_ID, client_name = create_new_client(client_socket=client_socket)

        # Add new client to the available client list
    with lock:
        CLIENTS[client_ID] = {
            'socket' : client_socket,
            'address' : client_address,
            'name' : client_name,
            'message' : []
        }

        print('Add new connection from {}:{}, username:{}, ID:{}'.format(*client_address,client_name,client_ID))
        broadcast_client_list()
    
    while True:
        message = receive_message(client_socket)
        if not message:
            print("Client {} disconnected".format(*client_address))
            remove_connection(client_ID)
            broadcast_client_list()
            break
        print('Received message from {}:{}'.format(*client_address))
        is_exit = handle_client_message(message=message)
        if is_exit:
            break





def main():

    #Create a socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    #Reuse the address and port without waiting time, and bind multiple sockets to the same address
    #Avoid "Address already in use"
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR,1)

    #bind
    server_socket.bind((IP,PORT))

    # BACK_LOG connection can be queued to be processed
    server_socket.listen(BACK_LOG)

    

    print("The server is ready for connection!")
    print(f"Listening for connection on {IP}:{PORT}...")


    while True:
        client_socket, client_address = server_socket.accept()
        client_handler = threading.Thread(target=handle_client,args=(client_socket,client_address),daemon= True)
        client_handler.start()

            
if __name__ == "__main__":
    main()