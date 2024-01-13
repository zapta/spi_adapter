// Implementation of board.h

#include "board.h"

#include <Adafruit_NeoPixel.h>

// LED implementation using a simple LED.
class SimpleLed : public Led {
 public:
  SimpleLed(int pin) : _pin(pin) { pinMode(_pin, OUTPUT); };

  virtual void update(bool led_state) override {
    digitalWrite(_pin, led_state);
  }

 private:
  const int _pin;
};

// LED implementation using a NeoPixel.
class NeoPixelLed : public Led {
 public:
  NeoPixelLed(int pin) : _neopixel(1, pin, NEO_GRB + NEO_KHZ800) {
    _neopixel.begin();
  };
  virtual void update(bool led_state) override {
    const uint32_t color = led_state ? 0x001100 : 0x000000;
    _neopixel.setPixelColor(0, color);
    _neopixel.show();
  }

 private:
  Adafruit_NeoPixel _neopixel;
};

namespace board {

#ifdef BOARD_RASPBERRY_PICO
static SimpleLed _led(25);
TwoWire i2c(4, 5);
void setup() {}
#endif

#ifdef BOARD_SPARKFUN_PRO_MICRO_RP2040
static NeoPixelLed _led(25);
TwoWire i2c(16, 17);
void setup() {}
#endif

#ifdef ADAFRUIT_KB2040
static NeoPixelLed _led(17);
TwoWire i2c(12, 13);
void setup() {}
#endif

#ifdef ADAFRUIT_QT_PY_RP2040
static NeoPixelLed _led(12);
TwoWire i2c(22, 23);
void setup() {
  // Pin 11 is used to power the neo pixel so needs to be high.
  pinMode(11, OUTPUT);
  digitalWrite(11, 1);
}
#endif

// Exports _led using its base class.
Led& led = _led;

}  // namespace board
