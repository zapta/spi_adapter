#!python

from i2c_adapter import I2cAdapter

i2c = I2cAdapter(port="COM18")
print(f"Scanning I2C bus 0x00 to 0x7f:")
for adr in range(0, 127):
    if i2c.write(adr, bytearray([0]), silent=True):
      print(f"  - Device at 0x{adr:02x}")

