"""The ``spi_adapter`` package provides the API to access SPI Adapter boards. To access an SPI Adapter,
create an object of the  class SPIAdapter, and use the methods it provides.
"""

from typing import Optional, List, Tuple
from serial import Serial
from enum import Enum
import time


# NOTE: Numeric values match wire protocol.
class AuxPinMode(Enum):
    """Auxilary pin modes."""

    INPUT_PULLDOWN = 1
    INPUT_PULLUP = 2
    OUTPUT = 3


class SpiAdapter:
    """Connects to the SPI Adapter at the specified serial port and asserts that the
    SPI responses as expcted.

    :param port: The serial port of the SPI Adapter. SPI Adapters
        appear on the local computer as a standard serial port
    :type port: str
    """

    def __init__(self, port: str):
        self.__serial: Serial = Serial(port, timeout=1.0)
        if not self.test_connection_to_adapter():
            raise RuntimeError(f"spi driver not detected at port {port}")
        adapter_info = self.__read_adapter_info()
        if adapter_info is None:
            raise RuntimeError(f"SPI driver failed to read adapter info at {port}")
        print(f"Adapter info: {adapter_info.hex(" ")}", flush=True)
        if (
            adapter_info[0] != ord("S")
            or adapter_info[1] != ord("P")
            or adapter_info[2] != ord("I")
            or adapter_info[3] != 0x3
        ):
            raise RuntimeError(f"Unexpected SPI adapter info at {port}")

    def __read_adapter_response(self, op_name: str, ok_resp_size: int) -> bytes:
        """A common method to read a response from the adapter.
        Returns None if error, otherwise OK response bytes"""
        assert isinstance(op_name, str)
        assert isinstance(ok_resp_size, int)
        assert 0 <= ok_resp_size
        # Read status flag.
        ok_resp = self.__serial.read(1)
        assert isinstance(ok_resp, bytes), type(ok_resp)
        if len(ok_resp) != 1:
            print(
                f"{op_name}: status flag read mismatch, expected {1}, got {len(ok_resp)}",
                flush=True,
            )
            return None
        status_flag = ok_resp[0]
        if status_flag not in (ord("E"), ord("K")):
            print(
                f"{op_name}: unexpected status flag in response: {ok_resp}", flush=True
            )
            return None

        # Handle the case of an error
        if status_flag == ord("E"):
            # Read the additional error info byte.
            ok_resp = self.__serial.read(1)
            assert isinstance(ok_resp, bytes), type(ok_resp)
            if len(ok_resp) != 1:
                print(
                    f"{op_name}: error info read mismatch, expected {1}, got {len(ok_resp)}",
                    flush=True,
                )
                return None
            print(f"{op_name}: failed with error code {ok_resp[0]}", flush=True)
            return None

        # Handle the OK case.
        #
        # Read the returned data count.
        ok_resp = self.__serial.read(ok_resp_size)
        assert isinstance(ok_resp, bytes), type(ok_resp)
        if len(ok_resp) != ok_resp_size:
            print(
                f"{op_name}: OK resp read count mismatch, expected {ok_resp_size}, got {len(ok_resp)}",
                flush=True,
            )
            return None
        return ok_resp

    def send(
        self,
        data: bytearray | bytes,
        extra_bytes: int = 0,
        cs: int = 0,
        mode: int = 0,
        speed: int = 1000000,
        read: bool = True,
    ) -> bytearray | None:
        """Perform an SPI transaction.

        :param write_data: Bytes to write to the device. The number of bytes must be 256 at most.
        :type write_data: bytearray | bytes | None

        :param extra_bytes: Number of additional ``0x00`` bytes to write to the device. This is typically use to read
          a response from the device. The value ``len(data) + extra_bytes`` should not exceed 256.
        :type extra_bytes: int

        :param cs: The Chip Select (CS) output to use for this transaction. This allows to connect the SPI Adapter to multiple
           SPI devices.
        :type cs: int

        :param mode: The SPI mode to use. Should be in the range [0, 3].
        :type mode: int

        :param speed: The SPI speed in Hz and must be in the range 25Khz to 4Mhz. The value
                      is rounded silently to a 25Khz increment.
        :type speed: int

        :param read: Indicates if the response should include the bytes read
           on the MISO line during the writing of ``data`` and ``extra_bytes``.
        :type read: bool

        :returns: If error, returns None, otherwise returns a ``bytearray``. If ``read == True``
           then the bytearray contains exactly ``len(data) + extra_bytes`` bytes that were read during
           the transaction. Otherwise the bytearray is empty(). Skipping the reading may improve
           the performance of large write only transactions.
        :rtype: bytearray | None
        """
        assert isinstance(data, (bytearray, bytes))
        assert len(data) <= 256
        assert isinstance(extra_bytes, int)
        assert 0 <= extra_bytes <= 256
        assert (len(data) + extra_bytes) <= 256
        assert isinstance(cs, int)
        assert 0 <= cs <= 3
        assert isinstance(mode, int)
        assert 0 <= mode <= 3
        assert isinstance(speed, int)
        assert 25000 <= speed <= 4000000
        assert isinstance(read, bool)

        # Construct and send the command request.
        req = bytearray()
        req.append(ord("s"))
        # print(f"Read: {read}", flush=True)
        config_byte = 0b10000 if read else 0b00000
        config_byte |= mode << 2
        config_byte |= cs
        # print(f"Config byte: {config_byte:08b}", flush=True)
        req.append(config_byte)
        speed_byte = int(round(speed / 25000))
        # print(f"Speed byte: {speed_byte}, speed={speed}", flush=True)
        assert isinstance(speed_byte, int)
        assert 1 <= speed_byte <= 160
        req.append(speed_byte)
        req.append(len(data) // 256)
        req.append(len(data) % 256)
        req.append(extra_bytes // 256)
        req.append(extra_bytes % 256)
        req.extend(data)
        n = self.__serial.write(req)
        if n != len(req):
            print(f"SPI read: write mismatch, expected {len(req)}, got {n}", flush=True)
            return None

        # Read response.
        ok_resp = self.__read_adapter_response("SPI read", 2)
        if ok_resp is None:
            return None

        # Here response was OK. Get the count of returned data bytes read from the device.
        resp_count = (ok_resp[0] << 8) + ok_resp[1]
        expected_resp_count = len(data) + extra_bytes if read else 0
        if resp_count != expected_resp_count:
            print(
                f"SPI read: response count mismatch, expected {expected_resp_count}, got {resp_count}",
                flush=True,
            )
            return None

        # Read the data bytes
        resp = self.__serial.read(resp_count)
        assert isinstance(resp, bytes), type(resp)
        if len(resp) != resp_count:
            print(
                f"SPI read: data read mismatch, expected {resp_count}, got {len(resp)}",
                flush=True,
            )
            return None
        return bytearray(resp)

    def set_aux_pin_mode(self, pin: int, pin_mode: AuxPinMode) -> bool:
        """Sets the mode of an auxilary pin.

        :param pin: The aux pin index, should be in [0, 7].
        :type pin: int

        :param pin_mode: The new pin mode.
        :type pin_mode: AuxPinMode

        :returns: True if OK, False otherwise.
        :rtype: bool
        """
        assert isinstance(pin, int)
        assert 0 <= pin <= 7
        assert isinstance(pin_mode, AuxPinMode)
        req = bytearray()
        req.append(ord("m"))
        req.append(pin)
        req.append(pin_mode.value)
        self.__serial.write(req)
        ok_resp = self.__read_adapter_response("Aux mode", 0)
        if ok_resp is None:
            return False
        return True

    def read_aux_pins(self) -> int | None:
        """Reads the auxilary pins.

        :returns: The pins value as a 8 bit in value or None if an error.
        :rtype: int | None
        """
        req = bytearray()
        req.append(ord("a"))
        self.__serial.write(req)
        ok_resp = self.__read_adapter_response("Aux read", 1)
        if ok_resp is None:
            return None
        return ok_resp[0]

    def write_aux_pins(self, values, mask=0b11111111) -> bool:
        """Writes the aux pins.

        :param values: An 8 bits integer with the bit values to write. In the range [0, 255].
        :type values: int

        :param mask: An 8 bits int with mask that indicates which auxilary pins should be written. If
            the corresponding bits is 1 than the pin is updated otherwise it's left as is.
        :type mask: int

        :returns: True if OK, False otherwise.
        :rtype: bool
        """
        assert isinstance(values, int)
        assert 0 <= values <= 255
        assert isinstance(mask, int)
        assert 0 <= mask <= 255
        req = bytearray()
        req.append(ord("b"))
        req.append(values)
        req.append(mask)
        self.__serial.write(req)
        ok_resp = self.__read_adapter_response("Aux write", 0)
        if ok_resp is None:
            return False
        return True
      
    def read_aux_pin(self, aux_pin_index:int) -> bool | None:
        """Read a single aux pin.

        :param aux_pin_index: An aux pin index in the range [0, 7]
        :type aux_pin_index: int

        :returns: The boolean value of the pin or None if error.
        :rtype: bool | None
        """
        assert isinstance(aux_pin_index, int)
        assert 0 <= aux_pin_index <= 7
        pins_values = self.read_aux_pins()
        if pins_values is None:
          return None
        return True if pins_values & (1 << aux_pin_index) else False
      
    def write_aux_pin(self, aux_pin_index:int, value: bool | int) -> bool:
        """Writes a single aux pin.

        :param aux_pin_index: An aux pin index in the range [0, 7]
        :type aux_pin_index: int

        :param value: The value to write.
        :type value: bool | int

        :returns: True if OK, False otherwise.
        :rtype: bool
        """
        assert isinstance(aux_pin_index, int)
        assert 0 <= aux_pin_index <= 7
        assert isinstance(value, (bool, int))
        pin_mask = 1 << aux_pin_index
        pin_value_mask = pin_mask if value else 0
        return self.write_aux_pins(pin_value_mask, pin_mask)

    def test_connection_to_adapter(self, max_tries: int = 3) -> bool:
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

    def __read_adapter_info(self) -> Optional[bytearray]:
        """Return adapter info or None if an error."""
        req = bytearray()
        req.append(ord("i"))
        n = self.__serial.write(req)
        if n != len(req):
            print(
                f"SPI adapter info: write mismatch, expected {len(req)}, got {n}",
                flush=True,
            )
            return None
        ok_resp = self.__read_adapter_response("SPI adapter info", ok_resp_size=7)
        return ok_resp
