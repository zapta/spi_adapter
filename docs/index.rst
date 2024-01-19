.. SPI Adapter API documentation master file, created by
   sphinx-quickstart on Sun Dec 31 17:40:24 2023.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

.. See rst cheat sheet at 
   https://docs.anaconda.com/restructuredtext/index.html

Overview
========

The SPI Adapter is a USB to SPI bridge that uses off-the-shelf and inexpensive boards such as the 
Raspberry Pi Pico, and control it using the python package ``spi_adapter``.

For example, the diagram below shows the wiring to control a SPI OLED display using
USB and Python API. The full code is provided in the ``examples`` directory of the github repository.

|

.. image:: ../www/wiring_diagram.png
   :align: center

|

Examples
========

Reading an ADS1118 SPI analog to digital converter from Python.

.. code-block:: python
  :linenos:

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

|

Reading and writing auxiliary I/O pins:

.. code-block:: python
  :linenos:

  import time
  from spi_adapter import SpiAdapter, AuxPinMode

  # Customize for your system.
  port = "COM18"
  aux_out_pin = 0
  aux_in_pin = 1

  # Configure the two aux pins.
  spi = SpiAdapter(port)
  spi.set_aux_pin_mode(aux_out_pin, AuxPinMode.OUTPUT)
  spi.set_aux_pin_mode(aux_in_pin, AuxPinMode.INPUT_PULLUP)

  # Access the two pins.
  i = 0
  while True:
    i += 1
    spi.write_aux_pin(aux_out_pin, i % 2)   # Generates a square wave
    in_value = spi.read_aux_pin(aux_in_pin)
    print(f"{i:03d}: Input pin value: {in_value}", flush=True)
    time.sleep(0.5)
    
|

Supported Boards
================

The able below lists the currently supported boards.
To make your own SPI Adapter, get one of these boards, and flash it according to the manufacturer's 
instructions with the corresponding SPI Adapter firmware from https://github.com/zapta/spi_adapter/tree/main/firmware/release. 

:Example: 
  For the Raspberry Pico and similar RP2040 boards, flash it by connecting the board
  to your computer while holding the BOOTSEL button. Once your computer recognized the board 
  as a new hard driver, release the button and copy the firmware file to that hard drive.

+---------------------------------------------------------------------------------+------------------+----------------+-----------+
|  Board                                                                          | CLK, MOSI, MISO  |  CS0 - CS3     |  Aux pins |
+=================================================================================+==================+================+===========+
| `Raspberry Pi Pico <https://www.raspberrypi.com/products/raspberry-pi-pico/>`_  | GP 18,19,16      | GP 20,21,22,26 | GP 0-7    |
+---------------------------------------------------------------------------------+------------------+----------------+-----------+
| `Sparkfun Pro Micro RP2040 <https://www.sparkfun.com/products/18288>`_          | GP 18,19,16      | GP 20,21,22,26 | GP 0-7    |
+---------------------------------------------------------------------------------+------------------+----------------+-----------+
| `Adafruit KB2040 <https://learn.adafruit.com/adafruit-kb2040/overview>`_        | GP 18,19,16      | GP 20,21,22,26 | GP 0-7    |
+---------------------------------------------------------------------------------+------------------+----------------+-----------+
| `Adafruit QT Py RP2040 <https://www.adafruit.com/product/4900>`_                | GP 18,19,16      | GP 20,21,22,26 | GP 0-7    |
+---------------------------------------------------------------------------------+------------------+----------------+-----------+

|

Raspberry PI Pico Pinout
========================
The diagram below shows the pinout for the popular Raspberry Pi Pico. For the other supported board, consult the table above.


.. image:: ../www/pinout.png
   :align: center
   :height: 500px

|

API Installation
================

The Python API package is available from PyPi at https://pypi.org/project/spi-adapter and can be installed
on your computer using pip:

.. code-block:: shell

  pip install spi_adapter

:Note: 
  The SPI Adapter boards appear on the computer as a standard CDC serial port and
  thus do not require driver installation.

|

API Reference
=============

.. automodule:: spi_adapter
  :members:
  :member-order: bysource

|

The Wire Protocol
=================

The ``spi_adapter`` package communicates with the SPI Adapter board by sending commands
and receiving command responses on a serial connection. The commands and responses are made of a plain sequence of
'binary' bytes with no special encoding such as end of line or byte stuffing. For 
an updated specification of the commands and their wire representation see the  
`firmware protocol implementation <https://github.com/zapta/spi_adapter/blob/main/firmware/platformio/src/main.cpp>`_.

|

Firmware Development
=====================

The firmware is written in C++ and is developed as a platformio project under Visual Studio Code. The following
sections summarize the key aspect of the firmware development.

Project Structure
----------------------------
The platformio project resides in the firmware/platformio directory of the SPI Adapter repository https://github.com/zapta/spi_adapter, 
the project configuration is in the `platformio.ini <https://github.com/zapta/spi_adapter/tree/main/firmware/platformio>`_ file
and the source code is in the  `src directory <https://github.com/zapta/spi_adapter/blob/main/firmware/platformio/src>`_.

Setting up the environment
--------------------------
1. Install Microsoft's Visual Studio Code ('VSC')
#. In VSC, add the extension 'platformio'
#. Clone the I2C Adapter `github repository <https://github.com/zapta/spi_adapter>`_ on your computer.
#. Use VSC's 'file | open-folder', to open the 'platformio' directory in your local repository.
#. After platformio will complete installing the necessary tools, click on the 'build' icon in the status bar to verify that the project builds correctly.

Testing a new firmware version
------------------------------
1. Make the changes in the source code.
#. Connect a compatible board to your computer.
#. Select in the status bar the board target that matches your board.
#. Use the 'upload' button in the status bar to build and upload the binary to the board.

Generating new binaries
-----------------------
Run the python script 'build_env.py' and it will build binaries for all the targets and will copy them to 
release directory.

Adding a new board
------------------------------
Board definitions resides in platformio.ini and in src/board.cpp and the amount
of refactoring needed to add a board depends how close it is to the existing boards.
Adding a typical board includes adding:

* A new target to platformio.ini

* A new section in src/boards.cpp.

* A new row to the documentation's list.

* A new binary to the release.

|

Contact
=======

Bug reports and contributions are welcome. You can contact the team and fellow users at the 
gibhub repository at https://github.com/zapta/spi_adapter.



.. toctree::
  :maxdepth: 2
  :caption: Contents:

