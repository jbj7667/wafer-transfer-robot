// sense.h — Timer1 1kHz 제어 틱과 센서.
//  틱마다: 라인센서 샘플·이벤트 판정, 출발 버튼 디바운스, LED 4Hz 패턴, 승강 가감속,
//          FOLLOW 모드일 때 5ms마다 PD 라인추종 출력
#pragma once
#include <Arduino.h>

// 라인 비트: bit2=L, bit1=C, bit0=R, 1 = 흑(선 위)
uint8_t lineBits();
// 3채널 모두 흑이 EVENT_MIN_MS 이상 지속된 뒤 래치. lineEventTake()가 읽고 지운다.
bool lineEventTake();
void lineEventClear();
// 3채널 모두 백이 지속된 시간(ms)
uint16_t lineLostMs();

enum class DriveMode : uint8_t { Manual, Follow };
void followStart(uint8_t baseSpeed);  // PD 라인추종 시작(Follow 모드)
void followSpeed(uint8_t baseSpeed);  // Follow 중 기본 속도만 변경(D항 유지)
void manualDrive(int16_t left, int16_t right);  // Follow 해제 후 고정 출력
void manualBrake();                             // Follow 해제 후 능동 제동(drive.h)
bool neckPressed();                             // 넥 접촉 스위치(디바운스 후 눌림)

bool startButtonTake();               // 눌림 엣지 1회
enum class LedMode : uint8_t { Off, Blink4Hz, On };
void ledSet(LedMode m);

void senseInit();
uint32_t ticks();                     // 1ms 틱 카운터

// 초음파: loop에서 sonarUpdate()를 계속 부르면 50ms마다 측정. 무효 = 0
void sonarUpdate();
uint16_t sonarMm();
uint16_t irWaferAdc();                // 5회 중앙값
