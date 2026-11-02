// t07_voltage — 전압 분배기 A2(제어팩) / A3(모터팩), 20k/10k (x3). 평균 후 출력, EEPROM 보정, 저전압 경고.
// 명령: c ctrl <멀티미터 V> | c motor <멀티미터 V>  보정계수 = 멀티미터값 / 미보정값 -> EEPROM 저장
//       r  (보정계수 1.000 으로 초기화)
// 결과 보정계수를 config.h 의 VBAT_CAL_CTRL / VBAT_CAL_MOTOR 에 옮겨 적는다.
#include <EEPROM.h>

const uint8_t PIN_VBAT_CTRL = A2, PIN_VBAT_MOTOR = A3;
const float VBAT_SCALE = 5.0f / 1023.0f * 3.0f;
const float VBAT_MOTOR_LOW = 6.6f;  // NiMH 6셀 경고 기준

const int EE_MAGIC = 0;      // 1 byte
const int EE_CTRL = 4;       // float
const int EE_MOTOR = 8;      // float
const uint8_t MAGIC = 0xA7;

float calCtrl = 1.0f, calMotor = 1.0f;
uint32_t lastPrint = 0;

float readAvg(uint8_t pin) {  // 64회 평균 (미보정 전압)
  uint32_t sum = 0;
  for (uint8_t i = 0; i < 64; i++) sum += analogRead(pin);
  return (sum / 64.0f) * VBAT_SCALE;
}

void saveCal() {
  EEPROM.update(EE_MAGIC, MAGIC);
  EEPROM.put(EE_CTRL, calCtrl);
  EEPROM.put(EE_MOTOR, calMotor);
}

void printCal() {
  Serial.print(F("보정계수: ctrl=")); Serial.print(calCtrl, 4);
  Serial.print(F(" motor=")); Serial.println(calMotor, 4);
}

void handle(char *s) {
  if (s[0] == 'r') {
    calCtrl = calMotor = 1.0f; saveCal(); printCal();
  } else if (s[0] == 'c') {
    char name[8];
    float meter = 0;
    if (sscanf(s + 1, "%7s", name) != 1) { Serial.println(F("? c ctrl|motor <V>")); return; }
    char *p = strstr(s, name) + strlen(name);
    meter = atof(p);
    if (meter < 1.0f) { Serial.println(F("멀티미터 값(V)을 입력")); return; }
    if (strcmp(name, "ctrl") == 0) calCtrl = meter / readAvg(PIN_VBAT_CTRL);
    else if (strcmp(name, "motor") == 0) calMotor = meter / readAvg(PIN_VBAT_MOTOR);
    else { Serial.println(F("ctrl 또는 motor")); return; }
    saveCal();
    printCal();
  } else {
    Serial.println(F("? c ctrl <V> | c motor <V> | r"));
  }
}

void setup() {
  Serial.begin(115200);
  if (EEPROM.read(EE_MAGIC) == MAGIC) {
    EEPROM.get(EE_CTRL, calCtrl);
    EEPROM.get(EE_MOTOR, calMotor);
    if (!(calCtrl > 0.5f && calCtrl < 2.0f)) calCtrl = 1.0f;
    if (!(calMotor > 0.5f && calMotor < 2.0f)) calMotor = 1.0f;
  }
  Serial.println(F("t07_voltage ready"));
  printCal();
}

void loop() {
  static char buf[28];
  static uint8_t n = 0;
  while (Serial.available()) {
    char ch = Serial.read();
    if (ch == '\n' || ch == '\r') {
      if (n) { buf[n] = 0; handle(buf); n = 0; }
    } else if (n < sizeof(buf) - 1) {
      buf[n++] = ch;
    }
  }
  if (millis() - lastPrint >= 500) {
    lastPrint = millis();
    float vc = readAvg(PIN_VBAT_CTRL) * calCtrl;
    float vm = readAvg(PIN_VBAT_MOTOR) * calMotor;
    Serial.print(F("ctrl=")); Serial.print(vc, 2);
    Serial.print(F(" V  motor=")); Serial.print(vm, 2); Serial.print(F(" V"));
    if (vm < VBAT_MOTOR_LOW) Serial.print(F("  [경고: 모터 팩 저전압]"));
    Serial.println();
  }
}
