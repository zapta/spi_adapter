import sys
import time

sys.path.insert(0, '../src/')
from spi_adapter import SpiAdapter, AuxPinMode

port = "COM18"

print(f"Connecting to port {port}...", flush=True)
spi =  SpiAdapter(port = port)
print(f"Connected.", flush=True)

spi.set_aux_pin_mode(0, AuxPinMode.OUTPUT)


i = 0
while True:
  i += 1
  print(f"\n{i:04d} Sending...", flush=True)

  #spi.write_aux_pins(i % 256, 0b00000001)
  #   cs = 0  #i % 4
  #   mode = 0 # (i % 2) * 2
  #   #speed = 4000000
  #   #result = spi.send(bytearray([0x11, 0x22, 0x33]), extra_bytes=2, cs=cs, mode=mode, speed=speed, read=True)

  data = bytearray([1, 2, 3])
  result = spi.send(data, read=True)
  print(f"{i:04d} Result: {result.hex(' ')}", flush=True)
  time.sleep(0.5)
  


