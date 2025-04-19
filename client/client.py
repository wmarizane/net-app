# client.py
import socket
import json
import threading
import textwrap
import ssl
import os  # For clearing the terminal
import random
import re
import subprocess
import sys
from datetime import datetime

# Configuration
IP = "127.0.0.1"
PORT = 65432
HEADER_LENGTH = 2048
BUBBLE_WIDTH = 40  # Maximum characters per line in the bubble
MESSAGES = []
ACTIVE_CLIENTS = []


# Global variable to hold our user id after login.
my_user_id = None
lock = threading.Lock()

def speech_bubble(message, sender, msg_id, timestamp, private, optional=None):
    """
    Creates a speech bubble string that contains:
      - The message text,
      - The sender's name,
      - And at the bottom, the message ID and timestamp (in light gray).
    """

    if sender == my_user_id:
        sender = 'You'
    # Wrap the message text.
    lines = textwrap.wrap(message, width=BUBBLE_WIDTH)
    if not lines:
        lines = [""]
    max_length = max(len(line) for line in lines)
    

    reply_box = ""
    if optional is not None:
        reply_lines = textwrap.wrap(optional, width=BUBBLE_WIDTH)
    
        if not reply_lines:
            reply_lines = [""]
        reply_max_length = max(len(line) for line in reply_lines)

        # Top reply border.
        reply_top = " " + "_" * (reply_max_length + 2)
        
        # Middle block: the message lines.
        reply_middle = "/ " + reply_lines[0].ljust(reply_max_length) + " \\"
        if len(reply_lines) > 1:
            reply_middle += "\n" + "\n".join([f"| {line.ljust(reply_max_length)} |" for line in reply_lines[1:]])
        reply_bottom = f"\\_{'_' * reply_max_length}_/\n |/\n"

        reply_box = f"{reply_top}\n{reply_middle}\n{reply_bottom}"

    main_box = ""
    # Top border.
    top = " " + "_" * (max_length + 2)
    
    # Middle block: the message lines.
    middle = "/ " + lines[0].ljust(max_length) + " \\"
    if len(lines) > 1:
        middle += "\n" + "\n".join([f"| {line.ljust(max_length)} |" for line in lines[1:]])
    
    # Bottom block: sender and then the ID and timestamp in light gray.
    bottom = f"\\_{'_' * max_length}_/\n |/\n {sender}"
    bottom += " (Private)" if private else " (Public)"
    bottom += f"\n\033[90mID: {msg_id} | {timestamp}\033[0m"

    main_box = f"{top}\n{middle}\n{bottom}"
    
    #return f"{top}\n{middle}\n{bottom}"
    return reply_box+main_box

def clear_screen():
    # Clear the terminal screen.
    os.system('cls' if os.name == 'nt' else 'clear')

def render_messages():
    """
    Clears the screen and reprints all messages using the speech bubble format.
    """
    global my_user_id
    clear_screen()
    print("=== Chat History ===\n")
    
    for msg in MESSAGES:
        optional = None
        
        if msg['action'] == 'REPLY':
            reply_sender = msg['sender']
            reply_message = None
            reply_id = msg['optional']
            for m in MESSAGES:
                if m['id'] == reply_id:
                    reply_message = m['content'] 
                    break
            optional = f"[REPLY]\"{reply_sender}({reply_id}): {reply_message}\""


        bubble = speech_bubble(
            msg.get('content', ''),
            msg.get('sender', 'Unknown'),
            msg.get('id', 'N/A'),
            msg.get('time', 'N/A'),
            msg.get('private',False),
            optional,
        )
        print(bubble + "\n")
    print("=== End of Chat History ===\n")
    print("++ ACTIVE CLIENTS ++\n")
    for i, client_id in enumerate(ACTIVE_CLIENTS):
        print(f"{i+1}: {client_id}")
    print("++++++++++++++++++++\n")
    print("Direct messages: @<user_id> <message>")
    print("Delete a message: .delete <message_id")
    print("Type '.exit' to quit.")

    print(f"\nYou ({my_user_id})>")

def generate_message_id():
    return f"{random.randint(100000, 999999)}"

def receive_messages(client_socket):
    global MESSAGES
    global ACTIVE_CLIENTS
    while True:
        try:
            raw_msg = client_socket.recv(HEADER_LENGTH).decode('utf-8')
            if not raw_msg:
                print("Connection closed by the server.")
                break

            data = json.loads(raw_msg)
            # If a refresh event is received, re-render the entire chat history.
            if data["action"] == "MESSAGE" or data['action'] == 'TEMPORARY' or data['action'] == 'REPLY':
                with lock:
                    MESSAGES.append(data)
                    MESSAGES = sorted(MESSAGES, key=lambda x: x["time"])
                    render_messages()
            elif data["action"] == "DELETE":
                with lock:
                    for msg in MESSAGES:
                        if msg['id'] == data['content']:
                            msg['content'] = 'THIS MESSAGE IS REMOVED'
                            break
                    render_messages()
            elif data["action"] == 'ACTIVE_CLIENT':
                with lock:
                    ACTIVE_CLIENTS = data['receiver'][:]
                    render_messages()
            elif data["action"] == 'OUTDATED':
                with lock:
                    for msg in MESSAGES:
                        if msg['id'] == data['content']:
                            msg['content'] = 'THIS MESSAGE IS EXPIRED'
                            break
                    render_messages()    
            elif "error" in data:
                print("Error:", data["error"])
            else:
                # (If other events are sent, handle them here.)
                pass
        except Exception as e:
            print("Error receiving message:", e)
            break

def extract_message_and_users(mssg):
    parts = mssg.split()
    users = []
    message_start_index = -1

    for i, part in enumerate(parts):
        if part.startswith("@"):
            users.append(part[1:])  # Remove the "@" symbol
        else:
            message_start_index = i
            break  # Now it only breaks when the first non-@ word is found

    message = " ".join(parts[message_start_index:]) if message_start_index != -1 else ""
    
    return users, message

def extract_temp_message(input_str):
    parts = input_str.strip().split()

    if not parts or parts[0] != ".temp":
        return None  # or raise an error

    users = []
    message_start_index = None

    for i in range(1, len(parts)):
        if parts[i].startswith('@'):
            users.append(parts[i][1:])
        else:
            message_start_index = i
            break

    message = ' '.join(parts[message_start_index:]) if message_start_index is not None else ''

    return  users, message

def extract_reply_message(input_str):
    parts = input_str.strip().split()

    if not parts or parts[0] != ".reply":
        return None  # or raise an error

    if len(parts) < 3:
        return None  # Not enough parts for msg_id and msg_context

    msg_id = parts[1]
    msg_context = ' '.join(parts[2:])

    return msg_id, msg_context


# Function to search messages based on a keyword
def search_messages(keyword):
    pattern = re.compile(keyword, re.IGNORECASE)
    matches = []

    with lock:
        for msg in MESSAGES:
            content = msg.get("content", "")
            if pattern.search(content):
                bubble = speech_bubble(
                    msg.get('content', ''),
                    msg.get('sender', 'Unknown'),
                    msg.get('id', 'N/A'),
                    msg.get('time', 'N/A'),
                    msg.get('private', False)
                )
                matches.append(bubble)

    # Write results to search.txt
    with open("search.txt", "w", encoding="utf-8") as f:
        for bubble in matches:
            f.write(bubble + "\n\n")

    # Open search.txt in a new terminal window
    try:
        open_search_txt()
    except Exception as e:
        print("Something went wrong:", e)

def open_search_txt():
    """Open search.txt in a new terminal window and leave it open after printing."""
    filepath = "search.txt"
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"Couldn’t find {filepath} in {os.getcwd()}")
    
    # Windows
    if sys.platform.startswith("win"):
        # `start` must be part of the shell string
        cmd = f'start cmd /k "type {filepath}"'
        subprocess.Popen(cmd, shell=True)
    
    # macOS
    elif sys.platform == "darwin":
        cwd = os.getcwd().replace('"', '\\"')
        # Activate Terminal and in one shot open a new window/tab to run your commands
        subprocess.run([
            "osascript",
            "-e", 'tell application "Terminal" to activate',
            "-e", f'tell application "Terminal" to do script "cd \\"{cwd}\\"; less {filepath}; exec zsh"'
        ])
    
    # Linux (generic)
    else:
        cwd = os.getcwd().replace('"', '\\"')
        # Try x-terminal-emulator (Debian/Ubuntu), else fallback to gnome-terminal
        terminal_cmd = [
            "x-terminal-emulator", "-e",
            f'bash -c "cd \\"{cwd}\\" && less {filepath}; exec $SHELL"'
        ]
        try:
            subprocess.Popen(terminal_cmd)
        except FileNotFoundError:
            # fallback
            subprocess.Popen([
                "gnome-terminal", "--",
                "bash", "-c", f'cd "{cwd}" && less {filepath}; exec $SHELL'
            ])
        
def main():
    global my_user_id, MESSAGES

    #Raw socket
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    #Create TLS context
    context = ssl.create_default_context()

    # For development only: disable server cert validation (not secure!)
    context.check_hostname = False
    # context.verify_mode = ssl.CERT_NONE

    context.verify_mode = ssl.CERT_REQUIRED
    context.load_verify_locations('cert.pem')


    try:
        tls_socket = context.wrap_socket(client_socket, server_hostname=IP)

        tls_socket.connect((IP, PORT))
    except Exception as e:
        print("Unable to connect to the server:", e)
        return

    # Login handshake.
    response = json.loads(tls_socket.recv(HEADER_LENGTH).decode('utf-8'))
    if response.get("action") == "LOGIN":
        username = input("Enter your username: ").strip()
        #user_id = input("Enter your user ID (leave blank if new): ").strip()
        #login_data = {"username": username, "user_id": user_id}
        login_data = {"username": username}
        tls_socket.send(json.dumps(login_data).encode('utf-8'))
        
    # Receive login confirmation.
    response = json.loads(tls_socket.recv(HEADER_LENGTH).decode('utf-8'))
    if response.get("status") == "SUCCESS":
        my_user_id = response.get("user_id")
        print(f"Connected successfully. Your user ID is: {my_user_id}")
    else:
        print("Login failed.")
        return

    # Start a background thread to listen for server events (including refresh).
    threading.Thread(target=receive_messages, args=(tls_socket,), daemon=True).start()

    # Main loop: read user input and send commands/messages.
    while True:
        data = {
            "id": None,
            "action": None,
            "sender": None,
            "receiver": None,
            "content": None,
            "time": None,
            "private": False,
            "optional": None
        }

        user_input = input(f"You ({my_user_id}): ").strip()
        if not user_input:
            continue
        if user_input.lower() == ".exit":
            tls_socket.send(json.dumps({"action": "EXIT"}).encode('utf-8'))
            print("Disconnecting...")
            break

        # Check for delete command.
        if user_input.startswith(".delete"):
            try:
                parts = user_input.split()
                if len(parts) < 2:
                    print("Usage: .delete <message_id>")
                    continue
                message_id_to_delete = parts[1]
                data["action"] = "DELETE"
                data["content"] = message_id_to_delete
                data["sender"] = my_user_id
                
                #tls_socket.send(json.dumps(data).encode('utf-8'))
                print(f"Delete request sent for message ID {message_id_to_delete}")
            except Exception as e:
                print("Error processing delete command:", e)
        elif user_input.startswith(".reply"):
            # .reply <msg_id> <message>
            try:
                msg_id_replied, msg_text = extract_reply_message(user_input)
                
                receivers = []
                private_satus = False
                for msg in MESSAGES:
                    if msg['id'] == msg_id_replied:
                        if msg['sender'] == my_user_id: #Reply yourself
                            receivers = msg["receiver"][:] + [my_user_id]
                        else: #Reply other's message
                            receivers = msg["receiver"][:] + [msg["sender"]]
                        
                        private_satus = msg["private"]

                data["action"] = 'REPLY'
                data["sender"] = my_user_id
                data["receiver"] = receivers
                data["content"] = msg_text
                data["optional"] = msg_id_replied
                data["private"] = private_satus

            except ValueError:
                print("Invalid format. Use '@username message' for direct messages.")
                continue
        elif user_input.startswith(".temp"):
            try:
                recipient, msg_text = extract_temp_message(user_input)

                if len(recipient) == 0: #no recipient: PUBLIC
                    recipient = ["all"]
                else: # PRIVATE messsage
                    data['private'] = True

                data["action"] = 'TEMPORARY'
                data["sender"] = my_user_id
                data["receiver"] = recipient
                data["content"] = msg_text

            except ValueError:
                print("Invalid format. Use '@username message' for direct messages.")
                continue
        elif user_input.startswith(".search"):
            try:
                parts = user_input.split(maxsplit=1)
                if len(parts) < 2:
                    print("Usage: .search <keyword>")
                    continue
                keyword = parts[1]
                search_messages(keyword)
            except Exception as e:
                print("Error processing search command:", e)
        # Otherwise, treat as a normal message.
        elif user_input.startswith('@'):
            try:
                #Handle the message

                # recipient, msg_text = user_input.split(' ', 1)
                # recipient = recipient.lstrip('@')
                recipient, msg_text = extract_message_and_users(mssg=user_input)
                data["action"] = 'MESSAGE'
                data["sender"] = my_user_id
                data["receiver"] = recipient
                data["content"] = msg_text
                data['private'] = True
            except ValueError:
                print("Invalid format. Use '@username message' for direct messages.")
                continue
        else:
            recipient = ["all"]
            msg_text = user_input
            data["action"] = 'MESSAGE'
            data["sender"] = my_user_id
            data["receiver"] = recipient
            data["content"] = msg_text

        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        data["time"] = timestamp


        tls_socket.send(json.dumps(data).encode('utf-8'))

if __name__ == "__main__":
    main()