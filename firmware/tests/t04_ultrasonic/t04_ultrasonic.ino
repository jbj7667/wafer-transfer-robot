// t04_ultrasonic — HC-SR04 단독 시험. TRIG=D23, ECHO=D3(INT5). 20Hz, 최근 5회 중앙값, 2초 최소/최대.
// 출력: 중앙값 mm. 0 = 에코 없음/범위 밖.
const uint8_t PIN_TRIG = 23, PIN_ECHO = 3;

volatile uint32_t echoRise = 0;
volatile uint16_t echoUs = 0;
volatile bool echoDone = false;

void echoIsr() {
  if (PINE & _BV(PE5)) {
    echoRise = micros();
  } else {
    uint32_t w = micros() - echoRise;
    echoUs = w > 30000 ? 0 : (uint16_t)w;
    echoDone = true;
  }
}

uint16_t ring[5];
uint8_t ringN = 0, ringCount = 0;
uint16_t winMin = 0xFFFF, winMax = 0;
uint32_t lastTrig = 0, lastWin = 0;

uint16_t median5() {
  uint16_t s[5];
  for (uint8_t i = 0; i < 5; i++) s[i] = ring[i];
  for (uint8_t i = 1; i < 5; i++)
    for (uint8_t j = i; j > 0 && s[j - 1] > s[j]; j--) { uint16_t t = s[j]; s[j] = s[j - 1]; s[j - 1] = t; }
  return s[2];
}

void setup() {
  Serial.begin(115200);
  pinMode(PIN_TRIG, OUTPUT);
  pinMode(PIN_ECHO, INPUT);
  attachInterrupt(digitalPinToInterrupt(PIN_ECHO), echoIsr, CHANGE);
  Serial.println(F("t04_ultrasonic ready (20Hz). 형식: 중앙값 mm (raw us)"));
}

void loop() {
  if (echoDone) {
    noInterrupts();
    uint16_t us = echoUs;
    echoDone = false;
    interrupts();
    uint16_t mm = us ? (uint16_t)(us * 0.1715f) : 0;  // 343 m/s 왕복
    ring[ringN] = mm;
    ringN = (ringN + 1) % 5;
    if (ringCount < 5) ringCount++;
    if (ringCount >= 5) {
      uint16_t m = median5();
      if (m) {
        if (m < winMin) winMin = m;
        if (m > winMax) winMax = m;
      }
      Serial.print(m); Serial.print(F(" mm  (raw "));
      Serial.print(us); Serial.println(F(" us)"));
    }
  }
  if (millis() - lastTrig >= 50) {  // 20Hz
    lastTrig = millis();
    digitalWrite(PIN_TRIG, HIGH);
    delayMicroseconds(10);
    digitalWrite(PIN_TRIG, LOW);
  }
  if (millis() - lastWin >= 2000) {
    lastWin = millis();
    uint16_t mn = winMin == 0xFFFF ? 0 : winMin;
    Serial.print(F("[2s] min=")); Serial.print(mn);
    Serial.print(F(" max=")); Serial.print(winMax);
    Serial.print(F(" span=")); Serial.println(winMax - mn);
    winMin = 0xFFFF; winMax = 0;
  }
}
