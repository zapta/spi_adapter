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
  result = spi.send(bytearray([0x11, 0x22, 0x33]), 2, 0)
  print(f"{i:04d} Result: {result.hex(' ')}", flush=True)
  time.sleep(0.3)


