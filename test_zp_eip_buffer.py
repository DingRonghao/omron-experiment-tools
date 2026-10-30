import socket
import time

IP = "192.168.250.1"
PORT = 64000

def command(sock, cmd):
    sock.sendall((cmd + "\r\n").encode("ascii"))
    response = b""
    while not response.endswith(b"\r\n"):
        chunk = sock.recv(1024)
        if not chunk:
            raise ConnectionError("Device closed connection")
        response += chunk
    result = response.decode("ascii", errors="replace").strip()
    print(f"{cmd} -> {result}")
    return result

with socket.create_connection((IP, PORT), timeout=3) as sock:
    sock.settimeout(3)

    started = False
    try:
        # 1. Check initial status
        command(sock, "LI")

        # 2. Start buffering
        reply = command(sock, "LS")
        if reply != "LS,OK":
            raise RuntimeError("Buffering did not start")

        started = True

        # 3. Check while buffering
        time.sleep(1)
        command(sock, "LI")

        # 4. Keep buffering for 2 more seconds
        time.sleep(2)

    finally:
        # 5. Always attempt to stop buffering
        if started:
            command(sock, "LE")
            command(sock, "LI")

print("Buffer test finished.")
