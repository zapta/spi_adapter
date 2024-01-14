// Firmware of the I2C Adapter implementation using a Raspberry Pico.

#include <Arduino.h>
// #include <Wire.h>
#include <SPI.h>

#include "board.h"

// TODO: Add support for debug info using an auxilary UART.
// TODO: Add handling of SEND config
// TODO: Initialize the SPI hardware
// TODO: Add handling of CS.

// Arduino pins definitions:
// #define PIN_SPI_MISO  (16u)
// #define PIN_SPI_MOSI  (19u)
// #define PIN_SPI_SCK   (18u)

// using board::i2c;
using board::led;

static constexpr uint8_t kApiVersion = 1;
static constexpr uint16_t kFirmwareVersion = 1;

// Max number of bytes per transaction.
static constexpr uint16_t kMaxTransactionBytes = 1024;

// All command bytes must arrive within this time period.
static constexpr uint32_t kCommandTimeoutMillis = 250;

// Since LED updates may involved neopixel communication, we minimize
// it by filtering the 'no-change' updates.
static bool last_led_state;

// A temporary buffer for commands and SPI operations.
static uint8_t data_buffer[kMaxTransactionBytes];

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

// Time since the start of last cmd.
static Timer cmd_timer;

// Read exactly n chanrs to data buffer. If not enough bytes, none is read
// and the function returns false.
static bool read_serial_bytes(uint8_t* bfr, uint16_t n) {
  // Handle the case where not enough chars.
  const int avail = Serial.available();
  if (avail < (int)n) {
    return false;
  }

  // TODO: Verify actual read == n;
  size_t actual_read = Serial.readBytes((char*)bfr, n);
  (void)actual_read;
  return true;
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
    if (!read_serial_bytes(data_buffer, 1)) {
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
// - byte 0:  Number of bytes to follow (3).
// - byte 1:  Version of wire format API.
// - byte 2:  MSB of firmware version.
// - byte 3:  LSB of firmware version.
static class InfoCommandHandler : public CommandHandler {
 public:
  InfoCommandHandler() : CommandHandler("INFO") {}
  virtual bool on_cmd_loop() override {
    Serial.write(0x05);                     // Number of bytes to follow.
    Serial.write(0x12);                     // Magic number. MSB
    Serial.write(0x34);                     // Magic Number. LSB
    Serial.write(kApiVersion);              // API version.
    Serial.write(kFirmwareVersion >> 8);    // Firmware version MSB.
    Serial.write(kFirmwareVersion & 0x08);  // Firmware version LSB.
    return true;
  }
} info_cmd_handler;

// SEND command. Writes N bytes to an I2C device.
//
// Command:
// - byte 0:    's'
// - byte 1:    Config byte, see below
// - byte 2,3:  Number custom data bytes to write. Big endian. Should be in the
//              range 0 to (kMaxTransactionBytes - extra_bytes_to_write).
// - byte 4,5:  Number of extra 0x00 bytes to write. Big endian. should
//              range 0 to kMaxTransactionBytes.
// - Byte 6...  The custom data bytes to write.
//
// Error response:
// - byte 0:    'E' for error.
// - byte 1:    Additional device specific internal error info per the list
// below.
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

// Additional error response info:
//  1 : Data too long
//  2 : NACK on transmit of address
//  3 : NACK on transmit of data
//  4 : Other error
//  5 : Timeout
//  8 : Device address out of range..
//  9 : Custom byte count out of range.
// 10 : Extra byte count out of range.
// 11 : Byte count out of limit
//
static class SendCommandHandler : public CommandHandler {
 public:
  SendCommandHandler() : CommandHandler("SEND") {}
  virtual void on_cmd_entered() override {
    _got_cmd_header = false;
    _return_read_bytes = false;
    _spi_mode = SPI_MODE0;
    _custom_data_count = 0;
    _extra_data_count = 0;
  }
  virtual bool on_cmd_loop() override {
    // Read command header.
    if (!_got_cmd_header) {
      static_assert(sizeof(data_buffer) >= 5);
      if (!read_serial_bytes(data_buffer, 5)) {
        return false;
      }
      // Parse the command header
      // _config = data_buffer[0];
      _spi_mode = (SPIMode) (data_buffer[0] & 0b11);
      _return_read_bytes = data_buffer[0] & 0b10000;
      _custom_data_count = (((uint16_t)data_buffer[1]) << 8) + data_buffer[2];
      _extra_data_count = (((uint16_t)data_buffer[3]) << 8) + data_buffer[4];
      _got_cmd_header = true;

      // Validate the command header.
      uint8_t status =
          (_custom_data_count > kMaxTransactionBytes)  ? 0x09
          : (_extra_data_count > kMaxTransactionBytes) ? 0x0a
          : (_custom_data_count + _extra_data_count > kMaxTransactionBytes)
              ? 0x0b
              : 0x00;
      if (status != 0x00) {
        Serial.write('E');
        Serial.write(status);
        return true;
      }
    }

    // We have a valid header. Now read the custom data bytes, if any.
    static_assert(sizeof(data_buffer) >= kMaxTransactionBytes);
    if (_custom_data_count) {
      if (!read_serial_bytes(data_buffer, _custom_data_count)) {
        return false;
      }
    }

    // Perform the SPI transaction
    SPISettings spi_setting(4000000, MSBFIRST, _spi_mode);
    SPI.beginTransaction(spi_setting);
    uint16_t i = 0;
    while (i < _custom_data_count) {
      data_buffer[i] = SPI.transfer(data_buffer[i]);
      i++;
    }
    const uint16_t total_bytes = _custom_data_count + _extra_data_count;
    while (i < total_bytes) {
      data_buffer[i] = SPI.transfer(0x00);
      i++;
    }
    SPI.endTransaction();

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
  bool _return_read_bytes = false;
  SPIMode _spi_mode = SPI_MODE0;
  uint16_t _custom_data_count = 0;
  uint16_t _extra_data_count = 0;

} send_cmd_handler;

// Given a command char, return a Command pointer or null if invalid command
// char.
static CommandHandler* find_command_handler_by_char(const char cmd_char) {
  switch (cmd_char) {
    case 'e':
      return &echo_cmd_handler;
    case 'i':
      return &info_cmd_handler;
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

  // spi_settings.bitOrder(MSBFIRST);

  SPI.begin();
  // i2c.setClock(400000);   // 400Khz.
  // i2c.setTimeo(ut(50000);  // 50ms timeout.
  // i2c.begin();
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

  // Not in a command.
  // Try to read selection char of next command.
  static_assert(sizeof(data_buffer) >= 1);
  if (!read_serial_bytes(data_buffer, 1)) {
    return;
  }

  // Dispatch the next command by the selection char.
  current_cmd = find_command_handler_by_char(data_buffer[0]);
  if (current_cmd) {
    cmd_timer.reset(millis_now);
    current_cmd->on_cmd_entered();
    // We call on_cmd_loop() on the next iteration, after updating the LED.
  } else {
    // Unknown command selector. We ignore it silently.
  }
}
