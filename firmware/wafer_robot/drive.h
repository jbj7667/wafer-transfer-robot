// drive.h — L298 차동 구동. PWM은 Timer5 Fast PWM 8bit(약 7.8kHz), 듀티는 OCR5C(좌)/OCR5B(우).
#pragma once
#include <Arduino.h>

void driveInit();
// -255..255, 양수 = 전진. ISR과 loop 양쪽에서 호출하므로 내부는 레지스터 쓰기만 한다.
void driveSet(int16_t left, int16_t right);
inline void driveStop() { driveSet(0, 0); }  // 프리런 정지
// 능동 제동: IN 둘 다 HIGH + PWM 255 를 BRAKE_MS 유지. loop에서 driveBrakeUpdate()를 불러야 끝난다.
// 이후 driveSet()이 호출되면 제동은 즉시 해제된다.
void driveBrake();
void driveBrakeUpdate();
