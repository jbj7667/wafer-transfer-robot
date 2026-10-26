// lift.h — 승강 스테퍼(DRV8834).
//  Timer3 CTC ISR: 스텝 펄스 1개 출력 + 위치 카운트 + 리밋 스위치 감시
//  liftTick1ms(): Timer1 1kHz 틱에서 호출, 사다리꼴 가감속으로 스텝 주기(OCR3A) 갱신
//  liftUpdate(): loop에서 호출, 원점 잡기 단계 진행
#pragma once
#include <Arduino.h>

void liftInit();
void liftStartHoming();          // 전원 On 자체 초기화(추가기능 4)
void liftMoveToMm(float mm);     // 원점 잡기 완료 후에만 동작
bool liftBusy();                 // 이동 또는 원점 잡기 중
bool liftHomed();
bool liftFault();                // 원점 미검출, 상단 리밋 충돌
float liftPosMm();
void liftUpdate();
void liftTick1ms();
