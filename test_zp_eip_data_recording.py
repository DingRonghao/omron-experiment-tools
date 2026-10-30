import socket
import time
import csv
from pathlib import Path

IP, PORT = "192.168.250.1", 64000
DURATION = 0.1
SCALE_MM = 0.00001  

def read_exact(sock, n):
    data = bytearray()
    while len(data) < n:
        part = sock.recv(n - len(data))
        if not part:
            raise ConnectionError("Connection closed")
        data.extend(part)
    return bytes(data)

def read_until(sock, delimiter=b",", limit=32):
    data = bytearray()
    while not data.endswith(delimiter):
        if len(data) >= limit:
            raise ValueError("Invalid response header")
        data.extend(read_exact(sock, 1))
    return bytes(data[:-len(delimiter)])

def cmd(sock, name):
    sock.sendall((name + "\r\n").encode("ascii"))
    result = bytearray()
    while not result.endswith(b"\r\n"):
        result.extend(read_exact(sock, 1))
    reply = result.decode("ascii").strip()
    print(name, "->", reply)
    return reply

# 1. Record a short buffer
with socket.create_connection((IP, PORT), timeout=5) as s:
    s.settimeout(5)
    print("Initial:", cmd(s, "LI"))

    if cmd(s, "LS") != "LS,OK":
        raise RuntimeError("Buffer start failed")

    try:
        time.sleep(DURATION)
    finally:
        print("Stop:", cmd(s, "LE"))

    status = cmd(s, "LI")

parts = status.split(",")
if len(parts) != 4 or parts[1] != "2":
    raise RuntimeError("Unexpected buffer status")

label = int(parts[2], 16)
count = int(parts[3], 16)
print("Recorded points:", count)

if label < 1 or count < 1:
    raise RuntimeError("No readable buffered data")

# 2. Download one label, with timestamps
request = f"LB,1,1,{label:X},1\r\n"
binary = bytearray()
frame_count = 0

with socket.create_connection((IP, PORT), timeout=10) as s:
    s.settimeout(10)
    s.sendall(request.encode("ascii"))

    while True:
        prefix = read_until(s)
        if prefix != b"LB":
            raise RuntimeError(f"Unexpected LB reply: {prefix!r}")

        size_text = read_until(s)
        size = int(size_text, 16)

        # Read exactly the binary payload bytes
        frame = read_exact(s, size)

        output_status = int.from_bytes(frame[:2], "little")
        option = frame[2]

        if option != 1:
            raise RuntimeError("Timestamp option missing")

        last = output_status == 0xFFFF

        # The final frame contains a 2-byte SUM
        binary.extend(frame[3:-2] if last else frame[3:])
        frame_count += 1

        if last:
            # CR+LF follows the final binary frame
            ending = read_exact(s, 2)
            if ending != b"\r\n":
                raise RuntimeError(
                    f"Invalid final delimiter: {ending!r}"
                )
            break

print("Frames downloaded:", frame_count)
print("Binary payload bytes:", len(binary))

# 3. Parse label and samples
if len(binary) < 4:
    raise RuntimeError("Missing label header")

label_size = int.from_bytes(binary[:4], "little")
label_data = binary[4:]

if label_size != len(label_data):
    raise RuntimeError(
        f"Label size mismatch: {label_size} vs {len(label_data)}"
    )

# 6 timestamp bytes + 21 x 4-byte fields = 90 bytes
RECORD_SIZE = 90
if len(label_data) % RECORD_SIZE:
    raise RuntimeError("Unexpected record size")

rows = []
for i in range(0, len(label_data), RECORD_SIZE):
    record = label_data[i:i + RECORD_SIZE]

    timestamp = int.from_bytes(record[:6], "little")
    raw = int.from_bytes(record[10:14], "little")

    errors = {
        0x7FFFFFFD: "Light Excess",
        0x7FFFFFFE: "Light Shortage",
        0x7FFFFFFF: "Undetermined",
    }

    if raw in errors:
        value_mm = None
        state = errors[raw]
    else:
        signed = raw if raw < 0x80000000 else raw - 0x100000000
        value_mm = signed * SCALE_MM
        state = "OK"

    rows.append([timestamp, value_mm, state, f"{raw:08X}"])

# 4. Inspect timing, measurements and save CSV
print("\nFirst 10 samples:")
for row in rows[:10]:
    print(row)

intervals = [
    rows[i + 1][0] - rows[i][0]
    for i in range(len(rows) - 1)
]

if intervals:
    print("\nMean timestamp interval (ms):",
          sum(intervals) / len(intervals))
    print("Min / Max interval (ms):",
          min(intervals), max(intervals))

valid = sum(row[2] == "OK" for row in rows)
print("Valid measurements:", valid, "/", len(rows))

output = Path.cwd() / "zp_buffer_test.csv"
with output.open("w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["timestamp_ms", "distance_mm",
                     "status", "raw_hex"])
    writer.writerows(rows)

print("CSV saved:", output)
