#include <SPI.h>
#include <WiFi.h>
#include <esp_now.h>
#include <DW1000Ranging.h>

/* ---------- PIN CONFIG FOR HUZZAH32 ---------- */
#define PIN_RST 32  // Pin 36 is INPUT ONLY, 32 is OUTPUT capable
#define PIN_SS  15  // Standard SPI CS
#define PIN_IRQ 21 

uint8_t baseStationMAC[] = {0xE4,0xB0,0x63,0xAE,0xED,0x80};
char tagAddress[] = "7D:00:22:EA:82:60:3B:9C";

const int MAX_ANCHORS = 3;
uint16_t seenAnchors[MAX_ANCHORS] = {0};
float ranges[MAX_ANCHORS] = {0};
bool updated[MAX_ANCHORS] = {false};

void newRange();
void newDevice(DW1000Device* d);
void inactiveDevice(DW1000Device* d);

// CORRECTED CALLBACK FOR CORE 3.3.6
void onSent(const wifi_tx_info_t *tx_info, esp_now_send_status_t status) {
  Serial.print("ESP-NOW Status: ");
  Serial.println(status == ESP_NOW_SEND_SUCCESS ? "Success" : "Fail");
}

void setup() {
  Serial.begin(115200);
  delay(1000);
  
  WiFi.mode(WIFI_STA);
  if (esp_now_init() != ESP_OK) {
    Serial.println("ESP-NOW init failed");
    return;
  }
  esp_now_register_send_cb(onSent);

  esp_now_peer_info_t peer = {};
  memcpy(peer.peer_addr, baseStationMAC, 6);
  peer.channel = 0;
  peer.encrypt = false;
  if (esp_now_add_peer(&peer) != ESP_OK) {
    Serial.println("Failed to add peer");
    return;
  }

  SPI.begin();
  DW1000Ranging.initCommunication(PIN_RST, PIN_SS, PIN_IRQ);
  DW1000Ranging.attachNewRange(newRange);
  DW1000Ranging.attachNewDevice(newDevice);
  DW1000Ranging.attachInactiveDevice(inactiveDevice);

  DW1000Ranging.startAsTag(tagAddress, DW1000.MODE_LONGDATA_RANGE_LOWPOWER);
  Serial.println("System Online");
}

void loop() {
  DW1000Ranging.loop();
}

void newRange() {
  DW1000Device* dev = DW1000Ranging.getDistantDevice();
  if (!dev) return;

  float dist = dev->getRange();
  uint16_t addr = dev->getShortAddress();
  if (dist <= 0.0 || dist > 30.0) return;

  int index = -1;
  for (int i = 0; i < MAX_ANCHORS; i++) {
    if (seenAnchors[i] == addr) { index = i; break; }
  }
  if (index == -1) {
    for (int i = 0; i < MAX_ANCHORS; i++) {
      if (seenAnchors[i] == 0) { seenAnchors[i] = addr; index = i; break; }
    }
  }

  if (index != -1) {
    ranges[index] = dist;
    updated[index] = true;

    bool allUpdated = true;
    for (int i = 0; i < MAX_ANCHORS; i++) {
      if (!updated[i]) { allUpdated = false; break; }
    }

    if (allUpdated) {
      char csv[64];
      snprintf(csv, sizeof(csv), "%.3f,%.3f,%.3f\n", ranges[0], ranges[1], ranges[2]);
      esp_now_send(baseStationMAC, (uint8_t*)csv, strlen(csv));
      for (int i = 0; i < MAX_ANCHORS; i++) updated[i] = false;
    }
  }
}

void newDevice(DW1000Device* dev) { Serial.println("Anchor Found"); }
void inactiveDevice(DW1000Device* dev) { Serial.println("Anchor Lost"); }
