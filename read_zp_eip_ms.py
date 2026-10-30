import socket

IP = "192.168.250.1"
PORT = 64000

# 官方 MS 命令：读取 CH1，附带时间戳
command = b"MS,01,0\r\n"

try:
    with socket.create_connection((IP, PORT), timeout=3) as s:
        s.settimeout(3)
        s.sendall(command)

        response = s.recv(4096)
        print("Raw response:", repr(response))
        print("Decoded response:", response.decode("ascii", errors="replace"))

except Exception as e:
    print("Error:", e)
