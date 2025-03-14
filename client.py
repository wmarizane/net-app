import socket
import threading

HOST = '127.0.0.1'
PORT = 65432

def receive_messages(sock):
    while True:
        try:
            msg = sock.recv(1024).decode()
            if not msg:
                break
            print(msg)
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
    