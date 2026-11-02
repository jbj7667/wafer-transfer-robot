# Requirements Summary

My own summary of the contest constraints that drive the design. Dimensions in mm.

## Field (own half, 1000 × 1000)

```
 y=130  [5]o---| stop |--------+--------| stop |---o[6]   post 175   centers 740 apart
 y=305     [3]o--|     |-------+-------|     |--o[4]      post 200   centers 640 apart
 y=480        [1]o-|    |------+------|    |-o[2]         post 200   centers 540 apart
                               |  trunk x=500
                             .-'  R100
 y=870  |---------------------'   start/finish bar at x=130 (19 x 100)
```

- Lines 19 wide. Each row ends in a 100-long stop bar, 100 from the post center.
- Post: lower cylinder Ø100 × 100, upper cylinder Ø50, total height 200 (rows 2–3) or 175 (top row). Flat top, not fixed to the floor.
- Wafer: Ø120 × 1.2 CD lying on the Ø50 top, overhanging 35 on every side.
- Both posts in a row have the same height.

## Runs

| | Qualifying | Tournament |
|---|---|---|
| Time | 120 s | 150 s |
| Wafer start | left posts (1, 3, 5) | one random side per row |
| Goal | move each wafer to the post opposite in its row, return, stop covering the start bar | same; first to finish wins |
| Score | wafers moved, +1 if all done in time | wafers moved |

Wafer positions may not be entered by a human (no app input, DIP switch or jumper) — the robot must sense them.

## Robot

- Fits in 250 × 250 × 250 at start; may unfold afterwards.
- Drive: the two issued DC gear motors. Actuators: at most 3 in total from Tamiya gearbox motors, steppers and RC servos.
- Controller: issued Arduino Mega 2560 + IO shield. Sensors: issued only — one 3-channel digital line sensor, up to 3 IR distance (Sharp GP2Y0A41SK), up to 3 ultrasonic (HC-SR04). Switches are free.
- Power: two separate 6 × AA packs (logic / motors), each with its own power switch.
- Fully autonomous after start. Team number and name visible on the robot.
- Self-funded parts ≤ 120,000 KRW with receipts.

## Bonus features (1 point each)

1. Start from a smartphone over the issued BLE module (custom app — a generic terminal app does not count).
2. Start with a push button on the robot.
3. Show battery voltage on the smartphone (custom app).
4. Self-initialize at power-on using a sensor (e.g. limit-switch homing). Merely moving an RC servo does not count.
5. Exterior LED off while moving, blinking 4 times per second in the start and finish areas.
