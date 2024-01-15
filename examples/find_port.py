#!python

# TODO: Develope the idea of identifying automatically the I2C Adapter devices.

import serial.tools.list_ports

print(serial.tools.list_ports.comports())
print(serial.tools.list_ports.comports()[0])
