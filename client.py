# client.py
import socket
import json
import threading
import textwrap
import ssl
import os  # For clearing the terminal

# Configuration
IP = "127.0.0.1"
PORT = 65432
HEADER_LENGTH = 2048
BUBBLE_WIDTH = 40  # Maximum characters per line in the bubble

# Global variable to hold our user id after login.
my_user_id = None

def speech_bubble(message, sender, msg_id, timestamp):
    """
    Creates a speech bubble string that contains:
      - The message text,
      - The sender's name,
      - And at the bottom, the message ID and timestamp (in light gray).
    """
    # Wrap the message text.
    lines = textwrap.wrap(message, width=BUBBLE_WIDTH)
    if not lines:
        lines = [""]
    max_length = max(len(line) for line in lines)
    
    # Top border.
    top = " " + "_" * (max_length + 2)
    
    # Middle block: the message lines.
    middle = "/ " + lines[0].ljust(max_length) + " \\"
    if len(lines) > 1:
        middle += "\n" + "\n".join([f"| {line.ljust(max_length)} |" for line in lines[1:]])
    
    # Bottom block: sender and then the ID and timestamp in light gray.
    bottom = f"\\_{'_' * max_length}_/\n |/\n {sender}"
    bottom += f"\n\033[90mID: {msg_id} | {timestamp}\033[0m"
    
    return f"{top}\n{middle}\n{bottom}"

def clear_screen():
    # Clear the terminal screen.
    os.system('cls' if os.name == 'nt' else 'clear')

def render_messages(messages):
    """
    Clears the screen and reprints all messages using the speech bubble format.
    """
    clear_screen()
    print("=== Chat History ===\n")
    for msg in messages:
        bubble = speech_bubble(
            msg.get('content', ''),
            msg.get('sender', 'Unknown'),
            msg.get('id', 'N/A'),
            msg.get('time', 'N/A')
        )
        print(bubble + "\n")
    print("=== End of Chat History ===\n")
    print("Type your message or command:")

def receive_messages(client_socket):
    while True:
        try:
            raw_msg = client_socket.recv(HEADER_LENGTH)
            if not raw_msg:
                print("Connection closed by the server.")
                break
            data = json.loads(raw_msg.decode('utf-8'))
            # If a refresh event is received, re-render the entire chat history.
            if data.get("action") == "REFRESH":
                messages = data.get("messages", [])
                render_messages(messages)
            elif "error" in data:
                print("Error:", data["error"])
            else:
                # (If other events are sent, handle them here.)
                pass
        except Exception as e:
            print("Error receiving message:", e)
            break

def main():
    global my_user_id

    #Raw socket
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    #Create TLS context
    context = ssl.create_default_context()

    # For development only: disable server cert validation (not secure!)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
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
        user_id = input("Enter your user ID (leave blank if new): ").strip()
        login_data = {"username": username, "user_id": user_id}
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
    print("Type your messages. For direct messages, start with '@username'.")
    print("To delete a message, type '.delete <message_id>'.")
    print("Type '.exit' to quit.")
    while True:
        user_input = input("You: ").strip()
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
                data = {
                    "action": "DELETE",
                    "id": message_id_to_delete,
                    "sender": my_user_id
                }
                tls_socket.send(json.dumps(data).encode('utf-8'))
                print(f"Delete request sent for message ID {message_id_to_delete}")
            except Exception as e:
                print("Error processing delete command:", e)
            continue

        # Otherwise, treat as a normal message.
        if user_input.startswith('@'):
            try:
                recipient, msg_text = user_input.split(' ', 1)
                recipient = recipient.lstrip('@')
            except ValueError:
                print("Invalid format. Use '@username message' for direct messages.")
                continue
        else:
            recipient = "all"
            msg_text = user_input

        data = {
            "action": "MESSAGE",
            "receiver": recipient,
            "content": msg_text
        }
        tls_socket.send(json.dumps(data).encode('utf-8'))

if __name__ == "__main__":
    main()