# AD9833 DDS SPI driver.

# See example here
# https://github.com/RobTillaart/AD9833/blob/master/AD9833.cpp

import sys
import time
from spi_adapter import SpiAdapter

#port = "COM18"
port = "/dev/tty.usbmodem101"

spi: SpiAdapter = None

dds_on: bool = False

def ones(num_bits: int) -> int:
    """Construct a bit mask with N LSB bits set."""
    assert isinstance(num_bits, int)
    assert 0 <= num_bits <= 16
    result = int((1 << (num_bits)) - 1)
    assert isinstance(result, int)
    assert 0 <= result <= 0xffff,  f"{num_bits = }, {result = }"
    return result


def bits(*bit_indexes: int) -> int:
    """Construct a bit mask with given bits set."""
    result: int = 0
    for bit_index in bit_indexes:
        assert isinstance(bit_index, int), type(bit_index)
        assert 0 <= bit_index <= 15
        result = result | (1 << bit_index)
    assert isinstance(result, int)
    assert 0 <= result <= ones(16)
    return result


def send_words(*words: int) -> None:
    """Send to the DDS device N 16 bit words over SPI."""
    global spi
    assert len(words) > 0
    data_bytes = bytearray()
    for w in words:
        assert isinstance(w, int), type(w)
        assert 0 <= w <= ones(16)
        data_bytes.append(w >> 8)
        data_bytes.append(w & ones(8))
    result = spi.send(data_bytes, mode=2,  read=False)
    assert result is not None


def dds_reset() -> None:
    global spi, dds_on
    dds_on = False
    send_words(bits(8))
    send_words(bits())


def dds_set_frequency(f: int) -> None:
    global spi
    # Compute DDS freq register value
    assert isinstance(f, int)
    assert 20 <= f <= 20000
    freq_reg_val = int((1 << 28) * 1000 / 25_000_000)
    assert 0 <= freq_reg_val < (1 << 28)
    # Write to the config register and the frequency reg.
    words = []
    words.append(bits(13))
    words.append(bits(14) | freq_reg_val & ones(14))
    words.append(bits(14) | freq_reg_val >> 14)
    send_words(*words)


def main() -> None:
    global spi
    print(f"Connecting to port {port}...", flush=True)
    spi = SpiAdapter(port=port)
    print(f"Connected.", flush=True)

    print(f"Resetting DDS device", flush=True)
    dds_reset()

    print(f"Setting DDS frequency", flush=True)
    dds_set_frequency(2000)
    print(f"Done")

    #while True:
    #    time.sleep(5.0)
    #    print("loop", flush=True)


if __name__ == "__main__":
    main()
