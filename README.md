# A Simple USB to SPI Adapter that works.

The SPI Adapter allows python programs to connect to SPI devices using off the shelf low cost boards such the Raspberry Pico or SparkFun Pro Micro - RP2040. The SPI Adapter appears on the computer as a serial port (no device installation required) and acts as a USB to SPI bridge, with the ``spi_adapter`` Python package providing an easy to use API.


For example, the diagram below shows the wiring of the [oled_demo.py](https://github.com/zapta/spi_adapter/blob/main/examples/oled_demo.py) example which drives an SPI OLED display using an SPI Adapter and the luma.oled python package.

<br>
<img  src="https://raw.githubusercontent.com/zapta/spi_adapter/main/www/wiring_diagram.png"
      style="display: block;margin-left: auto;margin-right: auto;width: 80%;" />
<br>



## Highlights

* Provides USB to SPI bridge.
* Supports Windows/Mac/Linux.
* Uses low cost low cost off-the-shelf boards as adapters.
* Does not require driver installation (it appears on the computer as standard a serial port).
* Comes with an easy to use Python API.
* Easy to modify/extend and to adapt to new hardware.
* Permissive open source license. Comercial use OK, sharing and attribution not required. 
* Provides additional 8 general purpose auxilary input/output signals.

<br>

## Python API Example

Package installation

```bash
pip install spi-adapter --upgrade
```

In the example below, we use an SPI Adapter that appears as serial port "COM7" to access an ADS1118 SPI ADC device.

```python
import time
from spi_adapter import SpiAdapter

spi =  SpiAdapter(port = "COM18)

# Single shot, 2.046v FS, Input (A0, GND).
adc_cmd = bytes([0b11000101, 0b10001010, 0x00, 0x00])

while True:
  # Read previous value and start a the next conversion.
  response_bytes = spi.send(adc_cmd, mode=1)
  adc_value = int.from_bytes(response_bytes[0:2], byteorder='big', signed=True)
  print(f"ADC: {adc_value}", flush=True)
  time.sleep(0.5)
```

<br>

## Documentation

Full documentation is available at <https://spi-adapter.readthedocs.io/>
