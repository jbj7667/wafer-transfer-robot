# contaxt\공지사항\07. 9월 15일 창의과제 안전교육 및 앱프로그래밍 교육 안내\첨부 자료\HM-10_TEST.zip

## ZIP 목록
- Arduino_HM10_Setup/ (0 B)
- Arduino_HM10_Setup/Arduino_HM10_Setup.ino (1309 B)
```
// HM-10을 설정할 때 한 번만 실행하는 프로그램
#define PC_BAUD_RATE    115200
#define HM10_BAUD_RATE  9600

#define HM10_NAME       "HM10_TEST"     // Device Name
#define HM10_PASSWORD   "123456"        // Password

void sendATCommand(const char *command) {
  Serial.print("전송: ");
  Serial.println(command);

  Serial3.print(command);
  delay(500);

  Serial.print("응답: ");
  while (Serial3.available() > 0) {
    Serial.write(Serial3.read());
  }

  Serial.println();
}

void setup() {
  Serial.begin(PC_BAUD_RATE);
  Serial3.begin(HM10_BAUD_RATE);

  delay(1000);

  // HM-10 통신 확인
  sendATCommand("AT");

  // BLE 장치 이름 설정
  Serial3.print("AT+NAME");
  sendATCommand(HM10_NAME);

  // 6자리 비밀번호 설정
  Serial3.print("AT+PASS");
  sendATCommand(HM10_PASSWORD);

  // 연결할 때 비밀번호를 확인하도록 설정
  sendATCommand("AT+TYPE3");

  // 설정 적용을 위해 HM-10 재시작
  sendATCommand("AT+RESET");
}

void loop() {
  // PC에서 받은 데이터를 HM-10으로 전송
  while (Serial.available() > 0) {
    Serial3.write(Serial.read());
  }

  // HM-10에서 받은 데이터를 PC로 전송
  while (Serial3.available() > 0) {
    Serial.write(Serial3.read());
  }
}
```
- Arduino_HM10_Test/ (0 B)
- Arduino_HM10_Test/Arduino_HM10_Test.ino (354 B)
```
// HM-10 테스트 프로그램
#define PC_BAUD_RATE    115200
#define HM10_BAUD_RATE  9600

void setup() {
  Serial.begin(PC_BAUD_RATE);
  Serial3.begin(HM10_BAUD_RATE);
}

void loop() {
  while (Serial.available() > 0) {
    Serial3.write(Serial.read());
  }

  while (Serial3.available() > 0) {
    Serial.write(Serial3.read());
  }
}
```
- HM10_Test.aia (206492 B)
- 읽어보세요.txt (212 B)
```
[Arduino_HM10_Setup] HM-10의 장치 이름과 암호를 설정하는 Arduino 프로그램

[Arduino_HM10_Setup] Arduino용 HM-10 테스트 프로그램

[HM10_Test.aia] App Inventor 용 프로젝트 파일

```
