// 로봇 BLE 프로토콜 에뮬레이터 (앱 시험용) - Arduino Mega 2560 + HM-10 (Serial3, 9600bps)
// 로봇 -> 앱 : "V,<제어V>,<모터V>\n" 500ms 주기, "S,<STATE>\n" 상태 변경 시
// 앱 -> 로봇 : "S" 출발, "H" 재홈(IDLE일 때만), "P" 핑(응답 "K")
// 시험 전용 명령: "L" 저전압 모드 토글(전압 임계값 빨강 표시 확인), "F" FAULT 토글
// 실제 로봇 펌웨어에는 L/F 명령이 없다. USB 시리얼 모니터(115200)에도 로그가 나온다.

#include <Arduino.h>

static const unsigned long BAUD_BLE = 9600UL;
static const unsigned long V_PERIOD_MS = 500UL;
static const unsigned long RUN_MS = 10000UL;
static const unsigned long HOMING_MS = 2000UL;
static const unsigned long BOOT_MS = 1500UL;
static const unsigned long ARRIVED_MS = 5000UL;  // 반복 시험 편의: 5초 후 자동 IDLE

enum State : uint8_t { ST_BOOT, ST_HOMING, ST_IDLE, ST_RUN, ST_ARRIVED, ST_FAULT };

static const char *const STATE_NAME[] = {"BOOT", "HOMING", "IDLE", "RUN", "ARRIVED", "FAULT"};

static State state = ST_BOOT;
static unsigned long stateSince = 0;
static unsigned long lastV = 0;
static bool lowVolt = false;

static void sendLine(const char *s) {
  Serial3.print(s);
  Serial3.print('\n');
  Serial.print(F("TX "));
  Serial.println(s);
}

static void setState(State s) {
  state = s;
  stateSince = millis();
  char buf[16];
  snprintf(buf, sizeof(buf), "S,%s", STATE_NAME[s]);
  sendLine(buf);
}

// 밀리볼트 정수를 "x.xx" 문자열로 (부동소수 printf 회피)
static void fmtVolt(char *out, size_t n, long mv) {
  snprintf(out, n, "%ld.%02ld", mv / 1000L, (mv % 1000L) / 10L);
}

static void sendVoltage() {
  const unsigned long t = millis();
  // 제어 팩 9.0 V 부근, 모터 팩 7.4 V 부근에서 완만히 변동(RUN 중에는 sag)
  long ctrlMv = 8950L + (long)((t / 400UL) % 11UL) * 10L;
  long motorMv = 7360L + (long)((t / 300UL) % 9UL) * 10L;
  if (state == ST_RUN) motorMv -= 350L;
  if (lowVolt) {
    ctrlMv = 7300L + (long)((t / 400UL) % 5UL) * 10L;
    motorMv = 6500L + (long)((t / 300UL) % 5UL) * 10L;
  }
  char c[12], m[12], buf[32];
  fmtVolt(c, sizeof(c), ctrlMv);
  fmtVolt(m, sizeof(m), motorMv);
  snprintf(buf, sizeof(buf), "V,%s,%s", c, m);
  sendLine(buf);
}

static void handleCommand(char c) {
  Serial.print(F("RX "));
  Serial.println(c);
  switch (c) {
    case 'P':
      sendLine("K");
      break;
    case 'S':
      if (state == ST_IDLE) setState(ST_RUN);
      break;
    case 'H':
      if (state == ST_IDLE) setState(ST_HOMING);
      break;
    case 'L':
      lowVolt = !lowVolt;
      break;
    case 'F':
      setState(state == ST_FAULT ? ST_IDLE : ST_FAULT);
      break;
    default:
      break;  // 알 수 없는 문자(개행 포함)는 무시
  }
}

void setup() {
  Serial.begin(115200);
  Serial3.begin(BAUD_BLE);
  Serial.println(F("test_echo: robot protocol emulator"));
  setState(ST_BOOT);
}

void loop() {
  // 명령은 한 글자이므로 개행 유무와 관계없이 글자 단위로 처리한다.
  while (Serial3.available() > 0) {
    handleCommand((char)Serial3.read());
  }

  const unsigned long now = millis();
  if (now - lastV >= V_PERIOD_MS) {
    lastV = now;
    sendVoltage();
  }

  switch (state) {
    case ST_BOOT:
      if (now - stateSince >= BOOT_MS) setState(ST_HOMING);
      break;
    case ST_HOMING:
      if (now - stateSince >= HOMING_MS) setState(ST_IDLE);
      break;
    case ST_RUN:
      if (now - stateSince >= RUN_MS) setState(ST_ARRIVED);
      break;
    case ST_ARRIVED:
      if (now - stateSince >= ARRIVED_MS) setState(ST_IDLE);
      break;
    default:
      break;
  }
}
