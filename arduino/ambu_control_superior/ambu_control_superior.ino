
#include <Wire.h>
#include <AmbuConfigUno.h>
#include <RelayControl.h>
#include <SensorDlcL20D4.h>
#include <SensorSp110Sm02Flow.h>
#include <SensorVolume.h>
#include <stdint.h>

#define RELAY_PIN 4
#define SENSOR_PERIOD_MILLIS 9

AmbuConfigUno       * conf  = new AmbuConfigUno();
SensorDlcL20D4      * press = new SensorDlcL20D4();
SensorSp110Sm02Flow * flow  = new SensorSp110Sm02Flow();
SensorVolume        * vol   = new SensorVolume(flow);
RelayControl        * relay = new RelayControl(conf,press,vol,RELAY_PIN);

uint32_t sensorTime;
uint32_t currTime;


void setup() {

   Serial.begin(57600);
   Serial.print("DEBUG Booted\n");

   Wire.begin();

   relay->setup();

   // Wait 5 seconds for pressure to settle
   Serial.print("DEBUG Wait 5 seconds\n");
   delay(5000);

   conf->setup();
   press->setup();
   flow->setup();
   vol->setup();

   sensorTime = millis();
   Serial.print("DEBUG setup done\n");
}

void loop() {

   currTime = millis();

   if ((currTime - sensorTime) > SENSOR_PERIOD_MILLIS ) {

      press->update(currTime);
      flow->update(currTime);
      vol->update(currTime);
      // Generate serial output
      Serial.print("STATUS ");
      Serial.print(currTime);
      relay->sendString();
      press->sendString();
      flow->sendString();
      vol->sendString();
      Serial.print("\n");
      sensorTime = currTime;
   }

   relay->update(currTime);
   conf->update(currTime,relay);

}

