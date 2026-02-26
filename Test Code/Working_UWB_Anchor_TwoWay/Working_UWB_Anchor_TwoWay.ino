#include <SPI.h>
#include "DW1000Ranging.h"

#define PIN_RST  27
#define PIN_IRQ  34
#define PIN_SS   5

char anchorAddr[] = "82:17:5B:D5:A9:9A:E2:9C";

void setup() {
  delay(2000);
  Serial.begin(115200);

  DW1000Ranging.initCommunication(PIN_RST, PIN_SS, PIN_IRQ);

  DW1000.useSmartPower(true);
  DW1000.setAntennaDelay(16550);


  DW1000Ranging.attachNewRange(newRange);
  DW1000Ranging.attachBlinkDevice(newBlink);
  DW1000Ranging.attachInactiveDevice(inactiveDevice);

  DW1000Ranging.startAsAnchor(
    anchorAddr,
    DW1000.MODE_LONGDATA_RANGE_ACCURACY
  );
}

void loop() {
  DW1000Ranging.loop();
}

void newRange() {
  static unsigned long lastPrint = 0;
  if (millis() - lastPrint < 250) return;

  Serial.print("TAG ");
  Serial.print(DW1000Ranging.getDistantDevice()->getShortAddress(), HEX);
  Serial.print(" -> ");
  Serial.print(DW1000Ranging.getDistantDevice()->getRange(), 2);
  Serial.println(" m");
}

void newBlink(DW1000Device* device) {
  Serial.println("New tag detected");
}

void inactiveDevice(DW1000Device* device) {
  Serial.println("Tag inactive");
}
