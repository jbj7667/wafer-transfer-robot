// comm.h — HM-10 BLE(Serial3) 줄 단위 ASCII 프로토콜과 배터리 전압.
//  로봇 -> 앱: "V,<제어V>,<모터V>\n" (TELEMETRY_MS 주기), "S,<상태이름>\n" (상태 변경 시),
//              "T,<IR|LINE|VBAT>,<OK|WARN|FAIL>\n" (SELFTEST 중 항목별 1회)
//  앱 -> 로봇: "S" 출발, "H" 재원점(대기 중에만), "P" 핑 -> "K\n"
#pragma once
#include <Arduino.h>

enum class Command : uint8_t { None, Start, Home, Ping };

void commInit();
Command commPoll();               // 수신 명령 1개
void commTelemetry();             // 주기적으로 호출, 내부에서 주기 관리
void commSendState(const char *name);
void commSendTest(const char *item, const char *result);  // 자가 점검 결과 한 줄 "T,<항목>,<결과>"
float vbatCtrl();
float vbatMotor();
