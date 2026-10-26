# Wafer Transfer Robot

Autonomous line-following robot that transfers three 120 mm wafers (CDs) between pedestal bases, built solo for the 2026 Dongyang Robot Contest (wafer-transfer category, Dongyang Mirae University, Dept. of Robot Automation).

> 동양미래대학교 로봇자동화공학부 2026 창의과제 · 동양로봇경진대회(웨이퍼 이송로봇 부문) 1인 출전 프로젝트

## Challenge in one paragraph

On a 1 m × 1 m field marked with 19 mm black lines, the robot leaves a start box, follows a central trunk line to three side rows, picks a wafer resting on top of a Ø50 mm post (175 mm or 200 mm tall) and places it on the post at the opposite end of the same row, three times, then returns and stops in the start box. Qualifying runs have a 120 s limit with known wafer positions; tournament runs last 150 s and the wafer side in each row is randomized, so the robot must detect it by itself. The robot must fit in a 250 mm cube at the start and may use two drive DC motors plus at most three actuator motors, an Arduino Mega 2560 and the issued sensors only.

## Approach

| Area | Design |
|---|---|
| Mechanism | Differential drive + front U-fork on a single vertical lift axis (selected from a 100-idea design review, see `docs/arena/`) |
| Fabrication | All structural parts 3D printed (Bambu Lab A1), M3 heat-set inserts |
| Control | Arduino Mega 2560, timer interrupts for control tick / stepper pulses / drive PWM, event-counting state machine for navigation |
| Sensing | 3-channel digital line sensor, ultrasonic approach distance, IR wafer-presence check, limit-switch homing |
| App | MIT App Inventor BLE app: start button and live battery voltage |

## Repository layout

| Path | Contents |
|---|---|
| `docs/` | Design documents: requirements summary, mechanism selection, state machine, wiring, review |
| `cad/` | Fusion 360 models and printable STL/STEP exports |
| `firmware/` | Arduino sketch (Mega 2560) |
| `app/` | App Inventor project |

## Status

Work in progress — contest on 2026-11-24.

## License

MIT (see `LICENSE`). Third-party part models in `cad/vendor/` keep their original licenses.
