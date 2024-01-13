#!python

# This program demonstrates how to use the I2CAdapter to allow the luma.oled
# package to draw on an I2C Oled display. In this example we use a 128x64
# SH1106 display.

import time
import datetime

from i2c_adapter import I2cAdapter
from luma.oled.device import sh1106
from luma.core.render import canvas
from PIL import ImageFont, ImageColor


# Related readings
# - https://buildmedia.readthedocs.org/media/pdf/luma-oled/rtd-update/luma-oled.pdf
# - https://github.com/rm-hull/luma.core/blob/master/luma/core/interface/serial.py#L25
# - https://github.com/rm-hull/luma.examples/blob/master/examples/sys_info.py
# - https://github.com/rm-hull/luma.examples/tree/master/examples
# - https://luma-oled.readthedocs.io/en/latest/
# - https://stackoverflow.com/questions/64189757/add-element-to-oled-display-via-pil-python-without-erasing-rest


# Customize for your system.
my_port = "COM20"
my_oled_addr = 0x3C


class MyLumaSerial:
    """Implementation of the luma.core.interface.serial interface using an I2C Adapter.
    See luma.core.interface.serial.i2c for an example.
    """

    def __init__(self, port: str, addr: int, cmd_mode: int, data_mode: int):
        """Open the I2C Adapter and initialize this Luma serial instance."""
        self._i2c = I2cAdapter(port)
        self._addr = int(str(addr), 0)
        self._cmd_mode = bytes([cmd_mode])
        self._data_mode = bytes([data_mode])

    def command(self, *cmd):
        """Send to the I2C display a command with given bytes."""
        payload = self._cmd_mode + bytes(list(cmd))
        assert self._i2c.write(self._addr, payload)

    def data(self, data):
        """Send to the I2C display data with given bytes."""
        i = 0
        n = len(data)
        while i < n:
            # I2C Adapter limits to 256 bytes payload.
            chunk_size = min(255, n - i)
            payload = self._data_mode + bytes(data[i : i + chunk_size])
            assert self._i2c.write(self._addr, payload)
            i += chunk_size


luma_serial = MyLumaSerial(my_port, addr=my_oled_addr, cmd_mode=0x00, data_mode=0x40)
luma_device = sh1106(luma_serial, width=128, height=64, rotate=0)
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
        draw.text((20, 14), f"I2C Adapter", fill=white, font=font1)
        draw.text((33, 40), f"{time_str}", fill=white, font=font2)
        # Uncomment to save screenshot.
        # draw._image.save("oled_demo_screenshot.png")
    time.sleep(1.0)
