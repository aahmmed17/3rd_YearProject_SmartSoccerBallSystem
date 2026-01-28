#include <SPI.h>
#include <DW1000Ranging.h>
#include <math.h>
#include <WiFi.h>
#include <esp_now.h>


#define PIN_RST 2
#define PIN_SS  7
#define PIN_IRQ 3

char tagAddress[] = "7D:00:22:EA:82:60:3B:9C"; //unique tag address
uint8_t anchorMAC[] = {0x3C, 0x8A, 0x1F, 0x55, 0x25, 0xCC};


//Anchor coordinates (in meters) arbitrary values for now
float ax[3] = {0.0, 3.0, 0.0};
float ay[3] = {0.0,  0.0, 3.6};

//Distances
float dist[3] = {0, 0, 0};

bool gotRange[3] = {false, false, false};

void setup() {
  
  Serial.begin(115200);

  WiFi.mode(WIFI_STA);
  WiFi.disconnect();

  if (esp_now_init() != ESP_OK) {
    Serial.println("ESP-NOW init failed");
    return;
  
  }
  esp_now_peer_info_t peerInfo = {};
  memcpy(peerInfo.peer_addr, anchorMAC, 6);
  peerInfo.channel = 0;
  peerInfo.encrypt = false;

  if (esp_now_add_peer(&peerInfo) != ESP_OK) {
    Serial.println("Failed to add peer");
    return;
  }

  // your DW1000 init continues here
  Serial.begin(115200);
  delay(1000);

  SPI.begin(4, 5, 6);
  DW1000Ranging.initCommunication(PIN_RST, PIN_SS, PIN_IRQ); //initialise dw1000

  DW1000Ranging.attachNewRange(newRange);

  DW1000Ranging.startAsTag(tagAddress, DW1000.MODE_LONGDATA_RANGE_LOWPOWER);
}

  

void loop() {
  DW1000Ranging.loop();

  if (gotRange[0] && gotRange[1] && gotRange[2]) { //only calculates position if all 3 distances are ready
    calculatePosition();
    gotRange[0] = gotRange[1] = gotRange[2] = false;
  }
}

void newRange() { //called when an anchor reports a distance
  DW1000Device *dev = DW1000Ranging.getDistantDevice();
  uint16_t addr = dev->getShortAddress();
  float d = dev->getRange();

  if (addr == 0x01) { dist[0] = d; gotRange[0] = true; } //Store distance based on which anchor replied
  if (addr == 0x02) { dist[1] = d; gotRange[1] = true; }
  if (addr == 0x03) { dist[2] = d; gotRange[2] = true; }
}

void calculatePosition() { //trilateration math to calculate coordinates
  float x1 = ax[0], y1 = ay[0], r1 = dist[0];
  float x2 = ax[1], y2 = ay[1], r2 = dist[1];
  float x3 = ax[2], y3 = ay[2], r3 = dist[2];

  float A = 2*(x2 - x1); //Linearised equations (assumes 2d only)
  float B = 2*(y2 - y1);
  float C = r1*r1 - r2*r2 - x1*x1 + x2*x2 - y1*y1 + y2*y2;

  float D = 2*(x3 - x1);
  float E = 2*(y3 - y1);
  float F = r1*r1 - r3*r3 - x1*x1 + x3*x3 - y1*y1 + y3*y3;

  float denom = (A*E - B*D);
  if (fabs(denom) < 0.01) return; 

  float x = (C*E - B*F) / denom; //solve for x and y 
  float y = (A*F - C*D) / denom;

PositionPacket pkt;
pkt.x = x;
pkt.y = y;

esp_now_send(anchorMAC, (uint8_t *)&pkt, sizeof(pkt));


  Serial.print("Ball position: X="); //prints coordinates of ball position
  Serial.print(x, 2);
  Serial.print(" m  Y=");
  Serial.print(y, 2);
  Serial.println(" m");
}
