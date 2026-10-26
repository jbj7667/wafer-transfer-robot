// comm.h — HM-10 BLE(Serial3) 줄 단위 ASCII 프로토콜과 배터리 전압.
//  로봇 -> 앱: "V,<제어V>,<모터V>\n" (TELEMETRY_MS 주기), "S,<상태이름>\n" (상태 변경 시)
//  앱 -> 로봇: "S" 출발, "H" 재원점(대기 중에만), "P" 핑 -> "K\n"
#pragma once
#include <Arduino.h>

enum class Command : uint8_t { None, Start, Home, Ping };

void commInit();
Command commPoll();               // 수신 명령 1개
void commTelemetry();             // 주기적으로 호출, 내부에서 주기 관리
void commSendState(const char *name);
float vbatCtrl();
float vbatMotor();
