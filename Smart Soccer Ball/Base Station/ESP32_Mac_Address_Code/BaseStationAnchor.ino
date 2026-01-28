#include <SPI.h>
#include <DW1000Ranging.h>
#include <WiFi.h>
#include <esp_now.h>

// ================= ESP-NOW =================
typedef struct {
  float x;
  float y;
} PositionPacket;

// This is the correct callback for ESP32 Arduino 2.x cores
void onReceive(const esp_now_recv_info *info, const uint8_t *data, int len) {
  if (len == sizeof(PositionPacket)) {
    PositionPacket pkt;
    memcpy(&pkt, data, sizeof(pkt));

    // Print coordinates
    Serial.print("TAG POSITION → X=");
    Serial.print(pkt.x, 2);
    Serial.print(" m  Y=");
    Serial.print(pkt.y, 2);
    Serial.println(" m");

    // Print sender MAC address
    Serial.print("Received from MAC: ");
    for (int i = 0; i < 6; i++) {
      if (i) Serial.print(":");
      Serial.print(info->src_addr[i], HEX);
    }
    Serial.println();
  }
}


// ================= DW1000 =================

// Set this anchor as the base station (example: ID 3)
#define ANCHOR_ID 3  

#if ANCHOR_ID == 1
  char anchorAddress[] = "82:17:5B:D5:A9:9A:E2:01";
#elif ANCHOR_ID == 2
  char anchorAddress[] = "82:17:5B:D5:A9:9A:E2:02";
#elif ANCHOR_ID == 3
  char anchorAddress[] = "82:17:5B:D5:A9:9A:E2:03";
#endif

// FireBeetle ESP32 DW1000 pins
#define PIN_RST  27
#define PIN_SS   5
#define PIN_IRQ  4

void setup() {
  Serial.begin(115200);
  delay(1000);

  // ---------- ESP-NOW ----------
  WiFi.mode(WIFI_STA);
  WiFi.disconnect();

  Serial.print("BASE STATION MAC: ");
  Serial.println(WiFi.macAddress());

  if (esp_now_init() != ESP_OK) {
    Serial.println("ESP-NOW init failed");
    return;
  }
  esp_now_register_recv_cb(onReceive);

  // ---------- DW1000 ----------
  SPI.begin(18, 19, 23);       // SCK, MISO, MOSI
  SPI.setFrequency(8000000);   // safe for DW1000

  DW1000Ranging.initCommunication(PIN_RST, PIN_SS, PIN_IRQ);
  DW1000Ranging.attachNewRange(newRange);
  DW1000Ranging.attachInactiveDevice(inactiveDevice);

  DW1000Ranging.startAsAnchor(
    anchorAddress,
    DW1000.MODE_LONGDATA_RANGE_LOWPOWER
  );

  Serial.println("Base Station Anchor Ready");
}

void loop() {
  DW1000Ranging.loop();
}

// Called whenever a new range is measured
void newRange() {
  Serial.print("Range from ");
  Serial.print(DW1000Ranging.getDistantDevice()->getShortAddress(), HEX);
  Serial.print(": ");
  Serial.print(DW1000Ranging.getDistantDevice()->getRange());
  Serial.println(" m");
}

// Called when a tag stops responding
void inactiveDevice(DW1000Device *device) {
  Serial.println("Device inactive");
}

