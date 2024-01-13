
// Board abstraction. Allow to retarget to different boards.

#pragma once

#include <Wire.h>

// An abstrat LED.
class Led {
 public:
  virtual void update(bool led_state) = 0;
};

namespace board {

extern void setup();
extern Led& led;
extern TwoWire i2c;

}  // namespace board
