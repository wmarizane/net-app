import socket
import sys
import threading
import json
import random
import queue
import re

IP = "127.0.0.1"
PORT = 12000
HEADER_LENGTH = 2048

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

CLIENT_LIST = []
lock = threading.Lock()
input_ready_event_dict = {}


MESSAGE_DICT = {}
#SENDING_QUEUE = queue.Queue()

def receive_message(socket):
    '''
        socket: 
    '''
    data = socket.recv(HEADER_LENGTH).decode('utf-8')
    return json.loads(data)

def send_message(socket,message):
    '''
        socket: socket of receiver
    '''
    socket.send(json.dumps(message).encode('utf-8'))

def generate_message_ID(clientID):
    while True:
        # Generate a random number between 1000 and 9999
        random_number = random.randint(1000, 9999)
        
        # Create a unique ID by combining name and random number
        message_ID = f"{clientID}/{random_number}"
        
        # Check if the ID is unique in the clients dictionary
        if message_ID not in MESSAGE_DICT:
            return message_ID    

def register_client_ID(client_socket):

    message = receive_message(client_socket)
    method_action = message.get('method',{}).get('action')
    content = message.get('content')
    sender = message.get('sender')

    if method_action == 'NEW' and sender == 'server':
        #Print the prompt and get user name
        user_name =input(content + ": ").strip()

        message = {
        'sender' : user_name,
        'receiver': ['server'],
        'content': user_name,
        'ID': None,
        'method': {
            'action' : 'NEW',
            'ID' : None,
            }
        }
    
    send_message(client_socket,message=message)

    message = receive_message(client_socket)

    client_ID = message.get('receiver')[0]

    input_ready_event_dict[client_ID] = threading.Event()

    return client_ID


def display_message(message):
    sender = message.get("sender", "Unknown")
    receivers = ", ".join(message.get("receiver", [])) if isinstance(message.get("receiver"), list) else "Unknown"
    content = message.get("content", "No content")
    msg_id = message.get("ID", "No ID")
    method = message.get("method", {})
    method_action = method.get("action", "Unknown")
    method_id = method.get("ID", "No method ID")
    print('\n')
    print("----- Message Details -----")
    print(f"Sender:      {sender}")
    print(f"Receivers:   {receivers}")
    print(f"Content:     {content}")
    print(f"Message ID:  {msg_id}")
    print("----- Method Details ------")
    print(f"Method Name: {method_action}")
    print(f"Method ID:   {method_id}")
    print("----------------------------")
    print('\n')

def display_reply_message(reply_message):
    sender = reply_message.get("sender", "Unknown")
    receivers = ", ".join(reply_message.get("receiver", [])) if isinstance(reply_message.get("receiver"), list) else "Unknown"
    content = reply_message.get("content", "No content")
    mssg_id = reply_message.get("ID", "No ID")
    method = reply_message.get("method", {})
    method_action = method.get("action", "Unknown")
    reply_id = method.get("ID", "No method ID")
    
    print('\n')
    print("----- Reply Message Details -----")
    print(f"Sender:      {sender}")
    print(f"Receivers:   {receivers}")
    print(f"Content:     {content}")
    print(f"Reply of Message ID:    {reply_id}")
    print(f"Message ID:  {mssg_id}")
    print("----- Method Details ------")
    print(f"Method Name: {method_action}")
    print("----------------------------")
    print('\n')


def display_client_list():
    """
    Display the updated client list.
    """
    global CLIENT_LIST

    print("\n----- Connected Clients -----")
    if CLIENT_LIST:
        for i, client in enumerate(CLIENT_LIST, start=1):
            print(f"{i}. {client}")
    else:
        print("No clients connected.")
    print("-----------------------------\n")

def parse_create_message(str,clientID,mssg_ID):
    headers_and_content = str.split(':')
    headers = [header for header in headers_and_content[0].split(' ') if header]
    content = headers_and_content[1].strip()

    message = {
        'sender' : None,
        'receiver': None,
        'content': content,
        'ID': None,
        'method': {
            'action' : None,
            'ID' : None,
            }
    }

    action = headers[0]

    if headers[0] == 'REPLY' or headers[0] == 'DEL':
        opt_ID = headers[-1]
        receivers = headers[1:len(headers)-1]
        message['method']['ID'] = opt_ID
    else:
        receivers = headers[1:]
    
    message['receiver'] = receivers
    message['sender'] = clientID
    message['ID'] = mssg_ID
    message['method']['action'] = action

    return message


def handling_messages(client_socket,client_ID, shutdown_event):
    global CLIENT_LIST
    while not shutdown_event.is_set():
        try:
            message = receive_message(client_socket)
            action = message['method']['action']
            if action == 'POST':

                #Update receiving message
                with lock:
                    message_ID = message['ID']
                    MESSAGE_DICT[message_ID] = {
                        'message' : message,
                        'status' : True,
                    }

                    # ack_message = {
                    #     'sender' : client_ID,
                    #     'receiver': [message['sender']],
                    #     'content': None,
                    #     'ID': None,
                    #     'method': {
                    #         'action' : 'ACK_MSSG',
                    #         'ID' : message_ID,
                    #     }
                    # }

                    # #Push the ACK to queue
                    # SENDING_QUEUE.put(ack_message)

                display_message(message=message)
                print('You >')
                
            elif action == 'UPDATE_CLIENT_LIST':
                # Update the global client list
                with lock:
                    clist = message['content'].split(', ')
                    CLIENT_LIST = clist
                    print("\nClient list updated:")
                    display_client_list()
                    print('You >')
            elif action == 'REPLY':
                with lock:
                    reply_mssg_ID = message['method']['ID']

                    if reply_mssg_ID in MESSAGE_DICT.keys():
                        if MESSAGE_DICT[reply_mssg_ID]['status'] == True:
                            MESSAGE_DICT[reply_mssg_ID] = message
                            display_reply_message(reply_message=message)
                        else:
                            print('The replied message is NOT available any more')
                            # message = {
                            #     'sender' : client_ID,
                            #     'receiver': [message['sender']],
                            #     'content': None,
                            #     'ID': None,
                            #     'method': {
                            #         'action' : 'REP_FAIL',
                            #         'ID' : reply_mssg_ID,
                            #     }
                            # }
                            # #Push the warning to queue
                            # SENDING_QUEUE.put(message)
                print('You >')
            elif action == 'DELETE':
                with lock:
                    del_mssg_ID = message['method']['ID']
                    if del_mssg_ID in MESSAGE_DICT.keys():
                        if MESSAGE_DICT[del_mssg_ID]['status'] == True:
                            MESSAGE_DICT[del_mssg_ID]['status'] == False

                            # message = {
                            #     'sender' : client_ID,
                            #     'receiver': [message['sender']],
                            #     'content': None,
                            #     'ID': None,
                            #     'method': {
                            #         'action' : 'ACK_DEL',
                            #         'ID' : del_mssg_ID,
                            #     }
                            # }

                            #Push the ACK to queue
                            #SENDING_QUEUE.put(message)

            # elif action == 'REP_FAIL':
            #     print('** Cannot reply message {} to {} **'.format(message['method']['ID'],message['sender']))
            # elif re.match(r"ACK_.*",action):
            #     # ACK_ is used for acknowledgement
            #     if action == 'ACK_MSSG':
            #         print('** Message {} has been received by {} **'.format(message['method']['ID'],message['sender']))
            #     elif action == 'ACK_DEL':
            #         print('** Message {} has been deleted by {} **'.format(message['method']['ID'],message['sender']))
            #     elif action == 'ACK_REP':
            #         print('** Replied message {} has been received by {} **'.format(message['method']['ID'],message['sender']))   
            else:
                print('Cannot found the action for the message')
            input_ready_event_dict[client_ID].set()

        except Exception as e:
            if not shutdown_event.is_set(): # Only print error if it wasn't a shutdown.
                print(f"Error receiving message: {e}")
                break
            # print(f"Error receiving message: {e}")
            # sys.exit()

# def send_queued_messages(client_socket):
#     while True:
#         with lock:
#         #Send all the receipt message back to the sender
#             outgoing_message = SENDING_QUEUE.get()
#             if not outgoing_message:
#                 break
#             send_message(client_socket,outgoing_message)


def main():


    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    shutdown_event = threading.Event()

    try:
        # Connect to the server
        client_socket.connect((IP, PORT))
        print(f"Connected to {IP}:{PORT}")
    except Exception as e:
        print(f"Connection failed: {e}")
        sys.exit()



    client_ID = register_client_ID(client_socket=client_socket)
    print(client_ID)

    #Create thread to receive all the messages from other clients
    message_receiver = threading.Thread(target=handling_messages, args=(client_socket,client_ID,shutdown_event), daemon=True)
    message_receiver.start()

    # queue_handler = threading.Thread(target=send_queued_messages, args=(client_socket,), daemon=True)
    # queue_handler.start()

    input_ready_event_dict[client_ID].wait()
    #Send the message to the server
    while True:
        content = input('You > ')

        # INPUT format
        # ACTION

        #generate ID for the new message
        message_ID = generate_message_ID(clientID=client_ID)

        message = {
        'sender' : client_ID,
        'receiver': None,
        'content': content,
        'ID': message_ID,
        'method': {
            'action' : None,
            'ID' : None,
            }
        }

        if content.lower() == ".exit":
            #Hanlde user input ".exit" to leave the chat
    
            with lock:
                message['method']['action'] = ['EXIT']
                print("Disconnecting...")
                send_message(client_socket,message=message)
            shutdown_event.set()
            client_socket.close()
            message_receiver.join() #Join the thread back
            #queue_handler.join()
            break
        else:
            # Create message and send to the server to forward toward receiver(s)
            message_ID = generate_message_ID(clientID=client_ID)
            message = parse_create_message(content,clientID=client_ID,mssg_ID = message_ID)
        
        with lock:
            if message['method']['action'] == 'DELETE':
                MESSAGE_DICT[message['method']['ID']] = False
    
        #Acquire the lock to update the new message to the message dictionary
        with lock:
            MESSAGE_DICT[message_ID] = {
                'message' : message,
                'status' : True,
            }
        print(message)
        send_message(client_socket,message=message)
        
        input_ready_event_dict[client_ID].clear()
        
   


if __name__ == "__main__":
    main()
