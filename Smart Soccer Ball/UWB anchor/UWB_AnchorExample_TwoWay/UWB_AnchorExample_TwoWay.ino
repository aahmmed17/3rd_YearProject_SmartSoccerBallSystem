/**
 * 
 * @todo
 *  - move strings to flash (less RAM consumption)
 *  - fix deprecated convertation form string to char* startAsAnchor
 *  - give example description
 */
#include <SPI.h>
#include "DW1000Ranging.h"

// connection pins
#define PIN_RST = 27; // reset pin
#define PIN_IRQ = 26; // irq pin
#define PIN_SS = 5; // spi select pin

void setup() {
  Serial.begin(115200);
  delay(1000);
  //init the configuration
  DW1000Ranging.initCommunication(PIN_RST, PIN_SS, PIN_IRQ); //Reset, CS, IRQ pin
  //define the sketch as anchor. It will be great to dynamically change the type of module
  DW1000Ranging.attachNewRange(newRange);
  DW1000Ranging.attachBlinkDevice(newBlink);
  DW1000Ranging.attachInactiveDevice(inactiveDevice);
  //Enable the filter to smooth the distance
  DW1000Ranging.useRangeFilter(true);
  
  //we start the module as an anchor
  DW1000Ranging.startAsAnchor("82:17:5B:D5:A9:9A:E2:9C", DW1000.MODE_LONGDATA_RANGE_ACCURACY);
}

void loop() {
  DW1000Ranging.loop();
}


void newRange() {
  float d = DW1000Ranging.getDistantDevice()->getRange();
  unsigned long now = millis();

  float speed = 0.0;
  if (lastTime > 0) {
    float dt = (now - lastTime) / 1000.0; // seconds
    if (dt > 0) {
      speed = (d - lastDistance) / dt;
    }
  }

  lastDistance = d;
  lastTime = now;

  Serial.print("Tag distance: ");
  Serial.print(d);
  Serial.print(" m | Speed: ");
  Serial.print(speed);
  Serial.println(" m/s");
}




void newBlink(DW1000Device* device) {
  Serial.print("blink; 1 device added ! -> ");
  Serial.print(" short:");
  Serial.println(device->getShortAddress(), HEX);
}

void inactiveDevice(DW1000Device* device) {
  Serial.print("delete inactive device: ");
  Serial.println(device->getShortAddress(), HEX);
}

