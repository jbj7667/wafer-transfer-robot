#include "comm.h"
#include "config.h"

#define BLE Serial3

static char rx[16];
static uint8_t rxLen = 0;
static uint32_t lastTx = 0;

void commInit() {
  BLE.begin(9600);
  Serial.begin(115200);  // USB 디버그
}

float vbatCtrl() { return analogRead(PIN_VBAT_CTRL) * VBAT_SCALE * VBAT_CAL_CTRL; }
float vbatMotor() { return analogRead(PIN_VBAT_MOTOR) * VBAT_SCALE * VBAT_CAL_MOTOR; }

static Command parse(const char *s) {
  if (s[0] == 'S' && s[1] == 0) return Command::Start;
  if (s[0] == 'H' && s[1] == 0) return Command::Home;
  if (s[0] == 'P' && s[1] == 0) return Command::Ping;
  return Command::None;
}

Command commPoll() {
  while (BLE.available()) {
    char c = BLE.read();
    if (c == '\r') continue;
    if (c == '\n') {
      rx[rxLen] = 0;
      rxLen = 0;
      Command cmd = parse(rx);
      if (cmd == Command::Ping) BLE.print("K\n");
      if (cmd != Command::None) return cmd;
    } else if (rxLen < sizeof(rx) - 1) {
      rx[rxLen++] = c;
    } else {
      rxLen = 0;  // 너무 긴 줄은 버린다
    }
  }
  return Command::None;
}

void commTelemetry() {
  if (millis() - lastTx < TELEMETRY_MS) return;
  lastTx = millis();
  float vc = vbatCtrl(), vm = vbatMotor();
  BLE.print("V,");
  BLE.print(vc, 2);
  BLE.print(',');
  BLE.print(vm, 2);
  BLE.print('\n');
  Serial.print("V ");
  Serial.print(vc, 2);
  Serial.print(' ');
  Serial.println(vm, 2);
}

void commSendState(const char *name) {
  BLE.print("S,");
  BLE.print(name);
  BLE.print('\n');
  Serial.print("STATE ");
  Serial.println(name);
}

void commSendTest(const char *item, const char *result) {
  BLE.print("T,");
  BLE.print(item);
  BLE.print(',');
  BLE.print(result);
  BLE.print('\n');
  Serial.print("TEST ");
  Serial.print(item);
  Serial.print(' ');
  Serial.println(result);
}
