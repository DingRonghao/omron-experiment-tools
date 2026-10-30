import socket

IP = "192.168.250.1"
PORT = 64000

try:
    with socket.create_connection((IP, PORT), timeout=3):
        print("TCP connection successful!")
except Exception as e:
    print("Connection failed:", e)
