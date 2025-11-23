# tq_Car_Chevrolet_Corvette_C7R_2019.001

## Complete Scene Structure

```
tq_Car_Chevrolet_Corvette-C7R-2019 (Scene)
├── Animation
│   └── Drivers
│       └── tq_Car_Chevrolet_Corvette-C7R-2019 (Armature Object)
├── Pose
└── tq_Car_Chevrolet_Corvette-C7R-2019 (Armature Data)
    ├── DEF_Body
    │   ├── Door_FL_0
    │   └── Door_FR_0
    ├── DEF_Wheel_FL_0
    ├── DEF_Wheel_FR_0
    ├── DEF_Wheel_BL_0
    ├── DEF_Wheel_BR_0
    ├── DEF_Brake_FL_0
    ├── DEF_Brake_FR_0
    ├── DEF_Brake_BL_0
    ├── DEF_Brake_BR_0
    ├── Root
    │   ├── SHP_Root
    │   └── Drift
    │       ├── GroundSensor_Axle_B
    │       │   ├── SHP_GroundSensor_Axle_B
    │       │   └── MCH_Root_Axle_B
    │       │       ├── SHP_Drift
    │       │       ├── GroundSensor_FL_0
    │       │       │   ├── SHP_GroundSensor_FL_0
    │       │       │   ├── MCH_Wheel_FL_0
    │       │       │   ├── MCH_Brake_FL_0
    │       │       │   │   └── Brake_FL_0
    │       │       │   ├── Wheel_FL_0
    │       │       │   └── Damper_FL_0
    │       │       │       └── MCH_Damper_FL_0
    │       │       ├── GroundSensor_FR_0
    │       │       │   ├── SHP_GroundSensor_FR_0
    │       │       │   ├── MCH_Wheel_FR_0
    │       │       │   ├── MCH_Brake_FR_0
    │       │       │   ├── Wheel_FR_0
    │       │       │   └── Damper_FR_0
    │       │       │       └── MCH_Damper_FR_0
    │       │       ├── GroundSensor_BL_0
    │       │       │   ├── SHP_GroundSensor_BL_0
    │       │       │   ├── MCH_Wheel_BL_0
    │       │       │   ├── MCH_Brake_BL_0
    │       │       │   │   └── Brake_BL_0
    │       │       │   ├── Wheel_BL_0
    │       │       │   └── Damper_BL_0
    │       │       │       └── MCH_Damper_BL_0
    │       │       ├── GroundSensor_BR_0
    │       │       │   ├── SHP_GroundSensor_BR_0
    │       │       │   ├── MCH_Wheel_BR_0
    │       │       │   ├── MCH_Brake_BR_0
    │       │       │   │   └── Brake_BR_0
    │       │       │   ├── Wheel_BR_0
    │       │       │   └── Damper_BR_0
    │       │       │       └── MCH_Damper_BR_0
    │       │       ├── MCH_Axis_F
    │       │       ├── MCH_Axis_B
    │       │       ├── MCH_Suspension_B
    │       │       └── MCH_Suspension_F
    │       │           └── MCH_Axis
    │       │               ├── MCH_Body
    │       │               └── Suspension
    │       └── GroundSensor_Axle_F
    │           ├── SHP_GroundSensor_Axle_F
    │           ├── MCH_Root_Axle_F
    │           └── MCH_Steering
    ├── MCH_WheelRotation_FL_0
    ├── MCH_WheelRotation_FR_0
    ├── MCH_WheelRotation_BL_0
    ├── MCH_WheelRotation_BR_0
    ├── MCH_SteeringRotation
    │   └── Steering
    └── Bone Collections
        ├── Layer 1
        ├── Layer 2
        ├── Layer 3
        ├── Layer 4
        ├── Layer 5
        ├── Layer 14
        ├── Layer 15
        ├── Layer 16
        ├── Layer 32
        ├── Direction
        ├── Suspension
        ├── Wheel
        ├── GroundSensor
        └── DoorTrunk
```

---

## Constraints System

### Deformation Bones (DEF_)

#### DEF_Body
- **Copy Transforms** - Copies transforms from MCH_Body

#### Door_FL_0 and Door_FR_0
- **Limit Rotation** - Restricts rotation range for door opening/closing

### Wheel and Brake Bones

#### DEF_Wheel_* (All wheels: FL_0, FR_0, BL_0, BR_0)
- **Copy Transforms** - Copies transforms from corresponding MCH_Wheel

#### DEF_Brake_* (All brakes: FL_0, FR_0, BL_0, BR_0)
- **Copy Transforms** - Copies transforms from corresponding MCH_Brake

### Control Mechanism Bones (MCH_)

#### MCH_Root_Axle_B (Back Axle Root)
- **Track Front Axle** - Constraint tracking MCH_Root_Axle_F orientation and position

#### GroundSensor_Axle_B
- **Ground Projection** - Projects sensor to ground/terrain level

#### GroundSensor_Axle_F (Front Axle Sensor)
- **Ground Projection** - Projects sensor to ground/terrain level
- **Limit Distance** - Limits maximum distance from Root bone

#### MCH_Steering (Steering Control)
- **Track Steering Bone** - Tracks steering input bone
- **Drift Counter Animation** - Applies counter-rotation to prevent unwanted drift

#### MCH_Axis_F (Front Axle Mechanism)
- **Copy Location** - Copies location from DEF_Wheel_FR_0 (right front wheel)
- **Track Left Wheel** - Tracks DEF_Wheel_FL_0 (left front wheel) orientation

#### MCH_Axis_B (Back Axle Mechanism)
- **Copy Location** - Copies location from DEF_Wheel_BR_0 (right back wheel)
- **Track Left Wheel** - Tracks DEF_Wheel_BL_0 (left back wheel) orientation

#### MCH_Suspension_B (Back Suspension)
- **Location from MCH_Axis_B** - Copies location from back axle mechanism

#### MCH_Suspension_F (Front Suspension)
- **Location from MCH_Axis_F** - Copies location from front axle mechanism
- **Track suspension back** - Tracks MCH_Suspension_B for coordinated suspension movement

#### MCH_Axis (Central Axis)
- **Rotation from MCH_Axis_F** - Copies rotation from front axle mechanism
- **Rotation from MCH_Axis_B** - Copies rotation from back axle mechanism

#### MCH_Body (Body Control)
- **Suspension on rollover** - Applies suspension influence on vehicle roll
- **Suspension on vertical** - Applies suspension influence on vertical movement

#### Suspension (Active Suspension Bone)
- **Limit Location** - Restricts suspension travel range

### Ground Sensor Constraints

#### GroundSensor_FL_0 and GroundSensor_FR_0 (Front Sensors)

**Constraints:**
- **Steering rotation** - Applies steering angle influence
- **Ground projection** - Projects to ground surface
- **Ground projection limitation** - Limits projection distance

**MCH_Wheel_FL_0 and MCH_Wheel_FR_0 (Front Wheel Controls):**
- **Brake animation wheels** - Drives brake deformation
- **Wheel rotation along Y axis** - Rotates wheel based on movement
- **Animation wheels** - Applies custom animation properties

#### GroundSensor_BL_0 and GroundSensor_BR_0 (Back Sensors)

**Constraints:**
- **Ground projection** - Projects to ground surface
- **Ground projection limitation** - Limits projection distance

**MCH_Wheel_BL_0 and MCH_Wheel_BR_0 (Back Wheel Controls):**
- **Brake animation wheels** - Drives brake deformation
- **Wheel rotation along Y axis** - Rotates wheel based on movement
- **Animation wheels** - Applies custom animation properties

### Wheel Rotation Bones (MCH_WheelRotation_*)

#### MCH_WheelRotation_FL_0, MCH_WheelRotation_FR_0, MCH_WheelRotation_BL_0, MCH_WheelRotation_BR_0
- **Child of:** MCH_Root_Axle_B (back axle root)
- Driven by custom properties for wheel rotation animation

### Steering Rotation Bone (MCH_SteeringRotation)

#### MCH_SteeringRotation
- **Copy Rotation** - Copies rotation from MCH_Axis_B (back axle rotation)
- **Child of:** No parent (top-level)
- Provides independent steering angle control

### Brake Control Bone (Brake_FL_0)

#### Brake_FL_0
- **Constraints:**
  - **Brakes** - Limit scale constraint (X: 1.0, Y: 0.5-1.0, Z: 0.5-1.0)
  - Controls brake pad compression and visual deformation

