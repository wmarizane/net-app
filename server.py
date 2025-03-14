#!/usr/bin/env python3

import socket
import threading

# server configuration
HOST = '127.0.0.1'
PORT = 65432

# store connected clients
clients = {}
lock = threading.Lock() 

def handle_client(conn, addr, client_name):
    print(f"{client_name} connected from {addr}")
    try:
        while True:
            msg = conn.recv(1024).decode()
            if not msg or msg.lower() == '.exit':
                break
            
            # parse recipient and message (recipient: message)
            if ':' in msg:
                recipient, message = msg.split(':', 1)
                message = message.strip()
                
                with lock:
                    if recipient in clients:
                        clients[recipient].sendall(f"{client_name}: {message}".encode())
                        
                    else:
                        conn.sendall(f"User {recipient} not found.".encode())
            else:
                conn.sendall("Invalid message format. Use 'recipient: message'.".encode())
    except Exception as e:
        print(f"Error with {client_name}: {e}")
    finally:
        with lock:
            del clients[client_name]
        conn.close()
        print(f"{client_name} disconnected")
        
def start_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.bind((HOST, PORT))
        server.listen()
        print(f"Server running on {HOST}:{PORT}")
        
        while True:
            conn, addr = server.accept()
            conn.sendall("Enter your name: ".encode())
            client_name = conn.recv(1024).decode().strip()
        
            with lock:
                clients[client_name] = conn
            
            threading.Thread(target=handle_client, args=(conn, addr, client_name), daemon=True).start()
            
if __name__ == "__main__":
    start_server()