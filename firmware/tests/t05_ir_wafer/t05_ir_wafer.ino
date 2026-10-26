// t05_ir_wafer — GP2Y0A41SK (A0) 웨이퍼 감지 시험. 5회 중앙값(firmware 의 irWaferAdc 와 동일).
// 거리 근사: d[mm] ~ 12343.85 * adc^-1.15 (10비트 ADC, 5V 기준. 제조사 곡선(4~30cm)을 거듭제곱으로 맞춘 널리 쓰는 근사식이며 오차 약 +-10%)
// 데이터시트 유효 범위 40 mm 미만은 출력이 오히려 감소(역전)하므로 무효(<40) 표시한다.
// 명령: e (빈 상태 기준 기록) | w (CD 있는 상태 기준 기록) | c (기록값·임계값 다시 출력)
// 결과: IR_WAFER_ADC_MIN = (empty + wafer) / 2  (firmware: ADC > 임계값이면 CD 있음)
const uint8_t PIN_IR_WAFER = A0;

int16_t emptyAdc = -1, waferAdc = -1;
uint32_t lastPrint = 0;

uint16_t irAdcMedian() {
  uint16_t s[5];
  for (uint8_t i = 0; i < 5; i++) s[i] = analogRead(PIN_IR_WAFER);
  for (uint8_t i = 1; i < 5; i++)
    for (uint8_t j = i; j > 0 && s[j - 1] > s[j]; j--) { uint16_t t = s[j]; s[j] = s[j - 1]; s[j - 1] = t; }
  return s[2];
}

float adcToMm(uint16_t adc) {
  if (adc < 1) return 999.0f;
  return 12343.85f * pow((float)adc, -1.15f);
}

uint16_t avg20() {  // 기준 기록용: 중앙값 20회의 평균
  uint32_t sum = 0;
  for (uint8_t i = 0; i < 20; i++) { sum += irAdcMedian(); delay(10); }
  return (uint16_t)(sum / 20);
}

void printSummary() {
  Serial.print(F("empty=")); Serial.print(emptyAdc);
  Serial.print(F("  wafer=")); Serial.println(waferAdc);
  if (emptyAdc >= 0 && waferAdc >= 0) {
    if (waferAdc <= emptyAdc + 20) {
      Serial.println(F("경고: wafer 값이 empty 보다 충분히 크지 않음 (감지 거리/방향 재확인)"));
    }
    int16_t th = (emptyAdc + waferAdc) / 2;
    Serial.print(F("제안 IR_WAFER_ADC_MIN = ")); Serial.print(th);
    Serial.print(F("  (마진 empty쪽 ")); Serial.print(th - emptyAdc);
    Serial.print(F(", wafer쪽 ")); Serial.print(waferAdc - th); Serial.println(F(")"));
  }
}

void handle(char c) {
  if (c == 'e') { emptyAdc = avg20(); Serial.print(F("empty 기록: ")); Serial.println(emptyAdc); printSummary(); }
  else if (c == 'w') { waferAdc = avg20(); Serial.print(F("wafer 기록: ")); Serial.println(waferAdc); printSummary(); }
  else if (c == 'c') printSummary();
  else Serial.println(F("? e | w | c"));
}

void setup() {
  Serial.begin(115200);
  Serial.println(F("t05_ir_wafer ready. e=빈 상태 기록, w=CD 얹은 상태 기록"));
}

void loop() {
  while (Serial.available()) {
    char ch = Serial.read();
    if (ch != '\n' && ch != '\r' && ch != ' ') handle(ch);
  }
  if (millis() - lastPrint >= 100) {
    lastPrint = millis();
    uint16_t adc = irAdcMedian();
    float mm = adcToMm(adc);
    Serial.print(F("ADC=")); Serial.print(adc);
    Serial.print(F("  ~")); Serial.print(mm, 0); Serial.print(F(" mm"));
    if (mm < 40.0f) Serial.print(F("  [무효: <40mm 구간]"));
    Serial.println();
  }
}
