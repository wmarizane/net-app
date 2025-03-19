import socket
import threading
import textwrap

HOST = '127.0.0.1'
PORT = 65432
BUBBLE_WIDTH = 40

def speech_bubble(message, sender):
    lines = textwrap.wrap(message, width=BUBBLE_WIDTH)
    max_length = max(len(line) for line in lines)
    
    top = " " + "_" * (max_length + 2)
    # middle = "\n".join([f"/ {line.ljust(max_length)} \"] + [f"| {line.ljust(max_length)} |" for line in wrapped_lines[1:]])
    middle = "/ " + lines[0].ljust(max_length) + " \\"  # First line with slashes
    middle += "\n" + "\n".join([f"| {line.ljust(max_length)} |" for line in lines[1:]]) 
    bottom = f"\\_{'_' * max_length}_/\n |/\n {sender}"
    
    return f"{top}\n{middle}\n{bottom}"

def receive_messages(sock):
    while True:
        try:
            msg = sock.recv(1024).decode()
            if not msg:
                break
            sender, message = msg.split(":", 1)
            print(speech_bubble(message.strip(), sender))
        except:
            break

def start_client():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
        client.connect((HOST, PORT))
        print(client.recv(1024).decode(), end="")  # Prompt for name
        name = input().strip()
        client.sendall(name.encode())
        
        threading.Thread(target=receive_messages, args=(client,), daemon=True).start()
        
        print("Typer your messages using 'recipient: message format. Type '.exit' to quit.") 
        while True:
            msg = input()
            if msg.lower() == '.exit':
                break
            client.sendall(msg.encode())

if __name__ == "__main__":
    start_client()
    