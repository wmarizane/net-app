import socket
import json
import threading
import textwrap

# Configuration
IP = "127.0.0.1"
PORT = 65432
HEADER_LENGTH = 2048
BUBBLE_WIDTH = 40  # Maximum characters per line in the bubble

def speech_bubble(message, sender, msg_id, timestamp):
    """
    Creates a speech bubble string that contains the message text, the sender,
    and at the bottom, the message ID and timestamp (in a light gray color).
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
    
    # Bottom block: sender and then the id & timestamp in light gray.
    bottom = f"\\_{'_' * max_length}_/\n |/\n {sender}"
    # ANSI escape code \033[90m for light gray, then \033[0m to reset.
    bottom += f"\n\033[90mID: {msg_id} | {timestamp}\033[0m"
    
    return f"{top}\n{middle}\n{bottom}"

def receive_messages(client_socket):
    while True:
        try:
            raw_msg = client_socket.recv(HEADER_LENGTH)
            if not raw_msg:
                print("Connection closed by the server.")
                break
            message = json.loads(raw_msg.decode('utf-8'))
            # Check if it's an error message from server.
            if "error" in message:
                print("Error:", message["error"])
            else:
                # Format the message in a bubble.
                bubble = speech_bubble(
                    message.get('content', ''),
                    message.get('sender', 'Unknown'),
                    message.get('id', 'N/A'),
                    message.get('time', 'N/A')
                )
                print("\n" + bubble)
        except Exception as e:
            print("Error receiving message:", e)
            break

def main():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client_socket.connect((IP, PORT))
    except Exception as e:
        print("Unable to connect to the server:", e)
        return

    # Login handshake.
    response = json.loads(client_socket.recv(HEADER_LENGTH).decode('utf-8'))
    if response.get("action") == "LOGIN":
        username = input("Enter your username: ").strip()
        user_id = input("Enter your user ID (leave blank if new): ").strip()
        login_data = {"username": username, "user_id": user_id}
        client_socket.send(json.dumps(login_data).encode('utf-8'))
    # Receive login confirmation.
    response = json.loads(client_socket.recv(HEADER_LENGTH).decode('utf-8'))
    if response.get("status") == "SUCCESS":
        user_id = response.get("user_id")
        print(f"Connected successfully. Your user ID is: {user_id}")
    else:
        print("Login failed.")
        return

    # Start a background thread to receive messages.
    threading.Thread(target=receive_messages, args=(client_socket,), daemon=True).start()

    # Main loop: read user input and send messages.
    print("Type your messages. For a direct message, start with '@username'.")
    while True:
        user_input = input("You: ").strip()
        if not user_input:
            continue
        if user_input.lower() == ".exit":
            client_socket.send(json.dumps({"action": "EXIT"}).encode('utf-8'))
            print("Disconnecting...")
            break

        # Determine if this is a direct message.
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
        client_socket.send(json.dumps(data).encode('utf-8'))

if __name__ == "__main__":
    main()