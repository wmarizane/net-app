#!/usr/bin/python3
import socket

HOST = '127.0.0.1'
PORT = 65432

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((HOST, PORT)) # Connect to the server
    
    # 3 - data is exchanged
    s.sendall(b'Hello, world') # Send data to the server
    data = s.recv(1024) # Receive data from the server
    
print(f"Received {data}")