#include <SPI.h>
#include <DW1000Ranging.h>

#define PIN_RST 9
#define PIN_SS  10
#define PIN_IRQ 2

char tagAddress[] = "7D:00:22:EA:82:60:3B:9C";

void newRange() {
  DW1000Device* device = DW1000Ranging.getDistantDevice();
  if (!device) return;

  Serial.print("RANGE from 0x");
  Serial.print(device->getShortAddress(), HEX);
  Serial.print(" -> ");
  Serial.print(device->getRange());
  Serial.println(" m");
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  SPI.begin(13, 12, 11);

  DW1000Ranging.initCommunication(PIN_RST, PIN_SS, PIN_IRQ);
  DW1000Ranging.attachNewRange(newRange);

  DW1000Ranging.startAsTag(
    tagAddress,
    DW1000.MODE_LONGDATA_RANGE_LOWPOWER
  );

  Serial.println("TAG started");
}

void loop() {
  DW1000Ranging.loop();
}

