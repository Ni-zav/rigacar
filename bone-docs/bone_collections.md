Damper_ : Layer 32
SHP_Root : Layer 14, Direction
DEF_Body : Layer 16
DEF_Wheel_ and DEF_Brake_ : Layer 16
Root : Layer 1, Direction
MCH_WheelRotation_ : Layer 32
MCH_SteeringRotation : Layer 32
Steering : Layer 3, Layer 14, Wheel
Door_ and Trunk_ : Layer 5, DoorTrunk
Drift : Layer 1, Direction
GroundSensor_Axle_F : Layer 4, GroundSensor
SHP_GroundSensor_Axle_F : Layer 14, GroundSensor
MCH_Root_Axle_F : Layer 32
MCH_Steering : Layer 15, Layer 32
GroundSensor_Axle_B : Layer 4, GroundSensor
SHP_GroundSensor_Axle_B : Layer 14, GroundSensor
MCH_Root_Axle_B : Layer 32
SHP_Drift : Layer 14, Direction
GroundSensor_FL_0, GroundSensor_FR_0, GroundSensor_BL_0, GroundSensor_BR_0 : Layer 4, GroundSensor
MCH_Axis_F, MCH_Axis_B : Layer 32
MCH_Suspension_B, MCH_Suspension_F : Layer 32
MCH_Axis : Layer 32
MCH_Body : Layer 15, Layer 32
Suspension : Layer 2, Layer 14, Suspension

SHP_GroundSensor_ : Layer 14, GroundSensor
MCH_Wheel_ : Layer 15, Layer 32
MCH_Brake_ : Layer 15, Layer 32
Wheel_ : Layer 3, Layer 14, Wheel
Damper_ : Layer 1, Layer 14
MCH_Damper_ : Layer 32
Brake_ : Layer 3, Layer 4, Wheel

**Grouped By Layer**

- **Layer 1:** Root (Direction); Drift (Direction); Damper_ (also appears on Layer 14 in the list).
- **Layer 2:** Suspension (also listed on Layer 14).
- **Layer 3:** Steering (also Layer 14, Wheel); Wheel_ (also Layer 14, Wheel); Brake_ (also Layer 4, Wheel).
- **Layer 4:** GroundSensor_Axle_F; GroundSensor_Axle_B; GroundSensor_FL_0; GroundSensor_FR_0; GroundSensor_BL_0; GroundSensor_BR_0 — all GroundSensor entries. (Also: Brake_ appears partly on Layer 4.)
- **Layer 5:** Door_; Trunk_ (DoorTrunk).
- **Layer 14:** SHP_Root (Direction); SHP_GroundSensor_* (GroundSensor); SHP_Drift (Direction); Steering (also Layer 3); Wheel_ (also Layer 3); Damper_ (also listed on Layer 1); Suspension (also Layer 2).
- **Layer 15:** MCH_Steering; MCH_Body; MCH_Wheel_; MCH_Brake_ (these also commonly appear on Layer 32).
- **Layer 16:** DEF_Body; DEF_Wheel_; DEF_Brake_.
- **Layer 32:** Damper_ (also appears elsewhere); MCH_WheelRotation_; MCH_SteeringRotation; MCH_Root_Axle_F; MCH_Root_Axle_B; MCH_Axis_F; MCH_Axis_B; MCH_Suspension_B; MCH_Suspension_F; MCH_Axis; MCH_Body (also Layer 15); MCH_Steering (also Layer 15); MCH_Wheel_; MCH_Brake_; MCH_Damper_.

Note: The original per-bone listing above is preserved. This appended section groups the same entries by layer to make it easier to see which bones/collections appear on each layer. Some names appear on multiple layers; where useful that cross-reference is noted.