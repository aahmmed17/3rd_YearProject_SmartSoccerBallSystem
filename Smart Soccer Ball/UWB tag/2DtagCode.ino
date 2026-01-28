#include <SPI.h>
#include <DW1000Ranging.h>
#include <WiFi.h>
#include <esp_now.h>
#include <math.h>

/* ================= ESP-NOW ================= */

typedef struct {
  float x;
  float y;
} PositionPacket;

// Base station WiFi MAC (CONFIRMED)
uint8_t baseStationMAC[] = {0x3C, 0x8A, 0x1F, 0x55, 0x25, 0xCC};

/* ================= DW1000 ================= */

// ESP32-C3 SAFE PIN CONFIG
#define PIN_RST  2
#define PIN_SS   10
#define PIN_IRQ  3

// SPI pins (ESP32-C3 SuperMini)
#define PIN_SCK  4
#define PIN_MISO 5
#define PIN_MOSI 6

// SHORT address tag
char tagAddress[] = "7D:00";

// Anchor positions (meters)
float ax[3] = {0.0, 3.0, 0.0};
float ay[3] = {0.0, 0.0, 3.6};

// Ranges
float dist[3] = {0, 0, 0};
bool gotRange[3] = {false, false, false};

/* ================= SETUP ================= */

void setup() {
  Serial.begin(115200);
  delay(500);

  /* ---- ESP-NOW ---- */
  WiFi.mode(WIFI_STA);
  WiFi.disconnect();

  if (esp_now_init() != ESP_OK) {
    Serial.println("ESP-NOW init failed");
    return;
  }

  esp_now_peer_info_t peerInfo = {};
  memcpy(peerInfo.peer_addr, baseStationMAC, 6);
  peerInfo.channel = 0;
  peerInfo.encrypt = false;

  if (esp_now_add_peer(&peerInfo) != ESP_OK) {
    Serial.println("Failed to add ESP-NOW peer");
    return;
  }

  Serial.println("ESP-NOW ready");

  /* ---- DW1000 ---- */
  SPI.begin(PIN_SCK, PIN_MISO, PIN_MOSI);

  DW1000Ranging.initCommunication(PIN_RST, PIN_SS, PIN_IRQ);

  
  DW1000Ranging.attachNewRange(newRange);

  DW1000Ranging.startAsTag(
    tagAddress,
    DW1000.MODE_LONGDATA_RANGE_LOWPOWER
  );

  Serial.println("UWB Tag started");
}

/* ================= LOOP ================= */

void loop() {
  DW1000Ranging.loop();

  if (gotRange[0] && gotRange[1] && gotRange[2]) {
    calculatePosition();
    gotRange[0] = gotRange[1] = gotRange[2] = false;
  }
}

/* ================= CALLBACKS ================= */

void newRange() {
  DW1000Device *dev = DW1000Ranging.getDistantDevice();
  uint16_t addr = dev->getShortAddress();
  float d = dev->getRange();

  if (addr == 0x01) { dist[0] = d; gotRange[0] = true; }
  else if (addr == 0x02) { dist[1] = d; gotRange[1] = true; }
  else if (addr == 0x03) { dist[2] = d; gotRange[2] = true; }
}

/* ================= TRILATERATION ================= */

void calculatePosition() {
  float x1 = ax[0], y1 = ay[0], r1 = dist[0];
  float x2 = ax[1], y2 = ay[1], r2 = dist[1];
  float x3 = ax[2], y3 = ay[2], r3 = dist[2];

  float A = 2 * (x2 - x1);
  float B = 2 * (y2 - y1);
  float C = r1*r1 - r2*r2 - x1*x1 + x2*x2 - y1*y1 + y2*y2;

  float D = 2 * (x3 - x1);
  float E = 2 * (y3 - y1);
  float F = r1*r1 - r3*r3 - x1*x1 + x3*x3 - y1*y1 + y3*y3;

  float denom = (A * E - B * D);
  if (fabs(denom) < 0.01) return;

  float x = (C * E - B * F) / denom;
  float y = (A * F - C * D) / denom;

  PositionPacket pkt;
  pkt.x = x;
  pkt.y = y;

  esp_now_send(baseStationMAC, (uint8_t *)&pkt, sizeof(pkt));

  Serial.print("Ball position → X=");
  Serial.print(x, 2);
  Serial.print(" m  Y=");
  Serial.print(y, 2);
  Serial.println(" m");
}
