#include <SPI.h>
#include "DW1000Ranging.h"

// ESP32-safe example pins — change if needed
#define PIN_RST  27
#define PIN_IRQ  4
#define PIN_SS   5

void setup() {
  delay(1500);
  Serial.begin(115200);
  delay(1000);

  DW1000Ranging.initCommunication(PIN_RST, PIN_SS, PIN_IRQ);

  DW1000Ranging.attachNewRange(newRange);
  DW1000Ranging.attachBlinkDevice(newBlink);
  DW1000Ranging.attachInactiveDevice(inactiveDevice);

  DW1000Ranging.startAsAnchor(
    "82:17:5B:D5:A9:9A:E2:9C",
    DW1000.MODE_LONGDATA_RANGE_ACCURACY
  );
}

void loop() {
  DW1000Ranging.loop();
}

void newRange() {
  Serial.print("TAG ");
  Serial.print(DW1000Ranging.getDistantDevice()->getShortAddress(), HEX);
  Serial.print(" -> ");
  Serial.print(DW1000Ranging.getDistantDevice()->getRange());
  Serial.println(" m");
}

void newBlink(DW1000Device* device) {
  Serial.print("New device: ");
  Serial.println(device->getShortAddress(), HEX);
}

void inactiveDevice(DW1000Device* device) {
  Serial.print("Inactive device: ");
  Serial.println(device->getShortAddress(), HEX);
}
