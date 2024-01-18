#!python

import time

import sys
sys.path.insert(0, '../src/')

from spi_adapter import SpiAdapter, AuxPinMode

# Customize for your system.
port = "COM18"
aux_out_pin = 0
aux_in_pin = 1

spi = SpiAdapter(port)
spi.set_aux_pin_mode(aux_out_pin, AuxPinMode.OUTPUT)
spi.set_aux_pin_mode(aux_in_pin, AuxPinMode.INPUT_PULLUP)


i = 0
while True:
  i += 1
  spi.write_aux_pin(aux_out_pin, i % 2)   # Square wave
  in_value = spi.read_aux_pin(aux_in_pin)
  print(f"{i:03d}: Input pin value: {in_value}", flush=True)
  time.sleep(0.5)


