#!python

# This program demonstrates how to use the SpiAdapter to allow the luma.oled
# package to draw on an SPI Oled display. In this example we use a 128x64
# SH1106 display.

import time
import datetime

# import sys
# sys.path.insert(0, '../src/')

from spi_adapter import SpiAdapter, AuxPinMode
from luma.oled.device import ssd1306
from luma.core.render import canvas
from PIL import ImageFont, ImageColor


# Related readings
# - https://buildmedia.readthedocs.org/media/pdf/luma-oled/rtd-update/luma-oled.pdf
# - https://github.com/rm-hull/luma.core/blob/master/luma/core/interface/serial.py#L260
# - https://github.com/rm-hull/luma.examples/blob/master/examples/sys_info.py
# - https://github.com/rm-hull/luma.examples/tree/master/examples
# - https://luma-oled.readthedocs.io/en/latest/
# - https://stackoverflow.com/questions/64189757/add-element-to-oled-display-via-pil-python-without-erasing-rest


# Customize for your system.
my_port = "COM18"
dc_aux_pin = 0
nrst_aux_pin = 1

# my_oled_addr = 0x3C


class MyLumaSerial:
    """Implementation of the luma.core.interface.serial interface using an SPI Adapter.
    See luma.core.interface.serial.spi for an example.
    """

    def __init__(self, port: str):
        """Open the SPI Adapter and initialize this Luma serial instance."""
        self.__spi = SpiAdapter(port)
        self.__spi.set_aux_pin_mode(dc_aux_pin, AuxPinMode.OUTPUT)
        self.__spi.set_aux_pin_mode(nrst_aux_pin, AuxPinMode.OUTPUT)
        self.__spi.write_aux_pin(nrst_aux_pin, 0)
        self.__spi.write_aux_pin(nrst_aux_pin, 1)

    def command(self, *cmd):
        """Send to the SPI display a command with given bytes."""
        self.__spi.write_aux_pins(0 << dc_aux_pin, 1 << dc_aux_pin)
        payload =  bytes(list(cmd))
        assert self.__spi.send(payload, read=False, speed=4000000) is not None

    def data(self, data):
        """Send to the SPI display data with given bytes."""
        self.__spi.write_aux_pins(1 << dc_aux_pin, 1 << dc_aux_pin)
        i = 0
        n = len(data)
        while i < n:
            # SPI Adapter limits to 256 bytes payload.
            chunk_size = min(256, n - i)
            payload =  bytes(data[i : i + chunk_size])
            assert self.__spi.send(payload, read=False, speed=4000000) is not None
            i += chunk_size


luma_serial = MyLumaSerial(my_port)
luma_device = ssd1306(luma_serial, width=128, height=64, rotate=0)
# luma_device.persist = True  # Do not clear display on exit


font1 = ImageFont.truetype("./fonts/FreePixel.ttf", 16)
font2 = ImageFont.truetype("./fonts/OLED.otf", 12)
white = ImageColor.getcolor("white", "1")
black = ImageColor.getcolor("black", "1")

while True:
    time_str = "{0:%H:%M:%S}".format(datetime.datetime.now())
    print(f"Drawing {time_str}", flush=True)
    # The canvas is drawn from scratch and is sent in its entirety to the display
    # upon exiting the 'with' clause.
    with canvas(luma_device) as draw:
        draw.rectangle(luma_device.bounding_box, outline=white, fill=black)
        draw.text((20, 14), f"SPI Adapter", fill=white, font=font1)
        draw.text((33, 40), f"{time_str}", fill=white, font=font2)
        # Uncomment to save screenshot.
        # draw._image.save("oled_demo_screenshot.png")
    time.sleep(1.0)
    
