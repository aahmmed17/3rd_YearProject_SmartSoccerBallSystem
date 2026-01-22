#include <DW1000.h>

// SPI pins
#define PIN_SS   5
#define PIN_RST  17
#define PIN_IRQ  16

void setup() {
  Serial.begin(115200);

  // Initialize SPI
  SPI.begin(18, 19, 23);  

  // Initialize DW1000
  DW1000.begin(PIN_IRQ, PIN_RST);
  DW1000.select(PIN_SS);

  Serial.println("Init DW1000...");
  DW1000.newConfiguration();
  DW1000.setDefaults();
  DW1000.commitConfiguration();
  Serial.println("Ready!");
}

void loop() {
}
