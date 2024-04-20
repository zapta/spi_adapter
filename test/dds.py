# AD9833 DDS SPI driver.

# See example here
# https://github.com/RobTillaart/AD9833/blob/master/AD9833.cpp

import time
from spi_adapter import SpiAdapter
from typing import List

# port = "COM18"
port = "/dev/tty.usbmodem1101"



class Dds:
    def __init__(self, port: str):
        self.__port = port
        self.__spi = None

    @classmethod
    def ones(cls, num_bits: int) -> int:
        """Construct a bit mask with N LSB bits set."""
        assert isinstance(num_bits, int)
        assert 0 <= num_bits <= 16
        result = int((1 << (num_bits)) - 1)
        assert isinstance(result, int)
        assert 0 <= result <= 0xffff, f"{num_bits = }, {result = }"
        return result

    @classmethod
    def bits(cls, *bit_indexes: int) -> int:
        """Construct a bit mask with given bits set."""
        result: int = 0
        for bit_index in bit_indexes:
            assert isinstance(bit_index, int), type(bit_index)
            assert 0 <= bit_index <= 15
            result = result | (1 << bit_index)
        assert isinstance(result, int)
        assert 0 <= result <= cls.ones(16)
        return result

    def __send_cmd_words(self, *words: int) -> None:
        """Send to the DDS device N 16 bit words over SPI."""
        assert self.__spi is not None
        assert len(words) > 0
        data_bytes = bytearray()
        for w in words:
            assert isinstance(w, int), type(w)
            assert 0 <= w <= self.ones(16)
            data_bytes.append(w >> 8)
            data_bytes.append(w & self.ones(8))
        result = self.__spi.send(data_bytes, mode=2, read=False)
        assert result is not None

    def __frequency_cmd_words(self, freq_hz: int) -> List[int]:
        """Return the command words to set the DDS frequency"""
        # Compute DDS freq register value
        assert isinstance(freq_hz, int)
        assert 0 <= freq_hz <= 20000
        freq_reg_val = int((1 << 28) * freq_hz / 25_000_000)
        assert 0 <= freq_reg_val < (1 << 28)
        # Write to the config register and the frequency reg.
        words = []
        # Config reg.
        words.append(self.bits(13))
        # Freq0 LSB, MSB words.
        words.append(self.bits(14) | freq_reg_val & self.ones(14))
        words.append(self.bits(14) | freq_reg_val >> 14)
        return words

    def connect(self) -> None:
        print(f"Connecting DDS SPI to port {self.__port}.", flush=True)
        assert self.__spi is None
        self.__spi = SpiAdapter(port=self.__port)
        assert self.__spi is not None

    def reset(self) -> None:
        """Reset the DDS. Output is disabled upon return and
        ADC is at mid point."""
        assert self.__spi is not None
        # Set frequency to zero.
        words = self.__frequency_cmd_words(0)
        # Tobble config reset bit on and then off.
        words.append(self.bits(8))
        words.append(self.bits())
        self.__send_cmd_words(*words)

    def set_frequency(self, freq_hz: int) -> None:
        assert self.__spi is not None
        words = self.__frequency_cmd_words(freq_hz)
        self.__send_cmd_words(*words)


def main() -> None:
    dds = Dds(port)
    dds.connect()

    print(f"Resetting DDS device", flush=True)
    dds.reset()

    while True:
        dds.set_frequency(2000)
        time.sleep(0.1)
        dds.reset()
        time.sleep(0.1)


if __name__ == "__main__":
    main()
