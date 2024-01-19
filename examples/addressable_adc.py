"""ADC ADS1118 demo."""

import sys
import time

sys.path.insert(0, '../src/')
from spi_adapter import SpiAdapter

port = "COM18"

print(f"Connecting to port {port}...", flush=True)
spi =  SpiAdapter(port = port)
print(f"Connected.", flush=True)

# Single shot, 2.046v FS, A0 input.
config_byte_msb = 0b11000101
config_byte_lsb = 0b10001010
spi_address = 15
cmd = bytes([spi_address,config_byte_msb, config_byte_lsb, 0x00, 0x00])

while True:
  resp = spi.send(cmd, mode=1, speed=4000000)
  assert isinstance(resp, bytearray), type(resp)
  assert len(resp) == 5
  value = int.from_bytes(resp[1:3], byteorder='big', signed=True)
  print(f"Response: {resp.hex(' ')} : {value:6d}", flush=True)

  time.sleep(0.5)

