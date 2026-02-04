#include <SPI.h>
#include <DW1000Ranging.h>

/* ---------- PIN CONFIG ---------- */
#define PIN_RST 9
#define PIN_SS  10
#define PIN_IRQ 2

/* ---------- TAG ADDRESS ---------- */
char tagAddress[] = "7D:00:22:EA:82:60:3B:9C";

/* ---------- STORAGE ---------- */
const int MAX_ANCHORS = 3;
uint16_t seenAnchors[MAX_ANCHORS] = {0};
float ranges[MAX_ANCHORS] = {0};
bool updated[MAX_ANCHORS] = {false};

/* ---------- CALLBACK ---------- */
void newRange() {
  DW1000Device* d = DW1000Ranging.getDistantDevice();
  if (!d) return;

  uint16_t addr = d->getShortAddress();
  float dist = d->getRange();

  // ignore bad readings
  if (dist <= 0.0 || dist > 30.0) return;

  int index = -1;

  // check if we have seen this anchor before
  for (int i = 0; i < MAX_ANCHORS; i++) {
    if (seenAnchors[i] == addr) {
      index = i;
      break;
    }
  }

  // if new anchor, add to list
  if (index == -1) {
    for (int i = 0; i < MAX_ANCHORS; i++) {
      if (seenAnchors[i] == 0) {
        seenAnchors[i] = addr;
        index = i;
        break;
      }
    }
  }

  // if more than MAX_ANCHORS, ignore extra anchors
  if (index == -1) return;

  ranges[index] = dist;
  updated[index] = true;

  // print batch only when all 3 updated
  bool allUpdated = true;
  for (int i = 0; i < MAX_ANCHORS; i++) {
    if (!updated[i]) {
      allUpdated = false;
      break;
    }
  }

  if (allUpdated) {
    for (int i = 0; i < MAX_ANCHORS; i++) {
      Serial.print(ranges[i], 3);
      if (i < MAX_ANCHORS - 1) Serial.print(", ");
    }
    Serial.println();

    // reset flags for next batch
    for (int i = 0; i < MAX_ANCHORS; i++) updated[i] = false;
  }
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

  Serial.println("UWB TAG started");
}

void loop() {
  DW1000Ranging.loop();
}


