"""The ``spi_adapter`` package provides the API to access SPI Adapter boards. To access an SPI Adapter,
create an object of the  class SPIAdapter, and use the methods it provides.
"""

from typing import Optional, List, Tuple
from serial import Serial
import time


class SpiAdapter:
    """Connects to the SPI Adapter at the specified serial port and asserts that the
    SPI responses as expcted.

    :param port: The serial port of the SPI Adapter. SPI Adapters
        appear on the local computer as a standard serial port
    :type port: str
    """

    def __init__(self, port: str):
        self.__serial: Serial = Serial(port, timeout=1.0)
        if not self.test_connection_to_driver():
            raise RuntimeError(f"spi driver not detected at port {port}")

    def send(
        self,  data: bytearray | bytes, extra_write_count: int, cs:int = 0, silent:bool=False
    ) -> Optional[Tuple[bytearray, bytearray]]:
        """Perform an SPI transaction.

        :param write_data: Bytes to write to the device.
        :type write_data: bytearray | bytes | None

        :param extra_write_count: Number of additional ``0x00`` bytes to write to the device. This is typically use to read
          a response from the device. 
        :type extra_write_count: int

        :param cs: The Chip Select (CS) output to use for this transaction. This allows to connect the SPI Adapter to multiple
           SPI devcies.
        :type silent: int

        :param silent: If true, supress printing of error messages. Useful when using the method
            to test the existance of a SPI device.
        :type silent: bool

        :returns: A bytearray with with the bytes read during the transaction, or None if an error. The length 
            of the bytearray is ``len(data) + extra_write_count.
        :rtype: bytearray
        """
        assert False, "Implement me"
        assert isinstance(device_address, int)
        assert 0 <= device_address <= 127
        assert isinstance(byte_count, int)
        assert 0 <= byte_count <= 256

        # Construct and send the command request.
        req = bytearray()
        req.append(ord("r"))
        req.append(device_address)
        req.append(byte_count // 256)
        req.append(byte_count % 256)
        n = self.__serial.write(req)
        if n != len(req):
            print(f"SPI read: write mismatch, expected {len(req)}, got {n}", flush=True)
            return None

        # Read status flag.
        resp = self.__serial.read(1)
        assert isinstance(resp, bytes), type(resp)
        if len(resp) != 1:
            print(
                f"SPI read: status flag read mismatch, expected {1}, got {len(resp)}",
                flush=True,
            )
            return None
        status_flag = resp[0]
        if status_flag not in (ord("E"), ord("K")):
            print(f"SPI read: unexpected status flag in response: {resp}", flush=True)
            return None

        # Handle the case of an error
        if status_flag == ord("E"):
            # Read the additional error info byte.
            resp = self.__serial.read(1)
            assert isinstance(resp, bytes), type(resp)
            if len(resp) != 1:
                print(
                    f"SPI read: error info read mismatch, expected {1}, got {len(resp)}",
                    flush=True,
                )
                return None
            if not slient:
                print(f"SPI read: failed with status = {resp[1]:02x}", flush=True)
            return None

        # Handle the OK case.
        #
        # Read the returned data count.
        resp = self.__serial.read(2)
        assert isinstance(resp, bytes), type(resp)
        if len(resp) != 2:
            print(
                f"SPI read: error count read mismatch, expected {2}, got {len(resp)}",
                flush=True,
            )
            return None
        resp_count = (resp[0] << 8) + resp[1]
        if resp_count != byte_count:
            print(
                f"SPI read: response count mismatch, expected {byte_count}, got {resp_count}",
                flush=True,
            )
            return None

        # Read the data bytes
        resp = self.__serial.read(byte_count)
        assert isinstance(resp, bytes), type(resp)
        if len(resp) != byte_count:
            print(
                f"SPI read: data read mismatch, expected {byte_count}, got {len(resp)}",
                flush=True,
            )
            return None
        return bytearray(resp)

    

    def test_connection_to_driver(self, max_tries: int = 3) -> bool:
        """Tests connection to the SPI Adapter.

        The method tests if the SPI adapter exists and is responding. It is provided
        for diagnostic purposes and is not needed in typical applications.

        :param max_tries: Max number of attempts. The default should be good for most case.
        :type max_tries: int

        :returns: True if connection is OK, false otherwise.
        :rtype: bool 
        """
        assert max_tries > 0
        for i in range(max_tries):
            if i > 0:
                # Delay to let any pending command to timeout.
                time.sleep(0.3)
            ok: bool = True
            for b in [0x00, 0xFF, 0x5A, 0xA5]:
                if not self.__test_echo_cmd(b):
                    ok = False
                    break
            if ok:
                # We had one good pass on all patterns. We are good.
                return True
        # All tries failed.
        return False

    def __test_echo_cmd(self, b: int) -> bool:
        """Test if an echo command with given byte returns the same byte. Used
        to test the connection to the driver."""
        assert isinstance(b, int)
        assert 0 <= b <= 256
        req = bytearray()
        req.append(ord("e"))
        req.append(b)
        self.__serial.write(req)
        resp = self.__serial.read(1)
        assert isinstance(resp, bytes), type(resp)
        assert len(resp) == 1
        return resp[0] == b
