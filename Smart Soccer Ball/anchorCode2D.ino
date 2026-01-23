#include <SPI.h>
#include <DW1000Ranging.h>

// anchor ID 1 , change this to 2 and 3 for the other anchors
#define ANCHOR_ID 1   

//Each anchor must have a unique address
#if ANCHOR_ID == 1
  char anchorAddress[] = "82:17:5B:D5:A9:9A:E2:01";
#elif ANCHOR_ID == 2
  char anchorAddress[] = "82:17:5B:D5:A9:9A:E2:02";
#elif ANCHOR_ID == 3
  char anchorAddress[] = "82:17:5B:D5:A9:9A:E2:03";
#endif
//DW1000 wiring to ESP32
#define PIN_RST 27    
#define PIN_SS  5     
#define PIN_IRQ 34  

void setup() {
  Serial.begin(115200);
  delay(1000);

  SPI.begin(18, 19, 23);
  //Initialise DW1000 communication
  DW1000Ranging.initCommunication(PIN_RST, PIN_SS, PIN_IRQ);
  //Called when a new distance is measured
  DW1000Ranging.attachNewRange(newRange);
  //Called when a tag goes out of range
  DW1000Ranging.attachInactiveDevice(inactiveDevice);
  DW1000Ranging.startAsAnchor(
    anchorAddress,
    DW1000.MODE_LONGDATA_RANGE_LOWPOWER
  );
}

void loop() {
  DW1000Ranging.loop();
}
//Runs every time a tag range is calculated
void newRange() {
  Serial.print("Range from ");
  Serial.print(
    DW1000Ranging.getDistantDevice()->getShortAddress(), HEX
  );
  Serial.print(": ");
  Serial.print(
    DW1000Ranging.getDistantDevice()->getRange()
  );
  Serial.println(" m");
}
//Runs when a tag stops responding
void inactiveDevice(DW1000Device *device) {
  Serial.println("Device inactive");
}
