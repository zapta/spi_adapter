import sys
import time

sys.path.insert(0, '../src/')
from spi_adapter import SpiAdapter

port = "COM17"

print(f"Connecting to port {port}...", flush=True)
spi =  SpiAdapter(port = port)
print(f"Connected.", flush=True)

i = 0
while True:
  i += 1
  print(f"\n{i:04d} Sending...", flush=True)
  cs = 0  #i % 4
  mode = 0 # (i % 2) * 2
  #speed = 4000000
  #result = spi.send(bytearray([0x11, 0x22, 0x33]), extra_bytes=2, cs=cs, mode=mode, speed=speed, read=True)
  result = spi.send(bytearray([0x11, 0x22, 0x33]), extra_bytes=2)
  print(f"Result type: {type(result)}", flush=True);
  print(f"{i:04d} Result: {result.hex(' ')}", flush=True)
  time.sleep(0.3)


