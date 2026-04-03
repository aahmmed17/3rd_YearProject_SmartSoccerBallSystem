#include <SPI.h>
#include <DW1000Ranging.h>

#define PIN_RST 27
#define PIN_SS  5
#define PIN_IRQ 34

char anchorAddress[] = "82:17:5B:D5:A9:9A:E2:03"; 

void setup() {
  Serial.begin(115200);
  delay(1000);

  SPI.begin(18, 19, 23);
  DW1000Ranging.initCommunication(PIN_RST, PIN_SS, PIN_IRQ);

  DW1000.useSmartPower(true);
  DW1000.setAntennaDelay(16580); //16600 for short lowp, //16620 for long lowp FAST //16580 for range lowp

  DW1000Ranging.startAsAnchor(
    anchorAddress,
    DW1000.MODE_LONGDATA_RANGE_LOWPOWER,
    0xE203   
  );


  Serial.println("UWB ANCHOR started");
}

void loop() {
  DW1000Ranging.loop();
}