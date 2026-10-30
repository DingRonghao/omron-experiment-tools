
import socket
import time
import csv
from pathlib import Path

IP = "192.168.250.1"
PORT = 64000
DURATION = 0.1
MM_PER_COUNT = 0.00001

def exact(sock, n):
    data = bytearray()
    while len(data) < n:
        chunk = sock.recv(n - len(data))
        if not chunk:
            raise ConnectionError("Connection closed")
        data.extend(chunk)
    return bytes(data)

def ascii_field(sock, limit=32):
    data = bytearray()
    while True:
        b = exact(sock, 1)
        if b == b",":
            return data.decode("ascii")
        if len(data) >= limit:
            raise ValueError("Invalid ASCII field")
        data.extend(b)

def command(sock, name):
    sock.sendall((name + "\r\n").encode("ascii"))
    reply = bytearray()
    while not reply.endswith(b"\r\n"):
        reply.extend(exact(sock, 1))
        if len(reply) > 256:
            raise ValueError("Unexpected command reply")
    return reply.decode("ascii").strip()

def read_lb_frame(sock):
    # Ignore CR/LF between consecutive frames
    first = exact(sock, 1)
    while first in (b"\r", b"\n"):
        first = exact(sock, 1)

    if first != b"L":
        raise ValueError(f"Invalid frame start: {first!r}")

    if exact(sock, 2) != b"B,":
        raise ValueError("Invalid LB header")

    size_text = ascii_field(sock)
    try:
        size = int(size_text, 16)
    except ValueError:
        raise ValueError(f"Invalid size: {size_text!r}")

    if not 3 <= size <= 65536:
        raise ValueError(f"Unreasonable frame size: {size}")

    frame = exact(sock, size)

    status = int.from_bytes(frame[:2], "little")
    option = frame[2]

    if option != 1:
        raise ValueError(f"Unexpected option: {option}")

    final = (status == 0xFFFF)

    # SUM is present only in the final frame
    if final:
        if len(frame) < 5:
            raise ValueError("Final frame too short")
        payload = frame[3:-2]
        checksum = frame[-2:]
    else:
        payload = frame[3:]
        checksum = None

    return status, payload, final, checksum

# ------------------------------------------------
# 1. Short buffering test
# ------------------------------------------------

with socket.create_connection((IP, PORT), timeout=5) as s:
    s.settimeout(5)

    initial = command(s, "LI")
    print("Initial:", initial)

    start = command(s, "LS")
    print("Start:", start)

    if start != "LS,OK":
        raise RuntimeError("Could not start buffering")

    try:
        time.sleep(DURATION)
    finally:
        stop = command(s, "LE")
        print("Stop:", stop)

    info = command(s, "LI")
    print("Status:", info)

fields = info.split(",")

if len(fields) != 4 or fields[1] != "2":
    raise ValueError("Unexpected LI status")

label = int(fields[2], 16)
count = int(fields[3], 16)

print("Recorded points:", count)

if label < 1 or count < 1:
    raise RuntimeError("No buffered data available")

# ------------------------------------------------
# 2. Download buffered data
# ------------------------------------------------

request = f"LB,1,1,{label:X},1\r\n"
buffer = bytearray()
frames = 0

with socket.create_connection((IP, PORT), timeout=10) as s:
    s.settimeout(10)
    s.sendall(request.encode("ascii"))

    while frames < 1000:
        status, payload, final, checksum = read_lb_frame(s)

        buffer.extend(payload)
        frames += 1

        print(
            f"Frame {frames}: "
            f"status={status:04X}, "
            f"payload={len(payload)} bytes"
        )

        if final:
            break
    else:
        raise RuntimeError("Too many LB frames")

print("Frames downloaded:", frames)
print("Total payload bytes:", len(buffer))

# ------------------------------------------------
# 3. Parse label data
# ------------------------------------------------

if len(buffer) < 4:
    raise ValueError("Missing label size")

label_size = int.from_bytes(buffer[:4], "little")
data = buffer[4:]

print("Declared label size:", label_size)
print("Actual label size:", len(data))

if label_size != len(data):
    raise ValueError("Label size mismatch")

# Each sample: 6-byte timestamp + 21 x 4 bytes
RECORD_SIZE = 90

if len(data) % RECORD_SIZE != 0:
    raise ValueError(
        f"Record size mismatch: {len(data)} bytes"
    )

errors = {
    0x7FFFFFFD: "Light Excess",
    0x7FFFFFFE: "Light Shortage",
    0x7FFFFFFF: "Undetermined",
}

rows = []

for offset in range(0, len(data), RECORD_SIZE):
    record = data[offset:offset + RECORD_SIZE]

    timestamp = int.from_bytes(record[:6], "little")

    # CH1 measurement: field after 4-byte header
    raw = int.from_bytes(record[10:14], "little")

    if raw in errors:
        distance = None
        state = errors[raw]
    else:
        signed = (
            raw if raw < 0x80000000
            else raw - 0x100000000
        )
        distance = signed * MM_PER_COUNT
        state = "OK"

    rows.append((timestamp, distance, state, f"{raw:08X}"))

# ------------------------------------------------
# 4. Verify results
# ------------------------------------------------

print("\nFirst 10 measurements:")
for row in rows[:10]:
    print(row)

intervals = [
    rows[i + 1][0] - rows[i][0]
    for i in range(len(rows) - 1)
]

if intervals:
    print("\nMean interval (ms):",
          sum(intervals) / len(intervals))
    print("Min / Max interval (ms):",
          min(intervals), max(intervals))

valid = sum(row[2] == "OK" for row in rows)
print("Valid measurements:", valid, "/", len(rows))

# Save locally only after successful parsing
output = Path.cwd() / "zp_buffer_test.csv"

with output.open("w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow([
        "timestamp_ms", "distance_mm",
        "status", "raw_hex"
    ])
    writer.writerows(rows)

print("Saved:", output)
