#include <SPI.h>
#include "DW1000Ranging.h"

#define PIN_RST  27
#define PIN_IRQ  4
#define PIN_SS   5

float lastDistance = 0;
unsigned long lastTime = 0;

void setup() {
  delay(1500);
  Serial.begin(115200);
  delay(1000);

  DW1000Ranging.initCommunication(PIN_RST, PIN_SS, PIN_IRQ);

  DW1000Ranging.attachNewRange(newRange);
  DW1000Ranging.attachNewDevice(newDevice);
  DW1000Ranging.attachInactiveDevice(inactiveDevice);

  DW1000Ranging.useRangeFilter(true);

  DW1000Ranging.startAsTag(
    "7D:00:22:EA:82:60:3B:9C",
    DW1000.MODE_LONGDATA_RANGE_ACCURACY
  );
}

void loop() {
  DW1000Ranging.loop();
}

void newRange() {
  float d = DW1000Ranging.getDistantDevice()->getRange();
  unsigned long t = millis();

  float velocity = 0;
  if (lastTime > 0) {
    float dt = (t - lastTime) / 1000.0;
    velocity = (d - lastDistance) / dt;
  }

  lastDistance = d;
  lastTime = t;

  Serial.print("Distance: ");
  Serial.print(d);
  Serial.print(" m  | Velocity: ");
  Serial.print(velocity);
  Serial.println(" m/s");
}

void newDevice(DW1000Device* device) {
  Serial.print("Connected to anchor: ");
  Serial.println(device->getShortAddress(), HEX);
}

void inactiveDevice(DW1000Device* device) {
  Serial.print("Lost anchor");
}
