#include <SPI.h>
#include <DW1000Ranging.h>
#include <esp_now.h>
#include <WiFi.h>

#define PIN_RST 9
#define PIN_SS  10
#define PIN_IRQ 22

// BASE STATION MAC ADDRESS
uint8_t BASE_MAC[] = {0x3C,0x8A,0x1F,0x53,0xC4,0x7C};

// range storage
float ranges[3] = {0, 0, 0};
bool updated[3] = {false, false, false};

// index mapping (YOUR VERIFIED ORDER)
#define IDX_ANCHOR_1 0
#define IDX_ANCHOR_2 2
#define IDX_ANCHOR_3 1

void newRange() {
  int idx = DW1000Ranging.getDistantDevice()->getShortAddress() % 3;
  ranges[idx] = DW1000Ranging.getDistantDevice()->getRange();
  updated[idx] = true;

  // if all 3 updated → send
  if (updated[0] && updated[1] && updated[2]) {
    char msg[64];
    snprintf(msg, sizeof(msg),
             "%.3f,%.3f,%.3f",
             ranges[IDX_ANCHOR_1],
             ranges[IDX_ANCHOR_2],
             ranges[IDX_ANCHOR_3]);

    esp_now_send(BASE_MAC, (uint8_t *)msg, strlen(msg) + 1);

    updated[0] = updated[1] = updated[2] = false;
  }
}

void setup() {
  Serial.begin(115200);

  // WiFi + ESP-NOW
  WiFi.mode(WIFI_STA);
  esp_now_init();

  esp_now_peer_info_t peer{};
  memcpy(peer.peer_addr, BASE_MAC, 6);
  peer.channel = 0;
  peer.encrypt = false;
  esp_now_add_peer(&peer);

  // UWB
  SPI.begin(18, 19, 23);
  DW1000Ranging.initCommunication(PIN_RST, PIN_SS, PIN_IRQ);

  DW1000Ranging.attachNewRange(newRange);
  DW1000Ranging.startAsTag("7D:00:22:EA:82:60:3B:9C",
                            DW1000.MODE_LONGDATA_RANGE_LOWPOWER);

  Serial.println("UWB TAG + ESP-NOW started");
}

void loop() {
  DW1000Ranging.loop();
}
