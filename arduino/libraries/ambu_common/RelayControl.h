
#ifndef __RELAY_CONTROL_H__
#define __RELAY_CONTROL_H__

#include <Arduino.h>

#define RELAY_ON  HIGH
#define RELAY_OFF LOW
#define MIN_OFF_MILLIS 10000

class AmbuConfig;
class GenericSensor;

class RelayControl {

      const unsigned int StateOff      = 0;
      const unsigned int StateOn       = 1;
      const unsigned int StateCycleOff = 2;
      const unsigned int StateCycleOn  = 3;

      AmbuConfig * conf_;
      GenericSensor * press_;

      unsigned int state_;
      unsigned int stateTime_;
      unsigned int relayPin_;
      unsigned int cycleCount_;

      char txBuffer_[20];

   public:

      RelayControl (AmbuConfig *conf, GenericSensor *press, unsigned int relayPin);

      void setup();

      void update(unsigned int ctime);

      void sendString();
};

#endif