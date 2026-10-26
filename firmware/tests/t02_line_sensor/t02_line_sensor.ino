// t02_line_sensor — 라인센서 L/C/R 단독 시험. D22/D24/D26 = PA0/PA2/PA4, 흑 = LOW.
// 20Hz 막대 출력, 초당 전환 횟수, 5초 흑 비율 측정(m), 좌/우 에지 시간차 -> 진입각 추정.
// 명령: m (5초 흑 비율 샘플링) | v <mm/s> (속도 입력) | d <mm> (L-R 채널 간격, 기본 25) | e (에지 통계 초기화)
// 진입각 theta = atan( v*dt / 간격 ). dt = tR - tL (L이 먼저 흑이면 +). +면 선이 오른쪽으로 기울어 L이 먼저 닿음.
// 주의: 막대 출력은 샘플링 중(m)에는 멈춘다.
#include <math.h>

const uint8_t PIN_LINE_L = 22, PIN_LINE_C = 24, PIN_LINE_R = 26;

float spacingMm = 25.0f;  // 좌/우 채널 간격 [측정: 센서 PCB 실측]
float speedMmS = 100.0f;  // 사용자 입력 속도

uint8_t readBits() {  // bit2=L, bit1=C, bit0=R, 1 = 흑
  uint8_t pa = PINA;
  return (!(pa & _BV(PA0)) << 2) | (!(pa & _BV(PA2)) << 1) | (!(pa & _BV(PA4)));
}

uint8_t prevBits = 0;
uint16_t transCount = 0;     // 1초당 전환 수
uint32_t lastBar = 0, lastSec = 0;

// 에지 시간차 상태: [0]=흑 진입 에지, [1]=백 복귀 에지
uint32_t tL[2] = {0, 0}, tR[2] = {0, 0};
bool hasL[2] = {false, false}, hasR[2] = {false, false};
const uint32_t STALE_US = 200000UL;

// 샘플링
bool sampling = false;
uint32_t sampT0 = 0, sampN = 0, sampBlack[3] = {0, 0, 0};  // [0]=L,[1]=C,[2]=R

void reportEdge(uint8_t k) {
  // 부호 있는 dt (us). L이 먼저 = 양수
  int32_t dt = (int32_t)(tR[k] - tL[k]);
  float theta = atan2(speedMmS * (dt * 1e-6f), spacingMm) * 57.29578f;
  Serial.print(k == 0 ? F("[edge 흑진입] ") : F("[edge 백복귀] "));
  Serial.print(F("dt=")); Serial.print(dt); Serial.print(F(" us  각도=")); Serial.print(theta, 1);
  Serial.print(F(" deg (v=")); Serial.print(speedMmS, 0); Serial.print(F(" mm/s, 간격=")); Serial.print(spacingMm, 1);
  Serial.println(F(" mm)"));
  hasL[k] = hasR[k] = false;
}

void edgeEvent(bool isL, uint8_t k, uint32_t t) {
  // 오래된 짝 폐기
  if (hasL[k] && t - tL[k] > STALE_US) hasL[k] = false;
  if (hasR[k] && t - tR[k] > STALE_US) hasR[k] = false;
  if (isL) { tL[k] = t; hasL[k] = true; } else { tR[k] = t; hasR[k] = true; }
  if (hasL[k] && hasR[k]) reportEdge(k);
}

void handle(char *line) {
  char c = line[0];
  float v = atof(line + 1);
  if (c == 'm') {
    sampling = true; sampT0 = millis(); sampN = 0;
    sampBlack[0] = sampBlack[1] = sampBlack[2] = 0;
    Serial.println(F("5초 샘플링 시작: 센서를 측정 위치에 고정하고 유지"));
  } else if (c == 'v' && v > 0) {
    speedMmS = v; Serial.print(F("speed = ")); Serial.println(speedMmS);
  } else if (c == 'd' && v > 0) {
    spacingMm = v; Serial.print(F("spacing = ")); Serial.println(spacingMm);
  } else if (c == 'e') {
    hasL[0] = hasL[1] = hasR[0] = hasR[1] = false;
    Serial.println(F("edge reset"));
  } else {
    Serial.println(F("? m | v <mm/s> | d <mm> | e"));
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(PIN_LINE_L, INPUT);
  pinMode(PIN_LINE_C, INPUT);
  pinMode(PIN_LINE_R, INPUT);
  prevBits = readBits();
  Serial.println(F("t02_line_sensor ready. 막대: #=흑 .=백  (L C R)"));
}

void loop() {
  static char buf[20];
  static uint8_t n = 0;
  while (Serial.available()) {
    char ch = Serial.read();
    if (ch == '\n' || ch == '\r') {
      if (n) { buf[n] = 0; handle(buf); n = 0; }
    } else if (n < sizeof(buf) - 1) {
      buf[n++] = ch;
    }
  }

  uint32_t t = micros();
  uint8_t b = readBits();
  uint8_t diff = b ^ prevBits;
  if (diff) {
    transCount++;
    // L(bit2)·R(bit0) 에지만 시간차에 사용
    if (diff & 0b100) edgeEvent(true, (b & 0b100) ? 0 : 1, t);
    if (diff & 0b001) edgeEvent(false, (b & 0b001) ? 0 : 1, t);
    prevBits = b;
  }

  if (sampling) {
    sampN++;
    if (b & 0b100) sampBlack[0]++;
    if (b & 0b010) sampBlack[1]++;
    if (b & 0b001) sampBlack[2]++;
    if (millis() - sampT0 >= 5000) {
      sampling = false;
      Serial.print(F("흑 비율(5s, 샘플 ")); Serial.print(sampN); Serial.print(F("): L="));
      Serial.print(100.0f * sampBlack[0] / sampN, 1); Serial.print(F("% C="));
      Serial.print(100.0f * sampBlack[1] / sampN, 1); Serial.print(F("% R="));
      Serial.print(100.0f * sampBlack[2] / sampN, 1); Serial.println('%');
      Serial.println(F("백 위: 0%에 가깝게, 흑 위: 100%에 가깝게. 중간값이면 높이/기울기/전원 조정."));
    }
    return;
  }

  if (millis() - lastSec >= 1000) {
    lastSec = millis();
    Serial.print(F("transitions/s = ")); Serial.println(transCount);
    transCount = 0;
  }
  if (millis() - lastBar >= 50 && Serial.availableForWrite() > 30) {  // 20Hz
    lastBar = millis();
    Serial.print(F("L[")); Serial.print((b & 0b100) ? '#' : '.');
    Serial.print(F("] C[")); Serial.print((b & 0b010) ? '#' : '.');
    Serial.print(F("] R[")); Serial.print((b & 0b001) ? '#' : '.');
    Serial.print(F("]  "));
    Serial.print((b & 0b100) ? F("####") : F("....")); Serial.print((b & 0b010) ? F("####") : F("...."));
    Serial.println((b & 0b001) ? F("####") : F("...."));
  }
}
