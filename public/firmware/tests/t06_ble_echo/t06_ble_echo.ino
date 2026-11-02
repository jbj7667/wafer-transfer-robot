// t06_ble_echo — HM-10 AT 명령 도우미. Serial3(TX3=D14 -> HM-10 RXD(분압 1k/2k), RX3=D15 <- HM-10 TXD), 9600.
// USB 시리얼 모니터(115200, 줄 끝 "없음" 또는 "CR+LF" 모두 가능) <-> HM-10 양방향 브리지.
// 로봇 프로토콜 에뮬레이터는 public/app/test_echo 를 쓴다. 여기서는 AT 설정과 연결 확인용.
// AT 명령 예: AT / AT+NAME? / AT+NAMEwafer / AT+BAUD? / AT+ADDR? / AT+VERS?
//   HM-10 은 AT 명령에 줄 끝이 없어야 하므로 입력의 CR/LF 를 제거하고 전송한다.
// 특수 명령:
//   !v x y   -> Serial3 으로 "V,x,y\n" 전송 (로봇 프로토콜 전송 시험)
const uint32_t BLE_BAUD = 9600;

char line[48];
uint8_t n = 0;

void setup() {
  Serial.begin(115200);
  Serial3.begin(BLE_BAUD);
  Serial.println(F("t06_ble_echo ready. 입력=HM-10 으로 전송, 수신=화면 표시. 예: AT -> OK"));
}

void sendLine() {
  line[n] = 0;
  if (line[0] == '!' && line[1] == 'v') {
    // !v x y -> V,x,y
    int x = 0, y = 0;
    if (sscanf(line + 2, "%d %d", &x, &y) == 2) {
      Serial3.print(F("V,")); Serial3.print(x); Serial3.print(','); Serial3.println(y);
      Serial.print(F("sent: V,")); Serial.print(x); Serial.print(','); Serial.println(y);
    } else {
      Serial.println(F("사용법: !v <x> <y>"));
    }
  } else {
    Serial3.print(line);  // AT 는 줄 끝 없이 전송해야 한다
    Serial.print(F("sent: ")); Serial.println(line);
  }
  n = 0;
}

void loop() {
  while (Serial.available()) {
    char ch = Serial.read();
    if (ch == '\n' || ch == '\r') {
      if (n) sendLine();
    } else if (n < sizeof(line) - 1) {
      line[n++] = ch;
    }
  }
  while (Serial3.available()) Serial.write(Serial3.read());
}
