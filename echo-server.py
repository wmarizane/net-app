#!/usr/bin/python3
import socket

# 1 - server sets up a listening socket

HOST = '127.0.0.1' # Localhost
PORT = 65432 # Port to listen on (non-privileged ports are > 1023)

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.bind((HOST, PORT)) # Bind the socket to the address and port
    s.listen() # Listen for incoming connections
    conn, addr = s.accept() # Accept a connection
    
# 3 - data is exchanged

    with conn:
        print('Connected by', addr) # Print the address of the connected client
        while True:
            data = conn.recv(1024)
            if not data:
                break
            conn.sendall(data) # Echo the data back to the client