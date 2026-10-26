// t08_led_button — LED(D40=PG1) 4Hz 점멸, 출발 버튼(D19=PD2), 넥 스위치(D25=PA3, config.h 의 PIN_NECK_SW).
// Timer1 CTC 1kHz ISR 에서 125ms 마다 LED 토글, 버튼 30ms 디바운스, 넥 스위치 8ms 디바운스(NECK_DEBOUNCE_MS).
// 오실로스코프 없이 점멸 주기 확인: ISR 이 토글 시각을 micros() 로 기록 -> 한 주기(상승->상승) 평균/최소/최대 출력.
// 목표: 주기 250000 us (오차는 micros() 분해능 4us 와 ISR 지터 안).
const uint8_t PIN_START_BTN = 19, PIN_LED = 40, PIN_NECK_SW = 25;
const uint16_t LED_HALF_PERIOD_MS = 125;
const uint8_t BTN_DEBOUNCE_MS = 30;
const uint8_t NECK_DEBOUNCE_MS = 8;

volatile uint32_t ledRiseUs = 0;     // 마지막 LED 켜짐 시각
volatile bool ledRiseFlag = false;
volatile uint8_t btnCount = 0, neckCount = 0;
volatile bool btnPressed = false, neckDown = false;
volatile uint16_t btnEdges = 0, neckEdges = 0;  // 눌림 에지 수
volatile bool btnEvt = false, neckEvt = false;  // 이벤트(눌림/뗌 변화)
volatile bool btnState = false, neckState = false;

ISR(TIMER1_COMPA_vect) {
  static uint16_t div = 0;
  static bool phase = false;
  if (++div >= LED_HALF_PERIOD_MS) {
    div = 0;
    phase = !phase;
    if (phase) { PORTG |= _BV(PG1); ledRiseUs = micros(); ledRiseFlag = true; }
    else PORTG &= ~_BV(PG1);
  }
  bool rawB = !(PIND & _BV(PD2));
  if (rawB) { if (btnCount < BTN_DEBOUNCE_MS) btnCount++; } else btnCount = 0;
  bool pb = btnCount >= BTN_DEBOUNCE_MS;
  // 뗌 쪽도 같은 방식으로 확정(버튼이 떨어지면 카운트 0 이 되므로 즉시 뗌)
  if (pb != btnPressed) { btnPressed = pb; btnState = pb; btnEvt = true; if (pb) btnEdges++; }

  bool rawN = !(PINA & _BV(PA3));
  if (rawN) { if (neckCount < NECK_DEBOUNCE_MS) neckCount++; } else neckCount = 0;
  bool pn = neckCount >= NECK_DEBOUNCE_MS;
  if (pn != neckDown) { neckDown = pn; neckState = pn; neckEvt = true; if (pn) neckEdges++; }
}

void setup() {
  Serial.begin(115200);
  pinMode(PIN_LED, OUTPUT);
  pinMode(PIN_START_BTN, INPUT_PULLUP);
  pinMode(PIN_NECK_SW, INPUT_PULLUP);
  // Timer1: CTC, 분주 64, OCR1A 249 -> 1kHz
  TCCR1A = 0;
  TCCR1B = _BV(WGM12) | _BV(CS11) | _BV(CS10);
  OCR1A = 249;
  TIMSK1 |= _BV(OCIE1A);
  Serial.println(F("t08_led_button ready. LED 점멸 주기와 버튼/넥 이벤트를 출력"));
}

void loop() {
  static uint32_t prevRise = 0, sum = 0, mn = 0xFFFFFFFFUL, mx = 0;
  static uint16_t cnt = 0;
  if (ledRiseFlag) {
    noInterrupts();
    uint32_t t = ledRiseUs;
    ledRiseFlag = false;
    interrupts();
    if (prevRise) {
      uint32_t p = t - prevRise;
      sum += p; cnt++;
      if (p < mn) mn = p;
      if (p > mx) mx = p;
      if (cnt >= 8) {  // 2초마다 요약
        Serial.print(F("LED 주기 평균=")); Serial.print(sum / cnt);
        Serial.print(F(" us (목표 250000)  min=")); Serial.print(mn);
        Serial.print(F(" max=")); Serial.print(mx);
        Serial.print(F("  지터=")); Serial.print(mx - mn); Serial.print(F(" us  주파수="));
        Serial.print(1e6f * cnt / sum, 4); Serial.println(F(" Hz"));
        sum = 0; cnt = 0; mn = 0xFFFFFFFFUL; mx = 0;
      }
    }
    prevRise = t;
  }
  if (btnEvt) {
    noInterrupts(); bool s = btnState; uint16_t e = btnEdges; btnEvt = false; interrupts();
    Serial.print(F("[START] ")); Serial.print(s ? F("눌림") : F("뗌")); Serial.print(F("  눌림 횟수=")); Serial.println(e);
  }
  if (neckEvt) {
    noInterrupts(); bool s = neckState; uint16_t e = neckEdges; neckEvt = false; interrupts();
    Serial.print(F("[NECK] ")); Serial.print(s ? F("눌림") : F("뗌")); Serial.print(F("  눌림 횟수=")); Serial.println(e);
  }
}
