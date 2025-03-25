import socket
import sys
import threading
import textwrap

HOST = '127.0.0.1'
PORT = 65432
HEADER_LENGTH = 2048
BUBBLE_WIDTH = 40

def speech_bubble(message, sender):
    lines = textwrap.wrap(message, width=BUBBLE_WIDTH)
    max_length = max(len(line) for line in lines)
    
    top = " " + "_" * (max_length + 2)
    middle = "/ " + lines[0].ljust(max_length) + " \\"  # First line with slashes
    middle += "\n" + "\n".join([f"| {line.ljust(max_length)} |" for line in lines[1:]]) 
    bottom = f"\\_{'_' * max_length}_/\n |/\n {sender}"
    
    return f"{top}\n{middle}\n{bottom}"

def receive_messages(client_socket):
    while True:
        try:
            # Receive the sender's username header
            username_header = client_socket.recv(HEADER_LENGTH)

            if not len(username_header):
                print("Connection closed by the server.")
                sys.exit()

            # Get sender username
            username_length = int(username_header.decode('utf-8').strip())
            username = client_socket.recv(username_length).decode('utf-8')

            # Get the actual message
            message_header = client_socket.recv(HEADER_LENGTH)
            message_length = int(message_header.decode('utf-8').strip())
            message = client_socket.recv(message_length).decode('utf-8')

            sys.stdout.write("\r" + " " * 50 + "\r")  # Clear input line
            print(speech_bubble(message, username))
            print("You > ", end="", flush=True)

        except Exception as e:
            print(f"Error receiving message: {e}")
            sys.exit()

def main():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        client_socket.connect((HOST, PORT))
        print(f"Connected to {HOST}:{PORT}")
    except Exception as e:
        print(f"Connection failed: {e}")
        sys.exit()

    prompt_header = client_socket.recv(HEADER_LENGTH)
    prompt_length = int(prompt_header.decode('utf-8').strip())
    prompt_message = client_socket.recv(prompt_length).decode('utf-8')
    print(prompt_message, end=" ")

    username = input().strip()
    username_encoded = username.encode('utf-8')
    username_header = f"{len(username_encoded):<{HEADER_LENGTH}}".encode('utf-8')
    client_socket.send(username_header + username_encoded)

    threading.Thread(target=receive_messages, args=(client_socket,), daemon=True).start()

    while True:
        message = input('You > ')
        if message.lower() == ".exit":
            print("Disconnecting...")
            client_socket.close()
            sys.exit()

        message_encoded = message.encode('utf-8')
        message_header = f"{len(message_encoded):<{HEADER_LENGTH}}".encode('utf-8')
        client_socket.send(message_header + message_encoded)

if __name__ == "__main__":
    main()
