// t01_motor_pwm — L298 좌/우 모터 단독 시험 (Arduino Mega 2560)
// 명령: l <-255..255> | r <-255..255> | b(단락 제동 40ms 후 프리런) | s(정지)
// 핀·레지스터 방식은 wafer_robot/drive.cpp 와 동일 (Timer5 Fast PWM 7.8kHz, D30..D33 = PC7..PC4).

const uint8_t PIN_ENA = 44, PIN_ENB = 45;
const uint8_t PIN_IN1 = 30, PIN_IN2 = 31, PIN_IN3 = 32, PIN_IN4 = 33;
const uint16_t BRAKE_MS = 40;
const uint16_t RAMP_STEP_MS = 5;  // 램프: 5ms마다 PWM 1 단계(0->255 약 1.3초)

#define IN1_BIT _BV(PC7)
#define IN2_BIT _BV(PC6)
#define IN3_BIT _BV(PC5)
#define IN4_BIT _BV(PC4)

int16_t curL = 0, curR = 0;  // 현재 출력
int16_t tgtL = 0, tgtR = 0;  // 목표 (램프로 접근)
bool braking = false;
uint32_t brakeT0 = 0, rampT0 = 0;

uint8_t absDuty(int16_t v) {
  if (v < 0) v = -v;
  return v > 255 ? 255 : (uint8_t)v;
}

void driveSet(int16_t left, int16_t right) {
  uint8_t sreg = SREG;
  cli();
  uint8_t c = PORTC & ~(IN1_BIT | IN2_BIT | IN3_BIT | IN4_BIT);
  if (left > 0) c |= IN1_BIT; else if (left < 0) c |= IN2_BIT;
  if (right > 0) c |= IN3_BIT; else if (right < 0) c |= IN4_BIT;
  PORTC = c;
  OCR5C = absDuty(left);
  OCR5B = absDuty(right);
  SREG = sreg;
}

void driveBrake() {
  uint8_t sreg = SREG;
  cli();
  PORTC |= IN1_BIT | IN2_BIT | IN3_BIT | IN4_BIT;
  OCR5C = 255;
  OCR5B = 255;
  SREG = sreg;
  braking = true;
  brakeT0 = millis();
  curL = curR = tgtL = tgtR = 0;
}

int16_t stepToward(int16_t cur, int16_t tgt) {
  if (cur < tgt) return cur + 1;
  if (cur > tgt) return cur - 1;
  return cur;
}

// 방향이 바뀌면 0을 거쳐 가므로 자연스럽게 램프가 걸린다.
void rampUpdate() {
  if (braking) {
    if (millis() - brakeT0 >= BRAKE_MS) {
      braking = false;
      driveSet(0, 0);
      Serial.println(F("brake end -> free"));
    }
    return;
  }
  if (millis() - rampT0 < RAMP_STEP_MS) return;
  rampT0 = millis();
  if (curL == tgtL && curR == tgtR) return;
  curL = stepToward(curL, tgtL);
  curR = stepToward(curR, tgtR);
  driveSet(curL, curR);
}

void handle(char *line) {
  char cmd = line[0];
  long v = atol(line + 1);
  v = constrain(v, -255L, 255L);
  if (cmd == 'l') {
    braking = false; tgtL = (int16_t)v;
    Serial.print(F("left  -> ")); Serial.println(v);
  } else if (cmd == 'r') {
    braking = false; tgtR = (int16_t)v;
    Serial.print(F("right -> ")); Serial.println(v);
  } else if (cmd == 'b') {
    driveBrake();
    Serial.println(F("brake (IN all HIGH, PWM 255, 40ms)"));
  } else if (cmd == 's') {
    braking = false; tgtL = tgtR = curL = curR = 0;
    driveSet(0, 0);
    Serial.println(F("stop (free)"));
  } else {
    Serial.println(F("? l <n> | r <n> | b | s"));
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(PIN_ENA, OUTPUT); pinMode(PIN_ENB, OUTPUT);
  pinMode(PIN_IN1, OUTPUT); pinMode(PIN_IN2, OUTPUT);
  pinMode(PIN_IN3, OUTPUT); pinMode(PIN_IN4, OUTPUT);
  // Timer5: Fast PWM 8bit, 비반전 B/C, 분주 8
  TCCR5A = _BV(COM5B1) | _BV(COM5C1) | _BV(WGM50);
  TCCR5B = _BV(WGM52) | _BV(CS51);
  OCR5B = 0; OCR5C = 0;
  Serial.println(F("t01_motor_pwm ready. 바퀴를 띄운 상태에서 시험할 것."));
}

void loop() {
  static char buf[24];
  static uint8_t n = 0;
  while (Serial.available()) {
    char ch = Serial.read();
    if (ch == '\n' || ch == '\r') {
      if (n) { buf[n] = 0; handle(buf); n = 0; }
    } else if (n < sizeof(buf) - 1) {
      buf[n++] = ch;
    }
  }
  rampUpdate();
}
