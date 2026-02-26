#include <SPI.h>
#include "DW1000Ranging.h"

#define PIN_RST  32
#define PIN_IRQ  21
#define PIN_SS   15

void setup() {
  delay(1500);
  Serial.begin(115200);
  delay(1000);

  // Initialize UWB hardware
  DW1000Ranging.initCommunication(PIN_RST, PIN_SS, PIN_IRQ);

  // Attach callback functions
  DW1000Ranging.attachNewRange(newRange);
  DW1000Ranging.attachNewDevice(newDevice);
  DW1000Ranging.attachInactiveDevice(inactiveDevice);

  // Enable noise filtering
  DW1000Ranging.useRangeFilter(true);

  // Start as a tag
  DW1000Ranging.startAsTag(
    "7D:00:22:EA:82:60:3B:9C",
    DW1000.MODE_LONGDATA_RANGE_ACCURACY
  );
}

void loop() {
  DW1000Ranging.loop();
}

void newRange() {
  // Get distance from the current device
  float d = DW1000Ranging.getDistantDevice()->getRange();

  Serial.print("Distance: ");
  Serial.print(d);
  Serial.println(" m");
}

void newDevice(DW1000Device* device) {
  Serial.print("Connected to anchor: ");
  Serial.println(device->getShortAddress(), HEX);
}

void inactiveDevice(DW1000Device* device) {
  Serial.println("Lost anchor");
}