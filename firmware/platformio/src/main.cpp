// Firmware of the SPI Adapter implementation using a Raspberry Pico.

#include <Arduino.h>
#include <SPI.h>

#include "board.h"

// #pragma GCC push_options
// #pragma GCC optimize("Og")

using board::led;



// SPI pins:
//   PIN_SPI_SCK   GP18
//   PIN_SPI_MOSI  GP19
//   PIN_SPI_MISO  GP16

// Maps CS pin index to gp pin index.
static uint8_t cs_pins[] = {
    10,  // CS 0 = GP10
    11,  // CS 1 = GP11
    12,  // CS 2 = GP12
    13,  // CS 3 = GP13
};

static constexpr uint8_t kNumCsPins = sizeof(cs_pins) / sizeof(*cs_pins);
static_assert(kNumCsPins == 4);

// Maps aux pin index to gp pin index.
static uint8_t aux_pins[] = {
    0,  // Aux 0 = GP0
    1,  // Aux 0 = GP1
    2,  // Aux 0 = GP2
    3,  // Aux 0 = GP3
    4,  // Aux 0 = GP4
    5,  // Aux 0 = GP5
    6,  // Aux 0 = GP6
    7,  // Aux 0 = GP7
};

static constexpr uint8_t kNumAuxPins = sizeof(aux_pins) / sizeof(*aux_pins);
static_assert(kNumAuxPins == 8);

static constexpr uint8_t kApiVersion = 1;
static constexpr uint16_t kFirmwareVersion = 1;

// Max number of bytes per transaction.
// NOTE: We have an issue with custom data larger than 256 bytes so for now
// we limit the trnasaction size to 256 bytes. If needed, fix it and increase.
static constexpr uint16_t kMaxTransactionBytes = 256;

// All command bytes must arrive within this time period.
static constexpr uint32_t kCommandTimeoutMillis = 250;

// Since LED updates may involved neopixel communication, we minimize
// it by filtering the 'no-change' updates.
static bool last_led_state;

// A temporary buffer for commands and SPI operations.
static uint8_t data_buffer[kMaxTransactionBytes];
// The number of valid bytes in data_buffer.
static uint16_t data_size = 0;

// Tracks the last spi mode we used. Used to implement a woraround for
// clock polarity change which requires changing the idle SPI clock
// level. See https://github.com/arduino/ArduinoCore-mbed/issues/828
static SPIMode last_spi_mode = SPI_MODE1;

static void track_spi_clock_polarity(SPIMode new_spi_mode) {
  // No change.
  if (new_spi_mode == last_spi_mode) {
    return;
  }

  // Perform a dummy transaction to settle the clock level.
  SPISettings spi_setting(4000000, MSBFIRST, new_spi_mode);
  SPI.beginTransaction(spi_setting);
  uint8_t dummy_byte = 0;
  SPI.transfer(&dummy_byte, 0);
  SPI.endTransaction();

  // Update
  last_spi_mode = new_spi_mode;
}

// A simple timer.
// Cveate: overflows 50 days after last reset().
class Timer {
 public:
  Timer() { reset(millis()); }
  void reset(uint32_t millis_now) { _start_millis = millis_now; }
  uint32_t elapsed_millis(uint32_t millis_now) {
    return millis_now - _start_millis;
  }

 private:
  uint32_t _start_millis;
};

// Turn off all CS outputs.
static inline void all_cs_off() {
  static_assert(kNumCsPins == 4);
  digitalWrite(cs_pins[0], HIGH);
  digitalWrite(cs_pins[1], HIGH);
  digitalWrite(cs_pins[2], HIGH);
  digitalWrite(cs_pins[3], HIGH);
}

// Turn on a specific CS output.
static inline void cs_on(uint8_t cs_index) {
  if (cs_index < kNumCsPins) {
    digitalWrite(cs_pins[cs_index], LOW);
  }
}

// Time since the start of last cmd.
static Timer cmd_timer;

// Fill data_buffer with n bytes. Done in chunks. data_size tracks the
// num of bytes read so far.
static bool read_serial_bytes(uint16_t n) {
  // Handle the case where not enough chars.
  const uint16_t avail = Serial.available();
  const uint16_t required = n - data_size;
  const uint16_t requested = std::min(avail, required);

  if (requested) {
    size_t actual_read =
        Serial.readBytes((char*)(&data_buffer[data_size]), requested);
    data_size += actual_read;
  }

  return data_size >= n;
}

// Abstract base of all command handlers.
class CommandHandler {
 public:
  CommandHandler(const char* name) : _name(name) {}
  const char* cmd_name() const { return _name; }
  // Called each time the command starts to allow initialization.
  virtual void on_cmd_entered() {}
  // Returns true if command completed.
  virtual bool on_cmd_loop() = 0;
  // Call if the command is aborted due to timeout.
  virtual void on_cmd_aborted() {}

 private:
  const char* _name;
};

// ECHO command. Recieves a byte and echoes it back as a response. Used
// to test connectivity with the driver.
//
// Command:
// - byte 0:  'e'
// - byte 1:  Bhar to echo, 0x00 to 0xff
//
// Response:
// - byte 0:  Byte 1 from the command.
//
static class EchoCommandHandler : public CommandHandler {
 public:
  EchoCommandHandler() : CommandHandler("ECHO") {}
  virtual bool on_cmd_loop() override {
    static_assert(sizeof(data_buffer) >= 1);
    if (!read_serial_bytes(1)) {
      return false;
    }
    Serial.write(data_buffer[0]);
    return true;
  }
} echo_cmd_handler;

// INFO command. Provides information about this driver. Currently
// it's a skeleton for future values that will be returned.
//
// Command:
// - byte 0:  'i'
//
// Response:
// - byte 0:  'K' for OK.
// - byte 1:  'S'
// - byte 2:  'P'
// - byte 3:  'I'
// - byte 4:  Number of bytes to follow (3).
// - byte 5:  Version of wire format API.
// - byte 6:  MSB of firmware version.
// - byte 7:  LSB of firmware version.
static class InfoCommandHandler : public CommandHandler {
 public:
  InfoCommandHandler() : CommandHandler("INFO") {}
  virtual bool on_cmd_loop() override {
    Serial.write('K');  // 'K' for OK.
    Serial.write('S');
    Serial.write('P');
    Serial.write('I');
    Serial.write(0x03);                     // Number of bytes to follow.
    Serial.write(kApiVersion);              // API version.
    Serial.write(kFirmwareVersion >> 8);    // Firmware version MSB.
    Serial.write(kFirmwareVersion & 0x08);  // Firmware version LSB.
    return true;
  }
} info_cmd_handler;

// SEND command. Send bytes to a device and read the returned bytes.
//
// Command:
// - byte 0:    's'
// - byte 1:    Config byte, see below
// - byte 2:    Speed in 25Khz steps. Valid range is [1, 160]
// - byte 3,4:  Number custom data bytes to write. Big endian. Should be in
//              the range 0 to (kMaxTransactionBytes - extra_bytes_to_write).
// - byte 5,6:  Number of extra 0x00 bytes to write. Big endian. should
//              range 0 to kMaxTransactionBytes.
// - Byte 7...  The custom data bytes to write.
//
// Error response:
// - byte 0:    'E' for error.
// - byte 1:    Error code, per the list below, providing more information about
// the error.
//
// OK response
// - byte 0:    'K' for 'OK'.
// - byte 1,2:  Number read bytes being return. This is zero if config.b4 is
// zero, else
//              it's the sumr of custom and extra bytes in the request.
// - byte 3...  Returned read bytes.

// Request config byte bits
// 0,1 : CS index.
// 2:3 : SPI mode, per arduino::SPIMode.
// 4   : Include bytes read in response
// 5   : Reserved. Should be 0.
// 6   : Reserved. Should be 0.
// 7   : Reserved. Should be 0.

// Error code:
//  1 : Data too long
//  2 : NACK on transmit of address
//  3 : NACK on transmit of data
//  4 : Other error
//  5 : Timeout
//  8 : Device address is out of range..
//  9 : Custom byte count is out of range.
// 10 : Extra byte count is out of range.
// 11 : Byte count out of limit
// 12 : Speed byte is out of range.
//
static class SendCommandHandler : public CommandHandler {
 public:
  SendCommandHandler() : CommandHandler("SEND") { reset(); }

  virtual void on_cmd_entered() override { reset(); }

  virtual bool on_cmd_loop() override {
    // Read command header.
    if (!_got_cmd_header) {
      static_assert(sizeof(data_buffer) >= 6);
      if (!read_serial_bytes(6)) {
        return false;
      }
      // Parse the command header
      _cs_index = data_buffer[0] & 0b11;
      _spi_mode = (SPIMode)((data_buffer[0] >> 2) & 0b11);
      _return_read_bytes = data_buffer[0] & 0b10000;
      _speed_units = data_buffer[1];
      _custom_data_count = (((uint16_t)data_buffer[2]) << 8) + data_buffer[3];
      _extra_data_count = (((uint16_t)data_buffer[4]) << 8) + data_buffer[5];
      data_size = 0;
      _got_cmd_header = true;

      // Validate the command header.
      const uint8_t error_code =
          (_speed_units < 1 || _speed_units > 160)      ? 0x0c
          : (_custom_data_count > kMaxTransactionBytes) ? 0x09
          : (_extra_data_count > kMaxTransactionBytes)  ? 0x0a
          : (_custom_data_count + _extra_data_count > kMaxTransactionBytes)
              ? 0x0b
              : 0x00;
      if (error_code) {
        Serial.write('E');
        Serial.write(error_code);
        return true;
      }
    }

    // We have a valid header. Now read the custom data bytes, if any.
    static_assert(sizeof(data_buffer) >= kMaxTransactionBytes);
    if (_custom_data_count) {
      if (!read_serial_bytes(_custom_data_count)) {
        return false;
      }
    }

    // At this point, the data buffer has already the custom bytes.
    // Prepare the extra bytes to send.
    static_assert(sizeof(data_buffer) >= kMaxTransactionBytes);
    memset(&data_buffer[_custom_data_count], 0, _extra_data_count);

    // If changing mode, update the clock idle clock level.
    track_spi_clock_polarity(_spi_mode);

    // Perform the SPI transaction using data_buffer as TX/RX buffer.
    const uint32_t frequency_hz = ((uint32_t)_speed_units) * 25000;
    SPISettings spi_setting(frequency_hz, MSBFIRST, _spi_mode);

    cs_on(_cs_index);
    SPI.beginTransaction(spi_setting);

    // Perofrm the transaction, using data_buffer and both TX and RX buffer.
    const uint16_t total_bytes = _custom_data_count + _extra_data_count;
    SPI.transfer(data_buffer, total_bytes);

    SPI.endTransaction();
    all_cs_off();

    // All done. Send OK response.
    Serial.write('K');
    const uint16_t response_count = _return_read_bytes ? total_bytes : 0;
    Serial.write(response_count >> 8);    // Count MSB
    Serial.write(response_count & 0xff);  // Count LSB
    if (response_count) {
      Serial.write(data_buffer, response_count);
    }
    return true;
  }

 private:
  bool _got_cmd_header = false;

  // Command header info.
  uint8_t _cs_index;
  SPIMode _spi_mode;
  bool _return_read_bytes;
  uint8_t _speed_units;
  uint16_t _custom_data_count;
  uint16_t _extra_data_count;

  void reset() {
    _got_cmd_header = false;
    _cs_index = 0;
    _spi_mode = SPI_MODE0;
    _return_read_bytes = false;
    _speed_units = 0;
    _custom_data_count = 0;
    _extra_data_count = 0;
  }

} send_cmd_handler;

// SET AUXILARY PIN MODE command.
//
// Command:
// - byte 0:    'm'
// - byte 1:    pin index, 0 - 7
// - byte 2:    pin mode
//
// Error response:
// - byte 0:    'E' for error.
// - byte 1:    Error code, per the list below.
//
// OK response
// - byte 0:    'K' for 'OK'.

// Error codes:
//  1 : Pin index out of range.
//  2 : Mode value out of range.
static class AuxPinModeCommandHandler : public CommandHandler {
 public:
  AuxPinModeCommandHandler() : CommandHandler("AUX_MODE") {}

  virtual bool on_cmd_loop() override {
    // Read command header.
    // if (!_got_cmd_header) {
    static_assert(sizeof(data_buffer) >= 2);
    if (!read_serial_bytes(2)) {
      return false;
    }
    // Parse the command header
    const uint8_t aux_pin_index = data_buffer[0];
    const uint8_t aux_pin_mode = data_buffer[1];

    // Check aux pin index range.
    if (aux_pin_index >= kNumAuxPins) {
      Serial.write('E');
      Serial.write(0x01);
      return true;
    }

    // Map to underlying gpio pin.
    const uint8_t gpio_pin = aux_pins[aux_pin_index];

    // Dispatch by pin mode:
    switch (aux_pin_mode) {
      // Input pulldown
      case 1:
        pinMode(gpio_pin, INPUT_PULLDOWN);
        break;

      // Input pullup
      case 2:
        pinMode(gpio_pin, INPUT_PULLUP);
        break;

      // Output.
      case 3:
        pinMode(gpio_pin, OUTPUT);
        break;

      default:
        Serial.write('E');
        Serial.write(0x02);
        return true;
    }

    // All done Ok
    Serial.write('K');
    return true;
  }

} aux_mode_cmd_handler;

// READ AUXILARY PINS command.
//
// Command:
// - byte 0:    'a'
//
// Error response:
// - byte 0:    'E' for error.
// - byte 1:    Reserved. Always 0.
//
// OK response
// - byte 0:    'K' for 'OK'.
// - byte 1:    Auxilary pins values
static class AuxPinsReadCommandHandler : public CommandHandler {
 public:
  AuxPinsReadCommandHandler() : CommandHandler("AUX_READ") {}

  virtual bool on_cmd_loop() override {
    uint8_t result = 0;
    static_assert(kNumAuxPins == 8);
    for (int i = 7; i >= 0; i--) {
      const uint8_t gpio_pin = aux_pins[i];
      const PinStatus pin_status = digitalRead(gpio_pin);
      result = result << 1;
      if (pin_status) {
        result |= 0b00000001;
      }
    }

    // All done Ok
    Serial.write('K');
    Serial.write(result);
    return true;
  }

} aux_pins_read_cmd_handler;

// WRITE AUXILARY PINS command.
//
// Command:
// - byte 0:    'b'
// - byte 1:    New pins values
// - byte 2:    Write mask. Only pins with a corresponding '1' are written.
//
// Error response:
// - byte 0:    'E' for error.
// - byte 1:    Reserved. Always 0.
//
// OK response
// - byte 0:    'K' for 'OK'.
static class AuxPinsWriteCommandHandler : public CommandHandler {
 public:
  AuxPinsWriteCommandHandler() : CommandHandler("AUX_WRITE") {}

  virtual bool on_cmd_loop() override {
    static_assert(sizeof(data_buffer) >= 2);
    if (!read_serial_bytes(2)) {
      return false;
    }
    const uint8_t values = data_buffer[0];
    const uint8_t mask = data_buffer[1];
    static_assert(kNumAuxPins == 8);
    for (int i = 0; i < 8; i++) {
      if (mask & 1 << i) {
        const uint8_t gpio_pin = aux_pins[i];
        // TODO: We write also to input pins. What is the semantic?
        digitalWrite(gpio_pin, values & 1 << i);
      }
    }

    // All done Ok
    Serial.write('K');
    return true;
  }

} aux_pins_write_cmd_handler;

// Given a command char, return a Command pointer or null if invalid command
// char.
static CommandHandler* find_command_handler_by_char(const char cmd_char) {
  switch (cmd_char) {
    case 'e':
      return &echo_cmd_handler;
    case 'i':
      return &info_cmd_handler;
    case 'm':
      return &aux_mode_cmd_handler;
    case 'a':
      return &aux_pins_read_cmd_handler;
    case 'b':
      return &aux_pins_write_cmd_handler;
    case 's':
      return &send_cmd_handler;
    default:
      return nullptr;
  }
}

void setup() {
  // A short delay to let the USB/CDC settle down. Otherwise
  // it messes up with the debugger, in case it's used.
  delay(500);

  board::setup();
  board::led.update(false);
  last_led_state = false;

  // USB serial.
  Serial.begin(115200);

  // Init CS outputs.
  for (uint8_t i = 0; i < kNumCsPins; i++) {
    auto gp_pin = cs_pins[i];
    pinMode(gp_pin, OUTPUT);
  }
  all_cs_off();

  // Init aux pins as inputs.
  for (uint8_t i = 0; i < kNumAuxPins; i++) {
    auto gp_pin = aux_pins[i];
    pinMode(gp_pin, INPUT_PULLUP);
  }

  // Initialize the SPI channel.
  SPI.begin();
  track_spi_clock_polarity(SPI_MODE0);
}

// If in command, points to the command handler.
static CommandHandler* current_cmd = nullptr;

void loop() {
  Serial.flush();
  const uint32_t millis_now = millis();
  const uint32_t millis_since_cmd_start = cmd_timer.elapsed_millis(millis_now);

  // Update LED state. Solid if active or short blinks if idle.
  {
    const bool is_active = current_cmd || millis_since_cmd_start < 200;
    const bool new_led_state =
        is_active || (millis_since_cmd_start & 0b11111111100) == 0;
    if (new_led_state != last_led_state) {
      led.update(new_led_state);
      last_led_state = new_led_state;
    }
  }

  // If a command is in progress, handle it.
  if (current_cmd) {
    // Handle command timeout.
    if (millis_since_cmd_start > kCommandTimeoutMillis) {
      current_cmd->on_cmd_aborted();
      current_cmd = nullptr;
      return;
    }
    // Invoke command loop.
    const bool cmd_completed = current_cmd->on_cmd_loop();
    if (cmd_completed) {
      current_cmd = nullptr;
    }
    return;
  }

  // Not in a command. Turn off all CS outputs. Just in case.
  all_cs_off();

  // Try to read selection char of next command.
  static_assert(sizeof(data_buffer) >= 1);
  data_size = 0;
  if (!read_serial_bytes(1)) {
    return;
  }

  // Dispatch the next command by the selection char.
  current_cmd = find_command_handler_by_char(data_buffer[0]);
  if (current_cmd) {
    cmd_timer.reset(millis_now);
    data_size = 0;
    current_cmd->on_cmd_entered();
    // We call on_cmd_loop() on the next iteration, after updating the LED.
  } else {
    // Unknown command selector. We ignore it silently.
  }
}
