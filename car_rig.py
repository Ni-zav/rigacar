# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 3
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

# <pep8 compliant>

import bpy
import math
import bpy_extras
import mathutils
import re
from math import inf
from rna_prop_ui import rna_idprop_ui_create

# Bone Collection Layers - Visible Layers
LAYER_1 = 'Layer 1'  # Main control bones (visible)
LAYER_2 = 'Layer 2'  # Suspension visualization (visible)
LAYER_3 = 'Layer 3'  # Wheel/Steering/Brake visualization (visible)
LAYER_4 = 'Layer 4'  # GroundSensor visualization (visible)
LAYER_5 = 'Layer 5'  # Door/Trunk visualization (visible)

# Bone Collection Groups - Hidden Collections
COLLECTION_DIRECTION = 'Direction'  # Root, Drift (hidden)
COLLECTION_SUSPENSION = 'Suspension'  # Suspension, Damper_* (hidden)
COLLECTION_WHEEL = 'Wheel'  # Wheel_*, Brake_*, Steering (hidden)
COLLECTION_GROUND_SENSOR = 'GroundSensor'  # GroundSensor_* (hidden)
COLLECTION_DOOR_TRUNK = 'DoorTrunk'  # Door_*, Trunk_*, Hood_*, etc. (hidden)

# Helper collections (hidden)
COLLECTION_SHP = 'Layer 14'  # Shape/Display bones (SHP_*)
COLLECTION_MCH_CONTROL = 'Layer 15'  # MCH bones (mechanics control subset)
COLLECTION_DEF = 'Layer 16'  # DEF bones (deformation)
COLLECTION_MCH_MAIN = 'Layer 32'  # MCH bones (mechanics main)


def enumerate_ground_sensors(bones):
    bone = bones.get('GroundSensor_Axle_F')
    if bone is not None:
        yield bone
        for bone in bones:
            if bone.name.startswith('GroundSensor_F'):
                yield bone
    bone = bones.get('GroundSensor_Axle_B')
    if bone is not None:
        yield bone
        for bone in bones:
            if bone.name.startswith('GroundSensor_B'):
                yield bone


def deselect_edit_bones(ob):
    for b in ob.data.edit_bones:
        b.select = False
        b.select_head = False
        b.select_tail = False


def create_constraint_influence_driver(ob, cns, driver_data_path, base_influence=1.0):
    fcurve = cns.driver_add('influence')
    drv = fcurve.driver
    drv.type = 'AVERAGE'
    var = drv.variables.new()
    var.name = 'influence'
    var.type = 'SINGLE_PROP'

    targ = var.targets[0]
    targ.id_type = 'OBJECT'
    targ.id = ob
    targ.data_path = driver_data_path

    if base_influence != 1.0:
        fmod = fcurve.modifiers[0]
        fmod.mode = 'POLYNOMIAL'
        fmod.poly_order = 1
        fmod.coefficients = (0, base_influence)


def create_rotation_euler_x_driver(ob, bone, driver_data_path):
    fcurve = bone.driver_add('rotation_euler', 0)
    drv = fcurve.driver
    drv.type = 'AVERAGE'
    var = drv.variables.new()
    var.name = 'rotationAngle'
    var.type = 'SINGLE_PROP'

    targ = var.targets[0]
    targ.id_type = 'OBJECT'
    targ.id = ob
    targ.data_path = driver_data_path


def create_rotation_euler_z_driver(ob, bone, driver_data_path):
    fcurve = bone.driver_add('rotation_euler', 2)
    drv = fcurve.driver
    drv.type = 'AVERAGE'
    var = drv.variables.new()
    var.name = 'rotationAngle'
    var.type = 'SINGLE_PROP'

    targ = var.targets[0]
    targ.id_type = 'OBJECT'
    targ.id = ob
    targ.data_path = driver_data_path


def create_translation_x_driver(ob, bone, driver_data_path):
    fcurve = bone.driver_add('location', 0)
    drv = fcurve.driver
    drv.type = 'AVERAGE'
    var = drv.variables.new()
    var.name = 'rotationAngle'
    var.type = 'SINGLE_PROP'

    targ = var.targets[0]
    targ.id_type = 'OBJECT'
    targ.id = ob
    targ.data_path = driver_data_path


def create_custom_property_from_bone_rotation_z_driver(ob, property_name, bone):
    fcurve = ob.driver_add(f'["{property_name}"]')
    drv = fcurve.driver
    drv.type = 'AVERAGE'
    var = drv.variables.new()
    var.name = 'rotationAngle'
    var.type = 'SINGLE_PROP'

    targ = var.targets[0]
    targ.id_type = 'OBJECT'
    targ.id = ob
    targ.data_path = f'pose.bones["{bone.name}"].rotation_euler[2]'


def create_bone_group(pose, group_name, color_set, bone_names):
    # Here Only set color
    for bone_name in bone_names:
        bone = pose.bones.get(bone_name)
        if bone is not None:
            bone.color.palette = color_set


def name_range(prefix, nb=1000):
    """Generate sequential names for wheels/brakes.
    For new naming convention: Wheel_FR_0, Wheel_FR_1, Wheel_FR_2, etc.
    """
    # Check if prefix already has a number at the end (new format)
    import re
    match = re.match(r'^(.+)_(\d+)$', prefix)
    if match:
        base_prefix = match.group(1)
        start_num = int(match.group(2))
        if nb > 0:
            yield prefix
            for i in range(1, nb):
                yield f'{base_prefix}_{start_num + i}'
    else:
        # Old format or Body/Steering - keep as is
        if nb > 0:
            yield prefix
            for i in range(1, nb):
                yield '%s.%03d' % (prefix, i)


def get_widget(name):
    widget = bpy.data.objects.get(name)
    if widget is None:
        from . import widgets
        widgets.create()
        widget = bpy.data.objects.get(name)
    return widget


def define_custom_property(target, name, value, description=None, overridable=True):
    rna_idprop_ui_create(target, name, default=value, description=description, overridable=overridable, min=-inf,
                         max=inf)


def dispatch_bones_to_armature_layers(ob):
    '''Bone Collections organize bones into both visible layers (1-5) and hidden functional groups.
    Visible layers: Layer 1-5 show control bones organized by function
    Hidden collections: Direction, Suspension, Wheel, GroundSensor, DoorTrunk groups bones by type
    '''
    amt = bpy.context.object.data
    
    # Create visible layers (Layer 1-4)
    layer_1 = amt.collections.new(name=LAYER_1)
    layer_2 = amt.collections.new(name=LAYER_2)
    layer_3 = amt.collections.new(name=LAYER_3)
    layer_4 = amt.collections.new(name=LAYER_4)
    
    # Create hidden functional collections
    coll_direction = amt.collections.new(name=COLLECTION_DIRECTION)
    coll_suspension = amt.collections.new(name=COLLECTION_SUSPENSION)
    coll_wheel = amt.collections.new(name=COLLECTION_WHEEL)
    coll_ground_sensor = amt.collections.new(name=COLLECTION_GROUND_SENSOR)
    
    # Create helper collections (hidden)
    coll_shp = amt.collections.new(name=COLLECTION_SHP)
    coll_mch_control = amt.collections.new(name=COLLECTION_MCH_CONTROL)
    coll_def = amt.collections.new(name=COLLECTION_DEF)
    coll_mch_main = amt.collections.new(name=COLLECTION_MCH_MAIN)
    
    # Set visibility
    coll_direction.is_visible = False
    coll_suspension.is_visible = False
    coll_wheel.is_visible = False
    coll_ground_sensor.is_visible = False
    coll_shp.is_visible = False
    coll_mch_control.is_visible = False
    coll_def.is_visible = False
    coll_mch_main.is_visible = False
    
    # Compile regex patterns for different bone types
    re_mch_wheel_rotation = re.compile(r'^MCH_WheelRotation_[FB][LR]_\d+$')
    re_mch_brake = re.compile(r'^MCH_Brake_[FB][LR]_\d+$')
    re_ground_sensor = re.compile(r'^GroundSensor_[FB][LR]_\d+$')
    re_shp_ground_sensor = re.compile(r'^SHP_GroundSensor')
    re_wheel = re.compile(r'^Wheel_[FB][LR]_\d+$')
    re_brake = re.compile(r'^Brake_[FB][LR]_\d+$')
    re_damper = re.compile(r'^Damper_[FB][LR]_\d+$')
    re_mch_damper = re.compile(r'^MCH_Damper_[FB][LR]_\d+$')
    re_mch_wheel = re.compile(r'^MCH_Wheel_[FB][LR]_\d+$')
    
    # Assign bones to layers based on naming patterns and types
    for b in ob.data.bones:
        
        # Layer 16 - DEF bones (deformation) - helper collection
        if b.name.startswith('DEF_'):
            coll_def.assign(b)
        
        # Layer 32 - MCH bones (main mechanics) - helper collection
        elif b.name.startswith('MCH_'):
            coll_mch_main.assign(b)
            
            # Layer 15 - Subset of MCH bones (control-related) - helper collection
            if b.name in ('MCH_Body', 'MCH_Steering') or re_mch_wheel.match(b.name) or re_mch_brake.match(b.name):
                coll_mch_control.assign(b)
        
        # Layer 14 - SHP bones (shape/display) - helper collection
        elif b.name.startswith('SHP_'):
            coll_shp.assign(b)
        
        # === DIRECTION BONES ===
        # Layer 1 - Direction control bones (visible)
        # Direction collection - hidden
        elif b.name in ('Root', 'Drift'):
            layer_1.assign(b)
            coll_direction.assign(b)
        
        # SHP_Root, SHP_Drift go to Layer 14 and Direction collection
        elif b.name in ('SHP_Root', 'SHP_Drift'):
            coll_shp.assign(b)
            coll_direction.assign(b)
        
        # === SUSPENSION BONES ===
        # Layer 2 - Suspension control bones (visible)
        # Suspension collection - hidden
        elif b.name == 'Suspension' or re_damper.match(b.name):
            layer_2.assign(b)
            coll_suspension.assign(b)
        
        # === WHEEL BONES ===
        # Layer 3 - Wheel, Brake, Steering control bones (visible)
        # Wheel collection - hidden
        elif re_wheel.match(b.name) or b.name == 'Steering':
            layer_3.assign(b)
            coll_wheel.assign(b)
        
        elif re_brake.match(b.name):
            layer_3.assign(b)
            coll_wheel.assign(b)
        
        # === GROUND SENSOR BONES ===
        # Layer 4 - GroundSensor bones (visible)
        # GroundSensor collection - hidden
        elif re_ground_sensor.match(b.name) or b.name in ('GroundSensor_Axle_F', 'GroundSensor_Axle_B'):
            layer_4.assign(b)
            coll_ground_sensor.assign(b)
        
        # Fallback to Layer 1 (Direction)
        else:
            layer_1.assign(b)
            coll_direction.assign(b)
    
    # Multi-layer assignments for shape bones
    for b in ob.data.bones:
        # Assign shape bones to their corresponding collections
        if b.name == 'SHP_Steering' or b.name.startswith('SHP_GroundSensor'):
            coll_ground_sensor.assign(b)
        elif b.name.startswith('SHP_Wheel') or b.name.startswith('SHP_Brake'):
            coll_wheel.assign(b)
        elif b.name.startswith('SHP_Damper'):
            coll_suspension.assign(b)
    
    # Handle custom shape bones
    for b in ob.pose.bones:
        if b.custom_shape:
            if b.custom_shape_transform:
                # Assign custom shape transform bone to helper collection
                shp_bone = ob.data.bones[b.custom_shape_transform.name]
                coll_shp.assign(shp_bone)
    
    # Optionally create Layer 5 and DoorTrunk collection for door/trunk support
    # Only create if any door/trunk bones exist
    has_door_trunk = any(b.name.startswith(('Door', 'Trunk')) for b in ob.data.bones)
    if has_door_trunk:
        layer_5 = amt.collections.new(name=LAYER_5)
        coll_door_trunk = amt.collections.new(name=COLLECTION_DOOR_TRUNK)
        coll_door_trunk.is_visible = False
        
        re_door_trunk = re.compile(r'^(Door|Trunk|Hood|Hatch|Tailgate)_?.*$', re.IGNORECASE)
        for b in ob.data.bones:
            if re_door_trunk.match(b.name) and not b.name.startswith(('DEF_', 'MCH_', 'SHP_')):
                layer_5.assign(b)
                coll_door_trunk.assign(b)


def set_edit_mode_bone_colors(ob):
    """Set bone colors for edit mode only, based on bone types.
    
    Colors visible only in edit mode:
    - suspension: 09 theme color set
    - groundsensor_ and groundsensor_axle_: 02 theme color set
    - Wheel_FL, Wheel_FR, Wheel_BL, Wheel_BR: 03 theme color set
    - root and drift: 04 theme color set
    - steering: 03 theme color set
    - door_ and trunk_: 05 theme color set
    - all others: default color set
    """
    edit_bones = ob.data.edit_bones
    
    # Theme color mapping
    theme_colors = {
        'THEME02': 2,  # GroundSensor
        'THEME03': 3,  # Wheel/Steering
        'THEME04': 4,  # Root/Drift
        'THEME05': 5,  # Door/Trunk
        'THEME09': 9,  # Suspension
    }
    
    for bone in edit_bones:
        # Determine which color set this bone should use
        color_set = None
        bone_name_lower = bone.name.lower()
        
        # Check suspension bones
        if 'suspension' in bone_name_lower:
            color_set = 'THEME09'
        
        # Check ground sensor bones
        elif 'groundsensor' in bone_name_lower or bone.name.startswith('GroundSensor_Axle'):
            color_set = 'THEME02'
        
        # Check wheel bones (Wheel_FL, Wheel_FR, Wheel_BL, Wheel_BR)
        elif bone.name in ('Wheel_FL_0', 'Wheel_FR_0', 'Wheel_BL_0', 'Wheel_BR_0') or \
             any(bone.name.startswith(f'Wheel_{pos}_') for pos in ['FL', 'FR', 'BL', 'BR']):
            color_set = 'THEME03'
        
        # Check steering bones
        elif bone.name == 'Steering' or 'steering' in bone_name_lower:
            color_set = 'THEME03'
        
        # Check root and drift
        elif bone.name in ('Root', 'Drift', 'SHP_Root', 'SHP_Drift'):
            color_set = 'THEME04'
        
        # Check door and trunk bones
        elif bone.name.startswith(('Door_', 'Trunk_', 'Hood_', 'Hatch_', 'Tailgate_')):
            color_set = 'THEME05'
        
        # Apply color if determined
        if color_set:
            # Set both the color palette (for Blender 3.2+) and bone_color.palette
            try:
                bone.color.palette = color_set
            except:
                # Fallback for older Blender versions
                pass


class NameSuffix(object):

    def __init__(self, position, side, index=0):
        self.position = position
        self.side = side
        self.index = index
        # Generate value in new format: FR_0, FR_1, BL_2, etc.
        # position: 'Ft' or 'Bk', side: 'L' or 'R'
        pos_abbr = 'F' if position == 'Ft' else 'B'
        self.value = f'{pos_abbr}{side}_{index}'

    def name(self, base_name=None):
        if base_name:
            # Generate Traffiq format: MCH_WheelRotation_FR_0
            return f'{base_name}_{self.value}'
        return self.value

    @property
    def is_front(self):
        return self.position == 'Ft'

    @property
    def is_left(self):
        return self.side == 'L'

    @property
    def is_first(self):
        return self.index == 0

    def __str__(self):
        return self.value


class BoundingBox(object):

    def __init__(self, armature, bone_name):
        objs = [o for o in armature.children if o.parent_bone == bone_name]
        bone = armature.data.bones[bone_name]
        self.__center = bone.head.copy()
        if not objs:
            self.__xyz = [bone.head.x - bone.length / 2, bone.head.x + bone.length / 2, bone.head.y - bone.length,
                          bone.head.y + bone.length, .0, bone.head.z * 2]
        else:
            self.__xyz = [inf, -inf, inf, -inf, inf, -inf]
            self.__compute(mathutils.Matrix(), *objs)

    def __compute(self, pmatrix, *objs):
        for obj in objs:
            omatrix = pmatrix @ obj.matrix_world
            if obj.instance_type == 'COLLECTION':
                self.__compute(omatrix, *obj.instance_collection.all_objects)
            elif obj.bound_box:
                for p in obj.bound_box:
                    world_p = omatrix @ mathutils.Vector(p)
                    self.__xyz[0] = min(world_p.x, self.__xyz[0])
                    self.__xyz[1] = max(world_p.x, self.__xyz[1])
                    self.__xyz[2] = min(world_p.y, self.__xyz[2])
                    self.__xyz[3] = max(world_p.y, self.__xyz[3])
                    self.__xyz[4] = min(world_p.z, self.__xyz[4])
                    self.__xyz[5] = max(world_p.z, self.__xyz[5])
            self.__compute(pmatrix, *obj.children)

    @property
    def center(self):
        return self.__center

    @property
    def box_center(self):
        return mathutils.Vector((self.max_x + self.min_x, self.max_y + self.min_y, self.max_z + self.min_z)) / 2

    @property
    def min_x(self):
        return self.__xyz[0]

    @property
    def max_x(self):
        return self.__xyz[1]

    @property
    def min_y(self):
        return self.__xyz[2]

    @property
    def max_y(self):
        return self.__xyz[3]

    @property
    def min_z(self):
        return self.__xyz[4]

    @property
    def max_z(self):
        return self.__xyz[5]

    @property
    def width(self):
        return abs(self.__xyz[0] - self.__xyz[1])

    @property
    def length(self):
        return abs(self.__xyz[2] - self.__xyz[3])

    @property
    def height(self):
        return abs(self.__xyz[4] - self.__xyz[5])


class WheelBoundingBox(BoundingBox):

    def __init__(self, armature, bone_name, side):
        super().__init__(armature, bone_name)
        self.side = side

    def compute_outer_x(self, delta=0):
        if self.side == 'L':
            return self.max_x + delta
        else:
            return self.min_x - delta


class WheelsDimension(object):

    def __init__(self, armature, position, side_position, default):
        self.default = default
        self.position = position
        self.side_position = side_position
        self.wheels = []
        # Generate new naming pattern: DEF_Wheel_FR_0, DEF_Wheel_FR_1, etc.
        pos_abbr = 'F' if position == 'Ft' else 'B'
        base_wheel_suffix = f'{pos_abbr}{side_position}_0'
        wheel_bones = (armature.data.edit_bones.get(name) for name in
                       name_range(f'DEF_Wheel_{base_wheel_suffix}'))
        for wheel_bone in wheel_bones:
            if wheel_bone is None:
                break
            self.wheels.append(WheelBoundingBox(armature, wheel_bone.name, side_position))

    def name_suffixes(self):
        for i in range(len(self.wheels)):
            yield NameSuffix(self.position, self.side_position, i)

    def names(self, base_name=None):
        pos_abbr = 'F' if self.position == 'Ft' else 'B'
        base_suffix = f'{pos_abbr}{self.side_position}_0'
        for name_suffix in name_range(base_suffix, self.nb):
            yield f'{base_name}_{name_suffix}' if base_name else name_suffix

    def name(self, base_name=None):
        pos_abbr = 'F' if self.position == 'Ft' else 'B'
        suffix = f'{pos_abbr}{self.side_position}_0'
        return f'{base_name}_{suffix}' if base_name else suffix

    @property
    def nb(self):
        return len(self.wheels)

    @property
    def min_position(self):
        if self.nb == 0:
            return self.default
        return min(self.wheels, key=lambda w: w.center.y).center

    @property
    def max_position(self):
        if self.nb == 0:
            return self.default
        return max(self.wheels, key=lambda w: w.center.y).center

    @property
    def medium_position(self):
        if self.nb == 0:
            return self.min_position
        return (self.min_position + self.max_position) / 2.0

    def compute_outer_x(self, delta=0):
        if self.side_position == 'L':
            x = max(map(lambda w: w.max_x, self.wheels))
            x += delta
        else:
            x = min(map(lambda w: w.min_x, self.wheels))
            x -= delta
        return x

    @property
    def outer_z(self):
        return max(map(lambda w: w.max_z, self.wheels))

    @property
    def outer_front(self):
        return min(map(lambda w: w.min_y, self.wheels))

    @property
    def outer_back(self):
        return max(map(lambda w: w.max_y, self.wheels))


class CarDimension(object):

    def __init__(self, armature):
        body = armature.data.edit_bones['DEF_Body']
        self.bb_body = BoundingBox(armature, 'DEF_Body')
        self.wheels_front_left = WheelsDimension(armature, 'Ft', 'L', default=body.head)
        self.wheels_front_right = WheelsDimension(armature, 'Ft', 'R', default=body.head)
        self.wheels_back_left = WheelsDimension(armature, 'Bk', 'L', default=body.tail)
        self.wheels_back_right = WheelsDimension(armature, 'Bk', 'R', default=body.tail)

    @property
    def body_center(self):
        return self.bb_body.center

    @property
    def car_center(self):
        center = self.bb_body.box_center.copy()
        center.y = (self.max_y + self.min_y) / 2
        return center

    @property
    def width(self):
        return max([self.bb_body.width] + [abs(w.compute_outer_x() - self.bb_body.center.x) * 2 for w in
                                           self.wheels_dimensions])

    @property
    def height(self):
        return max([self.bb_body.max_z] + [w.outer_z for w in self.wheels_dimensions])

    @property
    def length(self):
        return abs(self.max_y - self.min_y)

    @property
    def min_y(self):
        return min([self.bb_body.min_y] + [w.outer_front for w in self.wheels_dimensions])

    @property
    def max_y(self):
        return max([self.bb_body.max_y] + [w.outer_back for w in self.wheels_dimensions])

    @property
    def wheels_front_position(self):
        position = (self.wheels_front_left.min_position + self.wheels_front_right.min_position) / 2
        position.x = self.bb_body.center.x
        return position

    @property
    def wheels_back_position(self):
        position = (self.wheels_back_left.max_position + self.wheels_back_right.max_position) / 2
        position.x = self.bb_body.center.x
        return position

    @property
    def suspension_front_position(self):
        position = (self.wheels_front_left.medium_position + self.wheels_front_right.medium_position) / 2
        position.x = self.bb_body.center.x
        return position

    @property
    def suspension_back_position(self):
        position = (self.wheels_back_left.medium_position + self.wheels_back_right.medium_position) / 2
        position.x = self.bb_body.center.x
        return position

    @property
    def has_wheels(self):
        return self.has_front_wheels or self.has_back_wheels

    @property
    def has_front_wheels(self):
        return self.nb_front_wheels > 0

    @property
    def has_back_wheels(self):
        return self.nb_back_wheels > 0

    @property
    def nb_front_wheels(self):
        return max(self.wheels_front_left.nb, self.wheels_front_right.nb)

    @property
    def nb_back_wheels(self):
        return max(self.wheels_back_left.nb, self.wheels_back_right.nb)

    @property
    def wheels_dimensions(self):
        return filter(lambda w: w.nb,
                      (self.wheels_front_left, self.wheels_front_right, self.wheels_back_left, self.wheels_back_right))


def create_wheel_brake_bone(wheel_brake, parent_bone, wheel_bone):
    wheel_brake.use_deform = False
    wheel_brake.parent = parent_bone  # This is MCH_Brake
    wheel_brake.head = wheel_bone.head
    wheel_brake.tail = wheel_bone.tail


def generate_constraint_on_wheel_brake_bone(wheel_brake_pose_bone, wheel_pose_bone):
    wheel_brake_pose_bone.lock_location = (True, True, True)
    wheel_brake_pose_bone.lock_rotation = (True, True, True)
    wheel_brake_pose_bone.lock_rotation_w = True
    wheel_brake_pose_bone.lock_scale = (True, False, False)
    wheel_brake_pose_bone.custom_shape = get_widget('WGT-CarRig.WheelBrake')
    wheel_brake_pose_bone.bone.show_wire = True
    amt = bpy.context.object.data
    groups = amt.collections
    for group in groups:
        for bone in group.bones:
            if bone.name == wheel_pose_bone.name:
                group.assign(wheel_brake_pose_bone)

    cns = wheel_brake_pose_bone.constraints.new('LIMIT_SCALE')
    cns.name = 'Brakes'
    cns.use_transform_limit = True
    cns.owner_space = 'LOCAL'
    cns.use_max_x = True
    cns.use_min_x = True
    cns.min_x = 1.0
    cns.max_x = 1.0
    cns.use_max_y = True
    cns.use_min_y = True
    cns.min_y = .5
    cns.max_y = 1.0
    cns.use_max_z = True
    cns.use_min_z = True
    cns.min_z = .5
    cns.max_z = 1.0


class ArmatureGenerator(object):

    def __init__(self, ob):
        self.ob = ob

    def generate(self, scene, adjust_origin):
        # Traffiq-compatible property names
        define_custom_property(self.ob,
                               name='tq_WheelsYRolling',
                               value=False,
                               description="Activate wheels rotation when moving the root bone along the Y axis")
        define_custom_property(self.ob,
                               name='tq_SuspensionFactor',
                               value=.5,
                               description="Influence of the dampers over the pitch of the body")
        define_custom_property(self.ob,
                               name='tq_SuspensionRollingFactor',
                               value=.5,
                               description="Influence of the dampers over the roll of the body")

        location = self.ob.location.copy()
        self.ob.location = (0, 0, 0)
        try:
            bpy.ops.object.mode_set(mode='EDIT')
            self.dimension = CarDimension(self.ob)
            self.generate_animation_rig()
            self.ob.data['Car Rig'] = True
            deselect_edit_bones(self.ob)

            if adjust_origin:
                bpy.ops.object.mode_set(mode='OBJECT')
                self.set_origin(scene)

            bpy.ops.object.mode_set(mode='POSE')
            self.generate_constraints_on_rig()
            self.ob.display_type = 'WIRE'

            self.generate_bone_groups()
            dispatch_bones_to_armature_layers(self.ob)
            
            # Set bone colors for edit mode display
            bpy.ops.object.mode_set(mode='EDIT')
            set_edit_mode_bone_colors(self.ob)
            bpy.ops.object.mode_set(mode='POSE')
        finally:
            self.ob.location += location

    def generate_animation_rig(self):
        amt = self.ob.data

        body = amt.edit_bones['DEF_Body']
        root = amt.edit_bones.new('Root')
        # Position head at the head of SHP_GroundSensor_Axle_B (wheels_back_position)
        root.head = self.dimension.wheels_back_position
        root.head.z = 0
        root.tail = root.head
        root.tail.y += max(self.dimension.length / 1.95, self.dimension.width * 1.1)
        root.use_deform = False

        shape_root = amt.edit_bones.new('SHP_Root')
        shape_root.head = self.dimension.car_center
        shape_root.head.z = 0.01
        shape_root.tail = shape_root.head
        shape_root.tail.y += root.length
        shape_root.use_deform = False
        shape_root.parent = root

        drift = amt.edit_bones.new('Drift')
        drift.head = self.dimension.wheels_front_position
        drift.head.z = self.dimension.wheels_back_position.z
        drift.tail = drift.head
        drift.tail.y -= self.dimension.width * .95
        drift.roll = math.pi
        drift.use_deform = False
        drift.parent = root
        base_bone_parent = drift

        if self.dimension.has_front_wheels:
            groundsensor_axle_front = amt.edit_bones.new('GroundSensor_Axle_F')
            groundsensor_axle_front.head = self.dimension.wheels_front_position
            groundsensor_axle_front.tail = groundsensor_axle_front.head
            groundsensor_axle_front.tail.y += self.dimension.length / 16
            groundsensor_axle_front.parent = root  # Child of Root, not Drift

            shp_groundsensor_axle_front = amt.edit_bones.new('SHP_GroundSensor_Axle_F')
            shp_groundsensor_axle_front.head = groundsensor_axle_front.head
            shp_groundsensor_axle_front.tail = groundsensor_axle_front.tail
            shp_groundsensor_axle_front.head.z = shp_groundsensor_axle_front.tail.z = 0.001
            shp_groundsensor_axle_front.parent = groundsensor_axle_front

            mch_root_axle_front = amt.edit_bones.new('MCH_Root_Axle_F')
            mch_root_axle_front.head = self.dimension.wheels_front_position
            mch_root_axle_front.head.z = 0.001
            mch_root_axle_front.tail = mch_root_axle_front.head
            mch_root_axle_front.tail.y += self.dimension.length / 6
            mch_root_axle_front.parent = groundsensor_axle_front
            if not self.dimension.has_back_wheels:
                drift.parent = mch_root_axle_front

        if self.dimension.has_back_wheels:
            groundsensor_axle_back = amt.edit_bones.new('GroundSensor_Axle_B')
            groundsensor_axle_back.head = self.dimension.wheels_back_position
            groundsensor_axle_back.tail = groundsensor_axle_back.head
            groundsensor_axle_back.tail.y += self.dimension.length / 16
            groundsensor_axle_back.parent = drift

            shp_groundsensor_axle_back = amt.edit_bones.new('SHP_GroundSensor_Axle_B')
            shp_groundsensor_axle_back.head = groundsensor_axle_back.head
            shp_groundsensor_axle_back.tail = groundsensor_axle_back.tail
            shp_groundsensor_axle_back.head.z = shp_groundsensor_axle_back.tail.z = 0.001
            shp_groundsensor_axle_back.parent = groundsensor_axle_back

            mch_root_axle_back = amt.edit_bones.new('MCH_Root_Axle_B')
            mch_root_axle_back.head = self.dimension.wheels_back_position
            mch_root_axle_back.head.z = 0
            mch_root_axle_back.tail = mch_root_axle_back.head
            mch_root_axle_back.tail.y += self.dimension.length / 6
            mch_root_axle_back.parent = groundsensor_axle_back
            base_bone_parent = mch_root_axle_back

        shape_drift = amt.edit_bones.new('SHP_Drift')
        shape_drift.head = self.dimension.body_center
        shape_drift.head.y = self.dimension.max_y + drift.length * .2
        shape_drift.head.z = self.dimension.wheels_back_position.z
        shape_drift.tail = shape_drift.head
        shape_drift.tail.y += drift.length
        shape_drift.use_deform = False
        shape_drift.parent = base_bone_parent

        for wheel_dimension in self.dimension.wheels_dimensions:
            for name_suffix, wheel_bounding_box in zip(wheel_dimension.name_suffixes(), wheel_dimension.wheels):
                self.generate_animation_wheel_bones(name_suffix, wheel_bounding_box, base_bone_parent)
            self.generate_wheel_damper(wheel_dimension, base_bone_parent)

        if self.dimension.has_front_wheels:
            wheel_ft_r = amt.edit_bones.get('DEF_Wheel_FR_0')
            wheelFtL = amt.edit_bones.get('DEF_Wheel_FL_0')

            axis_ft = amt.edit_bones.new('MCH_Axis_F')
            axis_ft.head = wheel_ft_r.head
            axis_ft.tail = wheelFtL.head
            axis_ft.use_deform = False
            axis_ft.parent = base_bone_parent

            mch_steering = amt.edit_bones.new('MCH_Steering')
            mch_steering.head = self.dimension.wheels_front_position
            mch_steering.tail = self.dimension.wheels_front_position
            mch_steering.tail.y += self.dimension.width / 2
            mch_steering.use_deform = False
            mch_steering.parent = groundsensor_axle_front  # Child of GroundSensor_Axle_F per Traffiq

            steering_rotation = amt.edit_bones.new('MCH_SteeringRotation')
            steering_rotation.head = mch_steering.head
            steering_rotation.tail = mch_steering.tail
            steering_rotation.tail.y += 1
            steering_rotation.use_deform = False
            steering_rotation.parent = None

            steering = amt.edit_bones.new('Steering')
            steering.head = mch_steering.head
            steering.head.y = self.dimension.min_y - 4 * wheelFtL.length
            steering.tail = steering.head
            steering.tail.y -= self.dimension.width / 2
            steering.use_deform = False
            steering.parent = steering_rotation

        if self.dimension.has_back_wheels:
            wheel_bk_r = amt.edit_bones.get('DEF_Wheel_BR_0')
            wheel_bk_l = amt.edit_bones.get('DEF_Wheel_BL_0')

            axisBk = amt.edit_bones.new('MCH_Axis_B')
            axisBk.head = wheel_bk_r.head
            axisBk.tail = wheel_bk_l.head
            axisBk.use_deform = False
            axisBk.parent = base_bone_parent

        suspension_bk = amt.edit_bones.new('MCH_Suspension_B')
        suspension_bk.head = self.dimension.suspension_back_position
        suspension_bk.tail = self.dimension.suspension_back_position
        suspension_bk.tail.y += 2
        suspension_bk.use_deform = False
        suspension_bk.parent = base_bone_parent

        suspension_ft = amt.edit_bones.new('MCH_Suspension_F')
        suspension_ft.head = self.dimension.suspension_front_position
        align_vector = suspension_bk.head - suspension_ft.head
        align_vector.magnitude = 2
        suspension_ft.tail = self.dimension.suspension_front_position + align_vector
        suspension_ft.use_deform = False
        suspension_ft.parent = base_bone_parent

        axis = amt.edit_bones.new('MCH_Axis')
        axis.head = suspension_ft.head
        axis.tail = suspension_bk.head
        axis.use_deform = False
        axis.parent = suspension_ft

        mch_body = amt.edit_bones.new('MCH_Body')
        mch_body.head = mathutils.Vector((0, 0, 0))  # Position at armature origin
        mch_body.tail = mathutils.Vector((0, 1, 0))  # Point along Y axis
        mch_body.use_deform = False
        mch_body.parent = axis

        suspension = amt.edit_bones.new('Suspension')
        suspension.head = self.dimension.body_center
        suspension.head.z = self.dimension.height + self.dimension.width * .25
        suspension.tail = suspension.head
        suspension.tail.y += root.length * .5
        suspension.use_deform = False
        suspension.parent = axis
        
        # Create door and trunk bones only for meshes that exist
        self.create_door_trunk_bones(amt, body)

    def create_door_trunk_bones(self, amt, body):
        """Create door and trunk bones only for meshes that were found during deformation rig creation"""
        
        def find_matching_mesh(bone_name):
            """Find mesh object matching door/trunk bone name"""
            # First pass: exact name match or contains bone name
            for obj in bpy.data.objects:
                if obj.type == 'MESH' and bone_name in obj.name:
                    if obj.bound_box:
                        return obj
            return None
        
        def compute_bone_from_bbox(mesh_obj):
            """
            Compute bone head/tail from mesh bounding box Y-axis.
            Head at y-max (highest Z on that face), tail at y-min (lowest Z on that face).
            Returns (head, tail) in armature-local space.
            """
            # Get bounding box in world space
            bbox_world = [mesh_obj.matrix_world @ mathutils.Vector(corner) for corner in mesh_obj.bound_box]
            
            # Transform to armature-local space
            arm_inv = self.ob.matrix_world.inverted()
            bbox_local = [arm_inv @ p for p in bbox_world]
            
            # Extract Y values and find extremes
            ys = [v.y for v in bbox_local]
            max_y = max(ys)
            min_y = min(ys)
            
            # Compute center X and Z for alignment
            xs = [v.x for v in bbox_local]
            zs = [v.z for v in bbox_local]
            center_x = sum(xs) / len(xs)
            center_z = sum(zs) / len(zs)
            
            # Gather corners at y-max and y-min faces
            eps = 1e-6
            y_max_points = [v for v in bbox_local if abs(v.y - max_y) <= eps]
            y_min_points = [v for v in bbox_local if abs(v.y - min_y) <= eps]
            
            # Head: y-max face, highest Z corner
            if y_max_points:
                highest_z = max(y_max_points, key=lambda v: v.z).z
                head = mathutils.Vector((center_x, max_y, highest_z))
            else:
                head = mathutils.Vector((center_x, max_y, center_z))
            
            # Tail: y-min face, lowest Z corner
            if y_min_points:
                lowest_z = min(y_min_points, key=lambda v: v.z).z
                tail = mathutils.Vector((center_x, min_y, lowest_z))
            else:
                tail = mathutils.Vector((center_x, min_y, center_z))
            
            # Ensure head is above tail (swap if needed)
            if head.z < tail.z:
                head, tail = tail, head
            
            return head, tail
        
        # Check which door/trunk meshes exist by looking for objects with vertex groups
        door_trunk_configs = [
            ('Door_FL_0', 0.8, 0.3),    # (name, x_offset, y_offset)
            ('Door_FR_0', -0.8, 0.3),
            ('Door_BL_0', 0.8, -0.3),
            ('Door_BR_0', -0.8, -0.3),
        ]
        trunk_configs = [
            ('Trunk_F_0', self.dimension.min_y - 0.3, -0.5),  # (name, y_pos, tail_offset)
            ('Trunk_B_0', self.dimension.max_y + 0.3, 0.5),
        ]
        
        # Create door bones for found meshes
        for door_name, x_offset, y_offset in door_trunk_configs:
            # Check if any object has this vertex group (means mesh was found)
            if any(door_name in obj.vertex_groups for obj in bpy.data.objects if obj.type == 'MESH'):
                door = amt.edit_bones.new(door_name)
                
                # Try to find matching mesh and compute bone from it
                mesh_obj = find_matching_mesh(door_name)
                if mesh_obj:
                    head, tail = compute_bone_from_bbox(mesh_obj)
                    door.head = head
                    door.tail = tail
                    door.roll = 0.0
                else:
                    # Fallback to old positioning
                    door.head = self.dimension.body_center.copy()
                    door.head.x += x_offset
                    door.head.y = self.dimension.body_center.y + y_offset
                    door.head.z = self.dimension.body_center.z + 0.4
                    door.tail = door.head.copy()
                    door.tail.y += 0.3 if y_offset > 0 else -0.3
                    door.tail.z = self.dimension.body_center.z + 0.1
                
                door.use_deform = True
                door.parent = body
                
                # Create shape bone at tail position for widget placement
                shp_door = amt.edit_bones.new(f'SHP_{door_name}')
                shp_door.head = door.tail.copy()
                shp_door.head.z += 0.1  # Slightly above the bone tail
                shp_door.tail = shp_door.head.copy()
                shp_door.tail.z -= 0.01  # Small tail for shape bone
                shp_door.use_deform = False
                shp_door.parent = door
        
        # Create trunk bones for found meshes
        for trunk_name, y_pos, tail_offset in trunk_configs:
            # Check if mesh with this trunk name exists
            mesh_obj = find_matching_mesh(trunk_name)
            if mesh_obj:
                trunk = amt.edit_bones.new(trunk_name)
                
                # Compute bone from mesh bounding box
                head, tail = compute_bone_from_bbox(mesh_obj)
                # For Trunk_B_*, swap Z values of head and tail (keep Y values)
                if trunk_name.startswith('Trunk_B_'):
                    trunk.head = tail.copy()
                    trunk.tail = head.copy()
                    trunk.head.z, trunk.tail.z = trunk.tail.z, trunk.head.z
                else:
                    trunk.head = head
                    trunk.tail = tail
                trunk.roll = 0.0
                
                trunk.use_deform = True
                trunk.parent = body
                trunk.use_connect = False  # Not connected, so trunk can rotate independently

    def generate_animation_wheel_bones(self, name_suffix, wheel_bounding_box, parent_bone):
        amt = self.ob.data

        def_wheel_bone = amt.edit_bones.get(name_suffix.name('DEF_Wheel'))

        if def_wheel_bone is None:
            return

        ground_sensor = amt.edit_bones.new(name_suffix.name('GroundSensor'))
        ground_sensor.head = wheel_bounding_box.box_center
        ground_sensor.head.z = def_wheel_bone.head.z
        ground_sensor.tail = ground_sensor.head
        ground_sensor.tail.y += max(max(wheel_bounding_box.height, ground_sensor.head.z) / 2.5,
                                    wheel_bounding_box.width * 1.02)
        ground_sensor.use_deform = False
        ground_sensor.parent = parent_bone

        shp_ground_sensor = amt.edit_bones.new(name_suffix.name('SHP_GroundSensor'))
        shp_ground_sensor.head = ground_sensor.head
        shp_ground_sensor.tail = ground_sensor.tail
        shp_ground_sensor.head.z = shp_ground_sensor.tail.z = .001
        shp_ground_sensor.use_deform = False
        shp_ground_sensor.parent = ground_sensor

        mch_wheel = amt.edit_bones.new(name_suffix.name('MCH_Wheel'))
        mch_wheel.head = def_wheel_bone.head
        mch_wheel.tail = def_wheel_bone.tail
        mch_wheel.tail.y += .5
        mch_wheel.use_deform = False
        mch_wheel.parent = ground_sensor

        # Use Traffiq naming: tq_WheelRotation_FR_0, tq_WheelRotation_BL_1, etc.
        wheel_prop_name = f'tq_WheelRotation_{name_suffix.value}'
        define_custom_property(self.ob,
                               name=wheel_prop_name,
                               value=0.0,
                               description="Animation property for wheel spinning")
        mch_wheel_rotation = amt.edit_bones.new(name_suffix.name('MCH_WheelRotation'))
        mch_wheel_rotation.head = def_wheel_bone.head
        mch_wheel_rotation.tail = def_wheel_bone.head
        mch_wheel_rotation.tail.y += mch_wheel_rotation.tail.z
        mch_wheel_rotation.use_deform = False
        mch_wheel_rotation.parent = None  # At root level per Traffiq structure

        def_wheel_brake_bone = amt.edit_bones.get(name_suffix.name('DEF_Brake'))
        if def_wheel_brake_bone is not None:
            mch_brake = amt.edit_bones.new(name_suffix.name('MCH_Brake'))
            mch_brake.head = def_wheel_brake_bone.head
            mch_brake.tail = def_wheel_brake_bone.tail
            mch_brake.tail.y += .5
            mch_brake.use_deform = False
            mch_brake.parent = ground_sensor

        wheel = amt.edit_bones.new(name_suffix.name('Wheel'))
        wheel.use_deform = False
        wheel.parent = ground_sensor
        wheel.head = def_wheel_bone.head
        wheel.head.x = wheel_bounding_box.compute_outer_x(wheel_bounding_box.length * .05)
        wheel.tail = wheel.head
        wheel.tail.y += wheel.tail.z * .9

        # Create Brake control bone ONLY for FL and BL wheels (left wheels only)
        if def_wheel_brake_bone is not None and name_suffix.is_left:
            wheel_brake = amt.edit_bones.new(name_suffix.name('Brake'))
            # Use wheel position for all brake bones (FL and BL)
            create_wheel_brake_bone(wheel_brake, mch_brake, wheel)
            wheel_brake.use_deform = False
            wheel_brake.parent = mch_brake

    def generate_wheel_damper(self, wheel_dimension, parent_bone):
        amt = self.ob.data

        if wheel_dimension.nb == 1:
            wheel_damper_parent = amt.edit_bones[wheel_dimension.name('GroundSensor')]
        else:
            wheel_damper_parent = amt.edit_bones.new(wheel_dimension.name('MCH_GroundSensor'))
            wheel_damper_parent.head = wheel_dimension.medium_position
            wheel_damper_parent.tail = wheel_dimension.medium_position
            wheel_damper_parent.tail.y += 1.0
            wheel_damper_parent.head.z = 0
            wheel_damper_parent.tail.z = 0
            wheel_damper_parent.use_deform = False
            wheel_damper_parent.parent = parent_bone

        wheel_damper = amt.edit_bones.new(wheel_dimension.name('Damper'))
        wheel_damper.head = wheel_dimension.medium_position
        wheel_damper_scale_ratio = abs(wheel_damper.head.z)
        wheel_damper.head.x = wheel_dimension.compute_outer_x(wheel_damper_scale_ratio * .25)
        wheel_damper.head.z *= 1.5
        wheel_damper.tail = wheel_damper.head
        wheel_damper.tail.y += wheel_damper_scale_ratio
        wheel_damper.use_deform = False
        wheel_damper.parent = wheel_damper_parent

        mch_wheel_damper = amt.edit_bones.new(wheel_dimension.name('MCH_Damper'))
        mch_wheel_damper.head = wheel_dimension.medium_position
        mch_wheel_damper.tail = wheel_dimension.medium_position
        mch_wheel_damper.tail.y += 2
        mch_wheel_damper.use_deform = False
        mch_wheel_damper.parent = wheel_damper

    def generate_constraints_on_rig(self):
        pose = self.ob.pose
        amt = self.ob.data

        for b in pose.bones:
            if b.name.startswith('DEF_') or b.name.startswith('MCH_') or b.name.startswith('SHP_'):
                b.lock_location = (True, True, True)
                b.lock_rotation = (True, True, True)
                b.lock_scale = (True, True, True)
                b.lock_rotation_w = True

        for wheel_dimension in self.dimension.wheels_dimensions:
            for name_suffix in wheel_dimension.name_suffixes():
                self.generate_constraints_on_wheel_bones(name_suffix)
            self.generate_constraints_on_wheel_damper(wheel_dimension)

        self.generate_constraints_on_axle_bones('Ft')
        self.generate_constraints_on_axle_bones('Bk')

        mch_axis = pose.bones.get('MCH_Axis')
        if mch_axis is not None:
            for axis_pos, influence in (('F', 1), ('B', .5)):
                subtarget = 'MCH_Axis_%s' % axis_pos
                if subtarget in pose.bones:
                    cns = mch_axis.constraints.new('TRANSFORM')
                    cns.name = 'Rotation from %s' % subtarget
                    cns.target = self.ob
                    cns.subtarget = subtarget
                    cns.map_from = 'ROTATION'
                    cns.from_min_x_rot = math.radians(-180)
                    cns.from_max_x_rot = math.radians(180)
                    cns.map_to_y_from = 'X'
                    cns.map_to = 'ROTATION'
                    cns.to_min_y_rot = math.radians(180)
                    cns.to_max_y_rot = math.radians(-180)
                    cns.owner_space = 'LOCAL'
                    cns.target_space = 'LOCAL'
                    create_constraint_influence_driver(self.ob, cns, '["tq_SuspensionRollingFactor"]',
                                                       base_influence=influence)

        root = pose.bones['Root']
        root.lock_scale = (True, True, True)
        root.custom_shape = get_widget('WGT-CarRig.Root')
        root.custom_shape_transform = pose.bones['SHP_Root']
        root.bone.show_wire = True

        for ground_sensor_axle_name in ('GroundSensor_Axle_F', 'GroundSensor_Axle_B'):
            ground_sensor_axle = pose.bones.get(ground_sensor_axle_name)
            if ground_sensor_axle:
                ground_sensor_axle.lock_location = (True, True, False)
                ground_sensor_axle.lock_rotation = (True, True, True)
                ground_sensor_axle.lock_scale = (True, True, True)
                ground_sensor_axle.custom_shape = get_widget('WGT-CarRig.GroundSensor.Axle')
                ground_sensor_axle.lock_rotation_w = True
                ground_sensor_axle.custom_shape_transform = pose.bones['SHP_%s' % ground_sensor_axle.name]
                ground_sensor_axle.bone.show_wire = True
                self.generate_ground_projection_constraint(ground_sensor_axle)

                if ground_sensor_axle.name == 'GroundSensor_Axle_F' and 'GroundSensor_Axle_B' in pose.bones:
                    cns = ground_sensor_axle.constraints.new('LIMIT_DISTANCE')
                    cns.name = 'Limit distance from Root'
                    cns.limit_mode = 'LIMITDIST_ONSURFACE'
                    cns.target = self.ob
                    cns.subtarget = 'GroundSensor_Axle_B'
                    cns.use_transform_limit = True
                    cns.owner_space = 'POSE'
                    cns.target_space = 'POSE'

        mch_root_axle_front = pose.bones.get('MCH_Root_Axle_F')
        mch_root_axle_back = pose.bones.get('MCH_Root_Axle_B')
        if mch_root_axle_front and mch_root_axle_back:
            cns = mch_root_axle_back.constraints.new('DAMPED_TRACK')
            cns.name = 'Track front axle'
            cns.target = self.ob
            cns.subtarget = mch_root_axle_front.name
            cns.track_axis = 'TRACK_NEGATIVE_Y'

        drift = pose.bones['Drift']
        drift.lock_location = (True, True, True)
        drift.lock_rotation = (True, True, False)
        drift.lock_scale = (True, True, True)
        drift.rotation_mode = 'ZYX'
        drift.custom_shape = get_widget('WGT-CarRig.DriftHandle')
        drift.custom_shape_transform = pose.bones['SHP_Drift']
        drift.bone.show_wire = True

        suspension = pose.bones['Suspension']
        suspension.lock_rotation = (True, True, True)
        suspension.lock_scale = (True, True, True)
        suspension.lock_rotation_w = True
        suspension.custom_shape = get_widget('WGT-CarRig.Suspension')
        suspension.bone.show_wire = True

        # Add LIMIT_LOCATION constraint to Suspension bone to restrict travel
        cns = suspension.constraints.new('LIMIT_LOCATION')
        cns.name = 'Limit Location'
        cns.use_transform_limit = True
        cns.owner_space = 'LOCAL'
        cns.use_min_x = True
        cns.use_max_x = True
        cns.min_x = -0.5
        cns.max_x = 0.5
        cns.use_min_y = True
        cns.use_max_y = True
        cns.min_y = -0.3
        cns.max_y = 0.3
        cns.use_min_z = True
        cns.use_max_z = True
        cns.min_z = -0.1
        cns.max_z = 0.1
        cns.use_transform_limit = True
        cns.influence = 1.0

        steering = pose.bones.get('Steering')
        if steering is not None:
            steering.lock_location = (False, True, True)
            steering.lock_rotation = (True, True, True)
            steering.lock_scale = (True, True, True)
            steering.lock_rotation_w = True
            steering.custom_shape = get_widget('WGT-CarRig.Steering')
            steering.bone.show_wire = True

            mch_steering_rotation = pose.bones['MCH_SteeringRotation']
            mch_steering_rotation.rotation_mode = 'QUATERNION'
            define_custom_property(self.ob,
                                   name='tq_SteeringRotation',
                                   value=.0,
                                   description="Animation property for steering")
            create_translation_x_driver(self.ob, mch_steering_rotation, '["tq_SteeringRotation"]')

            if mch_root_axle_back:
                cns = mch_steering_rotation.constraints.new('COPY_ROTATION')
                cns.name = 'Copy back axle rotation'
                cns.target = self.ob
                cns.subtarget = mch_root_axle_back.name
                cns.use_x = True
                cns.use_y = False
                cns.use_z = False
                cns.owner_space = 'LOCAL'
                cns.target_space = 'LOCAL'

            self.generate_childof_constraint(mch_steering_rotation,
                                             mch_root_axle_front if mch_root_axle_front else root)

            mch_steering = pose.bones['MCH_Steering']
            cns = mch_steering.constraints.new('DAMPED_TRACK')
            cns.name = 'Track steering bone'
            cns.target = self.ob
            cns.subtarget = 'Steering'
            cns.track_axis = 'TRACK_NEGATIVE_Y'

            cns = mch_steering.constraints.new('COPY_ROTATION')
            cns.name = 'Drift counter animation'
            cns.target = self.ob
            cns.subtarget = 'Drift'
            cns.use_x = False
            cns.use_y = False
            cns.use_z = True
            cns.use_offset = True
            cns.owner_space = 'LOCAL'
            cns.target_space = 'LOCAL'
            cns.influence = 1.0  # Disable drift affecting steering - keeps wheels pointing straight

        mch_body = self.ob.pose.bones['MCH_Body']
        cns = mch_body.constraints.new('TRANSFORM')
        cns.name = 'Suspension on rollover'
        cns.target = self.ob
        cns.subtarget = 'Suspension'
        cns.map_from = 'LOCATION'
        cns.from_min_x = -2
        cns.from_max_x = 2
        cns.from_min_y = -2
        cns.from_max_y = 2
        cns.map_to_x_from = 'Y'
        cns.map_to_y_from = 'X'
        cns.map_to = 'ROTATION'
        cns.to_min_x_rot = math.radians(6)
        cns.to_max_x_rot = math.radians(-6)
        cns.to_min_y_rot = math.radians(-7)
        cns.to_max_y_rot = math.radians(7)
        cns.owner_space = 'LOCAL'
        cns.target_space = 'LOCAL'

        cns = mch_body.constraints.new('TRANSFORM')
        cns.name = 'Suspension on vertical'
        cns.target = self.ob
        cns.subtarget = 'Suspension'
        cns.map_from = 'LOCATION'
        cns.from_min_z = -0.5
        cns.from_max_z = 0.5
        cns.map_to_z_from = 'Z'
        cns.map_to = 'LOCATION'
        cns.to_min_z = -0.1
        cns.to_max_z = 0.1
        cns.owner_space = 'LOCAL'
        cns.target_space = 'LOCAL'

        body = self.ob.pose.bones['DEF_Body']
        cns = body.constraints.new('COPY_TRANSFORMS')
        cns.target = self.ob
        cns.subtarget = 'MCH_Body'
        
        # Setup door bones constraints (Z-axis rotation)
        door_positions = [('Door_FL_0', -90, 0), ('Door_FR_0', 0, 90), 
                         ('Door_BL_0', -90, 0), ('Door_BR_0', 0, 90)]
        
        for door_name, min_angle, max_angle in door_positions:
            door = pose.bones.get(door_name)
            if door:
                # Limit rotation for doors (Z-axis rotation for opening/closing)
                cns = door.constraints.new('LIMIT_ROTATION')
                cns.name = 'Door Rotation Limit'
                cns.use_limit_z = True
                cns.min_z = math.radians(min_angle)
                cns.max_z = math.radians(max_angle)
                cns.owner_space = 'LOCAL'
                cns.use_transform_limit = True  # Affect transform (legacy behavior)
                
                # Add child_of constraint for door/trunk attachment to armature
                cns_child = door.constraints.new('CHILD_OF')
                cns_child.name = 'tq_Armature-Attachment'
                cns_child.target = self.ob
                cns_child.subtarget = 'DEF_Body'  # Reference the body bone
                cns_child.inverse_matrix = self.ob.data.bones['DEF_Body'].matrix_local.inverted()
                cns_child.use_location_x = True
                cns_child.use_location_y = True
                cns_child.use_location_z = True
                cns_child.use_rotation_x = True
                cns_child.use_rotation_y = True
                cns_child.use_rotation_z = True
                
                # Set widget and properties
                door.custom_shape = get_widget('WGT-CarRig.DoorTrunk')
                door.custom_shape_scale_xyz = (0.2, 0.2, 0.2)  # Smaller circle
                door.custom_shape_transform = pose.bones[f'SHP_{door_name}']  # Position at tail
                door.lock_location = (True, True, True)
                door.lock_rotation = (True, True, False)  # Only Z rotation allowed
                door.lock_scale = (True, True, True)
        
        # Setup trunk bones constraints (X-axis rotation, 65-80° range)
        # Handle all trunk bones (Trunk_F_0, Trunk_F_1, ..., Trunk_B_0, Trunk_B_1, ...)
        for bone in pose.bones:
            if bone.name.startswith('Trunk_'):
                # Limit rotation for trunks (X-axis pitch, opens upward)
                cns = bone.constraints.new('LIMIT_ROTATION')
                cns.name = 'Trunk Rotation Limit'
                cns.use_limit_x = True
                cns.min_x = math.radians(-80)  # Opens upward 80 degrees
                cns.max_x = 0
                cns.owner_space = 'LOCAL'
                cns.use_transform_limit = True  # Affect transform (legacy behavior)
                
                # Add child_of constraint for trunk attachment to armature
                cns_child = bone.constraints.new('CHILD_OF')
                cns_child.name = 'tq_Armature-Attachment'
                cns_child.target = self.ob
                cns_child.subtarget = 'DEF_Body'  # Reference the body bone
                cns_child.inverse_matrix = self.ob.data.bones['DEF_Body'].matrix_local.inverted()
                cns_child.use_location_x = True
                cns_child.use_location_y = True
                cns_child.use_location_z = True
                cns_child.use_rotation_x = True
                cns_child.use_rotation_y = True
                cns_child.use_rotation_z = True
                
                # Set widget directly on bone with translation to position at head
                bone.custom_shape = get_widget('WGT-CarRig.DoorTrunk')
                bone.custom_shape_scale_xyz = (0.2, 0.2, 0.2)  # Smaller circle
                # Translate widget from tail to head (in bone's local space, head is at +1.0 along bone length)
                bone_length = bone.length
                bone.custom_shape_translation = (0, bone_length, 0)  # Move widget to head position
                bone.lock_location = (True, True, True)
                bone.lock_rotation = (False, True, True)  # Only X rotation allowed
                bone.lock_scale = (True, True, True)

    def generate_ground_projection_constraint(self, bone):
        cns = bone.constraints.new('SHRINKWRAP')
        cns.name = 'Ground projection'
        cns.shrinkwrap_type = 'NEAREST_SURFACE'
        cns.project_axis_space = 'LOCAL'
        cns.project_axis = 'NEG_Z'
        cns.distance = abs(bone.head.z)

    def generate_childof_constraint(self, child, parent):
        cns = child.constraints.new('CHILD_OF')
        cns.target = self.ob
        cns.subtarget = parent.name
        cns.inverse_matrix = self.ob.data.bones[parent.name].matrix_local.inverted()
        cns.use_location_x = True
        cns.use_location_y = True
        cns.use_location_z = True
        cns.use_rotation_x = True
        cns.use_rotation_y = True
        cns.use_rotation_z = True
        return cns

    def generate_constraints_on_axle_bones(self, position):
        pose = self.ob.pose

        # Convert position: 'Ft' -> 'F', 'Bk' -> 'B'
        pos_abbr = 'F' if position == 'Ft' else 'B'
        subtarget = f'MCH_Axis_{pos_abbr}'
        if subtarget in pose.bones:
            mch_suspension = pose.bones[f'MCH_Suspension_{pos_abbr}']
            cns = mch_suspension.constraints.new('COPY_LOCATION')
            cns.name = 'Location from %s' % subtarget
            cns.target = self.ob
            cns.subtarget = subtarget
            cns.head_tail = .5
            cns.use_x = False
            cns.use_y = False
            cns.use_z = True
            cns.owner_space = 'WORLD'
            cns.target_space = 'WORLD'
            create_constraint_influence_driver(self.ob, cns, '["tq_SuspensionFactor"]')

            if position == 'Ft':
                cns = mch_suspension.constraints.new('DAMPED_TRACK')
                cns.name = 'Track suspension back'
                cns.target = self.ob
                cns.subtarget = 'MCH_Suspension_B'
                cns.track_axis = 'TRACK_Y'

        mch_axis = pose.bones.get(f'MCH_Axis_{pos_abbr}')
        if mch_axis is not None:
            # Find the right and left wheel dimensions for this position
            right_wheel = None
            left_wheel = None
            for wheel_dim in self.dimension.wheels_dimensions:
                if wheel_dim.position == position:
                    if wheel_dim.side_position == 'R':
                        right_wheel = wheel_dim
                    elif wheel_dim.side_position == 'L':
                        left_wheel = wheel_dim
            
            if right_wheel:
                cns = mch_axis.constraints.new('COPY_LOCATION')
                cns.name = 'Copy location from right wheel'
                cns.target = self.ob
                cns.subtarget = right_wheel.name('MCH_Damper')
                cns.use_x = True
                cns.use_y = True
                cns.use_z = True
                cns.owner_space = 'WORLD'
                cns.target_space = 'WORLD'

            if left_wheel:
                mch_axis = pose.bones[f'MCH_Axis_{pos_abbr}']
                cns = mch_axis.constraints.new('DAMPED_TRACK')
                cns.name = 'Track Left Wheel'
                cns.target = self.ob
                cns.subtarget = left_wheel.name('MCH_Damper')
                cns.track_axis = 'TRACK_Y'

    def generate_constraints_on_wheel_bones(self, name_suffix):
        pose = self.ob.pose

        def_wheel = pose.bones.get(name_suffix.name('DEF_Wheel'))
        if def_wheel is None:
            return

        cns = def_wheel.constraints.new('COPY_TRANSFORMS')
        cns.target = self.ob
        cns.subtarget = name_suffix.name('MCH_Wheel')

        def_wheel_brake = pose.bones.get(name_suffix.name('DEF_Brake'))
        if def_wheel_brake is not None:
            cns = def_wheel_brake.constraints.new('COPY_TRANSFORMS')
            cns.target = self.ob
            cns.subtarget = name_suffix.name('MCH_Brake')

        ground_sensor = pose.bones[name_suffix.name('GroundSensor')]
        ground_sensor.lock_location = (True, True, False)
        ground_sensor.lock_rotation = (True, True, True)
        ground_sensor.lock_rotation_w = True
        ground_sensor.lock_scale = (True, True, True)
        ground_sensor.custom_shape = get_widget('WGT-CarRig.GroundSensor')
        ground_sensor.custom_shape_transform = pose.bones['SHP_%s' % ground_sensor.name]
        ground_sensor.bone.show_wire = True

        if name_suffix.is_front:
            cns = ground_sensor.constraints.new('COPY_ROTATION')
            cns.name = 'Steering rotation'
            cns.target = self.ob
            cns.subtarget = 'MCH_Steering'
            cns.use_x = False
            cns.use_y = False
            cns.use_z = True
            cns.owner_space = 'LOCAL'
            cns.target_space = 'LOCAL'

        self.generate_ground_projection_constraint(ground_sensor)

        cns = ground_sensor.constraints.new('LIMIT_LOCATION')
        cns.name = 'Ground projection limitation'
        cns.use_transform_limit = True
        cns.owner_space = 'LOCAL'
        cns.use_max_x = True
        cns.use_min_x = True
        cns.min_x = 0
        cns.max_x = 0
        cns.use_max_y = True
        cns.use_min_y = True
        cns.min_y = 0
        cns.max_y = 0
        cns.use_max_z = True
        cns.use_min_z = True
        cns.min_z = -.2
        cns.max_z = .2

        wheel = pose.bones.get(name_suffix.name('Wheel'))
        wheel.rotation_mode = "XYZ"
        wheel.lock_location = (True, True, True)
        wheel.lock_rotation = (False, True, True)
        wheel.lock_scale = (True, True, True)
        wheel.custom_shape = get_widget('WGT-CarRig.Wheel')
        wheel.bone.show_wire = True

        wheel_brake = pose.bones.get(name_suffix.name('Brake'))
        if wheel_brake:
            generate_constraint_on_wheel_brake_bone(wheel_brake, wheel)

        mch_wheel = pose.bones[name_suffix.name('MCH_Wheel')]
        mch_wheel.rotation_mode = "XYZ"

        cns = mch_wheel.constraints.new('COPY_ROTATION')
        cns.name = 'Bake animation wheels'
        cns.target = self.ob
        cns.subtarget = name_suffix.name('MCH_WheelRotation')
        cns.use_x = True
        cns.use_y = False
        cns.use_z = False
        cns.use_offset = False
        cns.owner_space = 'POSE'
        cns.target_space = 'POSE'

        cns = mch_wheel.constraints.new('TRANSFORM')
        cns.name = 'Wheel rotation along Y axis'
        cns.target = self.ob
        cns.subtarget = 'Root'
        cns.use_motion_extrapolate = True
        cns.map_from = 'LOCATION'
        cns.from_min_y = - math.pi * abs(mch_wheel.head.z if mch_wheel.head.z != 0 else 1)
        cns.from_max_y = - cns.from_min_y
        cns.map_to_x_from = 'Y'
        cns.map_to = 'ROTATION'
        cns.to_min_x_rot = math.pi
        cns.to_max_x_rot = -math.pi
        cns.owner_space = 'LOCAL'
        cns.target_space = 'LOCAL'

        create_constraint_influence_driver(self.ob, cns, '["tq_WheelsYRolling"]')

        cns = mch_wheel.constraints.new('COPY_ROTATION')
        cns.name = 'Animation wheels'
        cns.target = self.ob
        cns.subtarget = wheel.name
        cns.use_x = True
        cns.use_y = False
        cns.use_z = False
        cns.use_offset = True
        cns.owner_space = 'LOCAL'
        cns.target_space = 'LOCAL'

        mch_wheel_rotation = pose.bones[name_suffix.name('MCH_WheelRotation')]
        mch_wheel_rotation.rotation_mode = "XYZ"
        self.generate_childof_constraint(mch_wheel_rotation, ground_sensor)
        wheel_prop_name = f'tq_WheelRotation_{name_suffix.value}'
        create_rotation_euler_x_driver(self.ob, mch_wheel_rotation, f'["{wheel_prop_name}"]')

    def generate_constraints_on_wheel_damper(self, wheel_dimension):
        pose = self.ob.pose

        wheel_damper = pose.bones.get(wheel_dimension.name('Damper'))
        if wheel_damper is not None:
            wheel_damper.lock_location = (True, True, False)
            wheel_damper.lock_rotation = (True, True, True)
            wheel_damper.lock_rotation_w = True
            wheel_damper.lock_scale = (True, True, True)
            wheel_damper.custom_shape = get_widget('WGT-CarRig.WheelDamper')
            wheel_damper.bone.show_wire = True

        mch_wheel_damper = pose.bones.get(wheel_dimension.name('MCH_Damper'))
        if mch_wheel_damper is not None:
            mch_wheel_damper.lock_location = (True, True, False)
            mch_wheel_damper.lock_rotation = (True, True, True)
            mch_wheel_damper.lock_rotation_w = True
            mch_wheel_damper.lock_scale = (True, True, True)
            mch_wheel_damper.bone.show_wire = True

        mch_ground_sensor = pose.bones.get(wheel_dimension.name('MCH_GroundSensor'))
        if mch_ground_sensor is not None:
            fcurve = mch_ground_sensor.driver_add('location', 2)
            drv = fcurve.driver
            drv.type = 'MAX'

            for i, ground_sensor_name in enumerate(wheel_dimension.names('GroundSensor')):
                if ground_sensor_name in pose.bones:
                    var = drv.variables.new()
                    var.name = 'groundSensor%03d' % i
                    var.type = 'TRANSFORMS'

                    targ = var.targets[0]
                    targ.id = self.ob
                    targ.bone_target = ground_sensor_name
                    targ.transform_space = 'LOCAL_SPACE'
                    targ.transform_type = 'LOC_Z'

    def generate_bone_groups(self):
        pose = self.ob.pose
        create_bone_group(pose, 'Direction', color_set='THEME04', bone_names=('Root', 'Drift', 'SHP_Root', 'SHP_Drift'))
        
        # Generate Damper bone names dynamically based on new naming convention
        wheel_damper_names = ['Suspension']
        for wheel_dimension in self.dimension.wheels_dimensions:
            wheel_damper_name = wheel_dimension.name('Damper')
            if wheel_damper_name:
                wheel_damper_names.append(wheel_damper_name)
        
        create_bone_group(pose, 'Suspension', color_set='THEME09', bone_names=tuple(wheel_damper_names))

        wheel_widgets = ('Steering',)
        for wheel_dimension in self.dimension.wheels_dimensions:
            wheel_widgets += tuple(wheel_dimension.names('Wheel'))
            wheel_widgets += tuple(wheel_dimension.names('Brake'))
        create_bone_group(pose, 'Wheels', color_set='THEME03', bone_names=wheel_widgets)

        ground_sensor_names = (
            'GroundSensor_Axle_F', 'GroundSensor_Axle_B', 'SHP_GroundSensor_Axle_F', 'SHP_GroundSensor_Axle_B')
        for wheel_dimension in self.dimension.wheels_dimensions:
            ground_sensor_names += tuple(wheel_dimension.names('GroundSensor'))
        ground_sensor_names += tuple("SHP_%s" % i for i in ground_sensor_names)
        create_bone_group(pose, 'GroundSensor', color_set='THEME02', bone_names=ground_sensor_names)
        
        # DoorTrunk bone group - for door and trunk control bones (if they exist)
        # Traffiq vehicles may have Door_FL, Door_FR, Trunk, Hood bones
        door_trunk_names = []
        for bone in pose.bones:
            if any(keyword in bone.name for keyword in ['Door', 'Trunk', 'Hood', 'Tailgate', 'Hatch']):
                if not bone.name.startswith(('DEF_', 'MCH_', 'SHP_')):
                    door_trunk_names.append(bone.name)
        
        if door_trunk_names:
            create_bone_group(pose, 'DoorTrunk', color_set='THEME01', bone_names=tuple(door_trunk_names))

    def set_origin(self, scene):
        object_location = self.ob.location[:]
        shp_root = self.ob.data.bones.get('SHP_Root')
        if shp_root:
            cursor_location = scene.cursor.location[:]
            scene.cursor.location = shp_root.head
            try:
                bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
            finally:
                scene.cursor.location = cursor_location
                self.ob.location = object_location


class OBJECT_OT_armatureCarDeformationRig(bpy.types.Operator):
    bl_idname = "object.armature_car_deformation_rig"
    bl_label = "Add car deformation rig"
    bl_description = "Creates the base rig for a car."
    bl_options = {'REGISTER', 'UNDO'}

    body_pos_delta: bpy.props.FloatVectorProperty(name='Delta Location',
                                                  description='Extra translation added to location of the car body',
                                                  size=3,
                                                  default=(0, 0, 0),
                                                  subtype='TRANSLATION')

    nb_front_wheels_pairs: bpy.props.IntProperty(name='Pairs',
                                                 description='Number of front wheels pairs',
                                                 default=1,
                                                 min=0)

    front_wheel_pos_delta: bpy.props.FloatVectorProperty(name='Delta Location',
                                                         description='Extra translation added to location of the front wheels',
                                                         size=3,
                                                         default=(0, 0, 0),
                                                         subtype='TRANSLATION')

    nb_back_wheels_pairs: bpy.props.IntProperty(name='Pairs',
                                                description='Number of back wheels pairs',
                                                default=1,
                                                min=0)

    back_wheel_pos_delta: bpy.props.FloatVectorProperty(name='Delta Location',
                                                        description='Extra translation added to location of the back wheels',
                                                        size=3,
                                                        default=(0, 0, 0),
                                                        subtype='TRANSLATION')

    nb_front_wheel_brakes_pairs: bpy.props.IntProperty(name='Front Pairs',
                                                       description='Number of front wheel brakes pairs',
                                                       default=0,
                                                       min=0)

    front_wheel_brakes_pos_delta: bpy.props.FloatProperty(name='Front Delta Location',
                                                          description='Extra translation added to location of the front brakes',
                                                          default=0)

    nb_back_wheel_brakes_pairs: bpy.props.IntProperty(name='Back Pairs',
                                                      description='Number of back wheel brakes pairs',
                                                      default=0,
                                                      min=0)

    back_wheel_brakes_pos_delta: bpy.props.FloatProperty(name='Back Delta Location',
                                                         description='Extra translation added to location of the back brakes',
                                                         default=0)

    def draw(self, context):
        self.layout.use_property_split = True
        self.layout.use_property_decorate = False
        self.layout.label(text='Body')
        layout = self.layout.box()
        layout.prop(self, 'body_pos_delta')
        self.layout.label(text='Front wheels')
        layout = self.layout.box()
        layout.prop(self, 'nb_front_wheels_pairs')
        layout.prop(self, 'front_wheel_pos_delta')
        self.layout.label(text='Back wheels')
        layout = self.layout.box()
        layout.prop(self, 'nb_back_wheels_pairs')
        layout.prop(self, 'back_wheel_pos_delta')
        self.layout.label(text='Brakes')
        layout = self.layout.box()
        layout.prop(self, 'nb_front_wheel_brakes_pairs')
        layout.prop(self, 'front_wheel_brakes_pos_delta')
        layout.prop(self, 'nb_back_wheel_brakes_pairs')
        layout.prop(self, 'back_wheel_brakes_pos_delta')

    def invoke(self, context, event):
        self.bones_position = {
            'Body': mathutils.Vector((0.0, 0, .8)),
            'Wheel_FL_0': mathutils.Vector((0.9, -2, .5)),
            'Wheel_FR_0': mathutils.Vector((-.9, -2, .5)),
            'Wheel_BL_0': mathutils.Vector((0.9, 2, .5)),
            'Wheel_BR_0': mathutils.Vector((-.9, 2, .5)),
            'Brake_FL_0': mathutils.Vector((0.9, -2, .5)),
            'Brake_FR_0': mathutils.Vector((-.9, -2, .5)),
            'Brake_BL_0': mathutils.Vector((0.9, 2, .5)),
            'Brake_BR_0': mathutils.Vector((-.9, 2, .5))
        }
        self.target_objects_name = {}

        has_body_target = self._find_target_object(context, 'Body')

        nb_wheels_ft_l = self._find_target_object_for_wheels(context, 'Wheel_FL_0')
        nb_wheels_ft_r = self._find_target_object_for_wheels(context, 'Wheel_FR_0')
        nb_wheels_bk_l = self._find_target_object_for_wheels(context, 'Wheel_BL_0')
        nb_wheels_bk_r = self._find_target_object_for_wheels(context, 'Wheel_BR_0')

        nb_wheel_brakes_ft_l = self._find_target_object_for_wheels(context, 'Brake_FL_0')
        nb_wheel_brakes_ft_r = self._find_target_object_for_wheels(context, 'Brake_FR_0')
        nb_wheel_brakes_bk_l = self._find_target_object_for_wheels(context, 'Brake_BL_0')
        nb_wheel_brakes_bk_r = self._find_target_object_for_wheels(context, 'Brake_BR_0')

        # Find door and trunk meshes (supports multiple: Door_FL_0, Door_FL_1, etc.)
        nb_doors_fl = self._find_target_object_for_wheels(context, 'Door_FL_0')
        nb_doors_fr = self._find_target_object_for_wheels(context, 'Door_FR_0')
        nb_doors_bl = self._find_target_object_for_wheels(context, 'Door_BL_0')
        nb_doors_br = self._find_target_object_for_wheels(context, 'Door_BR_0')
        nb_trunks_f = self._find_target_object_for_wheels(context, 'Trunk_F_0')
        nb_trunks_b = self._find_target_object_for_wheels(context, 'Trunk_B_0')

        self.nb_front_wheels_pairs = max(nb_wheels_ft_l, nb_wheels_ft_r)
        self.nb_back_wheels_pairs = max(nb_wheels_bk_l, nb_wheels_bk_r)
        self.nb_front_wheel_brakes_pairs = max(nb_wheel_brakes_ft_l, nb_wheel_brakes_ft_r)
        self.nb_back_wheel_brakes_pairs = max(nb_wheel_brakes_bk_l, nb_wheel_brakes_bk_r)

        # if no target object has been found for body, we assume it may have no
        # target object for front and back wheels either.
        if not has_body_target:
            self.nb_front_wheels_pairs = max(1, self.nb_front_wheels_pairs)
            self.nb_back_wheels_pairs = max(1, self.nb_back_wheels_pairs)

        return self.execute(context)

    def _find_target_object_for_wheels(self, context, suffix_name):
        for count, name in enumerate(name_range(suffix_name)):
            if not self._find_target_object(context, name):
                return count

    def _find_target_object(self, context, name):
        # Match object names that use underscores (new Traffiq format)
        # Allows for minor variations in naming but prioritizes underscore format
        # Also matches with prefix (e.g., "car_Door_FL_0") or suffix variations
        escaped_name = re.escape(name).replace(r'\.', '_')
        # Pattern matches: prefix_name, name_suffix, or exact name (case insensitive)
        pattern = re.compile(f"^.*{escaped_name}.*$", re.IGNORECASE)
        
        for obj in context.selected_objects:
            if obj.type == 'MESH' and pattern.match(obj.name):
                self.target_objects_name[name] = obj.name
                self.bones_position[name] = obj.location.copy()
                print(f"Found mesh '{obj.name}' for bone '{name}'")
                return True
        return False

    def execute(self, context):
        """Creates the meta rig with basic bones"""
        # Determine rig name based on body mesh name (exclude "_Body" suffix)
        body_obj_name = self.target_objects_name.get('Body', 'Car')
        rig_name = body_obj_name.replace('_Body', '') if body_obj_name.endswith('_Body') else body_obj_name
        
        amt = bpy.data.armatures.new(f'{rig_name}')
        amt['Car Rig'] = False

        rig = bpy_extras.object_utils.object_data_add(context, amt, name=rig_name)
        
        # Ensure the rig object is active and in the correct context
        context.view_layer.objects.active = rig
        rig.select_set(True)

        # TODO: cannot edit new object added to a hidden collection
        # Could be a better fix (steal code from other addons).
        try:
            bpy.ops.object.mode_set(mode='EDIT')
        except (TypeError, RuntimeError) as e:
            self.report({'ERROR'},
                        f"Cannot edit the new armature! {str(e)} Please make sure the active collection is visible and editable")
            return {'CANCELLED'}

        self._create_bone(rig, 'Body', delta_pos=self.body_pos_delta)

        self._create_wheel_bones(rig, 'Wheel_FL_0', self.nb_front_wheels_pairs, self.front_wheel_pos_delta)
        self._create_wheel_bones(rig, 'Wheel_FR_0', self.nb_front_wheels_pairs,
                                 self.front_wheel_pos_delta.reflect(mathutils.Vector((1, 0, 0))))
        self._create_wheel_bones(rig, 'Wheel_BL_0', self.nb_back_wheels_pairs, self.back_wheel_pos_delta)
        self._create_wheel_bones(rig, 'Wheel_BR_0', self.nb_back_wheels_pairs,
                                 self.back_wheel_pos_delta.reflect(mathutils.Vector((1, 0, 0))))

        front_wheel_brakes_delta_pos = self.front_wheel_pos_delta.copy()
        front_wheel_brakes_delta_pos.x = self.front_wheel_brakes_pos_delta
        self._create_wheel_bones(rig, 'Brake_FL_0', self.nb_front_wheel_brakes_pairs, front_wheel_brakes_delta_pos)
        self._create_wheel_bones(rig, 'Brake_FR_0', self.nb_front_wheel_brakes_pairs,
                                 front_wheel_brakes_delta_pos.reflect(mathutils.Vector((1, 0, 0))))
        back_wheel_brakes_delta_pos = self.back_wheel_pos_delta.copy()
        back_wheel_brakes_delta_pos.x = self.back_wheel_brakes_pos_delta
        self._create_wheel_bones(rig, 'Brake_BL_0', self.nb_back_wheel_brakes_pairs, back_wheel_brakes_delta_pos)
        self._create_wheel_bones(rig, 'Brake_BR_0', self.nb_back_wheel_brakes_pairs,
                                 back_wheel_brakes_delta_pos.reflect(mathutils.Vector((1, 0, 0))))

        deselect_edit_bones(rig)
        
        bpy.ops.object.mode_set(mode='OBJECT')
        
        # Parent all door and trunk meshes that were found (Door_FL_0, Door_FL_1, etc.)
        # Doors use armature modifier with vertex groups
        # Trunks use bone parenting to DEF_Body (like the reference traffiq file)
        for dt_name, target_obj_name in self.target_objects_name.items():
            if dt_name.startswith('Door_'):
                if target_obj_name in bpy.context.scene.objects:
                    target_obj = bpy.context.scene.objects[target_obj_name]
                    
                    # Parent to armature object (not bone-parented)
                    target_obj.parent = rig
                    target_obj.parent_type = 'OBJECT'
                    
                    # Add armature modifier if not present
                    has_armature_mod = any(mod.type == 'ARMATURE' for mod in target_obj.modifiers)
                    if not has_armature_mod:
                        arm_mod = target_obj.modifiers.new(name='Armature', type='ARMATURE')
                        arm_mod.object = rig
                        arm_mod.use_vertex_groups = True
                    
                    # Create vertex group for the door bone
                    if dt_name not in target_obj.vertex_groups:
                        vg = target_obj.vertex_groups.new(name=dt_name)
                        # Assign all vertices to this vertex group with full weight
                        vertex_indices = [v.index for v in target_obj.data.vertices]
                        vg.add(vertex_indices, 1.0, 'REPLACE')
                    
                    print(f"Parented {target_obj_name} to armature with vertex group {dt_name}")
            
            elif dt_name.startswith('Trunk_'):
                if target_obj_name in bpy.context.scene.objects:
                    target_obj = bpy.context.scene.objects[target_obj_name]
                    
                    # Bone-parent trunk mesh to DEF_Body (not the trunk bone itself)
                    # The trunk bone is parented to DEF_Body, so it moves with body
                    # The mesh also follows DEF_Body, and can be rotated by the trunk bone
                    target_obj.parent = rig
                    target_obj.parent_bone = 'DEF_Body'
                    target_obj.parent_type = 'BONE'
                    
                    print(f"Bone-parented {target_obj_name} to DEF_Body")
            
            elif dt_name == 'Body' or dt_name.startswith(('Wheel_', 'Brake_')):
                if target_obj_name in bpy.context.scene.objects:
                    target_obj = bpy.context.scene.objects[target_obj_name]
                    target_obj.parent = rig
                    target_obj.parent_bone = 'DEF_' + dt_name
                    target_obj.parent_type = 'BONE'
                    bone = rig.data.bones['DEF_' + dt_name]
                    target_obj.matrix_parent_inverse = (rig.matrix_world @ mathutils.Matrix.Translation(bone.tail_local)).inverted()
                    print(f"Bone-parented {target_obj_name} to DEF_{dt_name}")

        return {'FINISHED'}

    def _create_bone(self, rig, name, delta_pos):
        b = rig.data.edit_bones.new('DEF_' + name)

        if name == 'Body':
            # Position DEF_Body at origin for smart placement
            b.head = mathutils.Vector((0, 0, 0))
            b.tail = mathutils.Vector((0, 1, 0))
        else:
            b.head = self.bones_position[name] + delta_pos
            b.tail = b.head
            b.tail.y += b.tail.z

        target_obj_name = self.target_objects_name.get(name)
        if target_obj_name is not None and target_obj_name in bpy.context.scene.objects:
            target_obj = bpy.context.scene.objects[target_obj_name]
            if name == 'Body':
                b.tail = b.head
                b.tail.y += target_obj.dimensions[1] / 2 if target_obj.dimensions and target_obj.dimensions[
                    0] != 0 else 1
                # Adjust mesh position to stay in place since DEF_Body is at origin
                original_mesh_pos = self.bones_position[name] + delta_pos
                target_obj.location = original_mesh_pos
            # Parenting will be done after mode_set to OBJECT

        return b

    def _create_wheel_bones(self, rig, base_wheel_name, nb_wheels, delta_pos):
        previous_wheel_default_pos = self.bones_position[base_wheel_name]
        for wheel_name in name_range(base_wheel_name, nb_wheels):
            if wheel_name not in self.bones_position:
                wheel_position = previous_wheel_default_pos.copy()
                wheel_position.y += abs(previous_wheel.head.z * 2.2)
                self.bones_position[wheel_name] = wheel_position
            previous_wheel = self._create_bone(rig, wheel_name, delta_pos)
            previous_wheel_default_pos = self.bones_position[wheel_name]


class POSE_OT_carAnimationRigGenerate(bpy.types.Operator):
    bl_idname = "pose.car_animation_rig_generate"
    bl_label = "Generate car animation rig"
    bl_description = "Creates the complete armature for animating the car."
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.object is not None and context.object.data is not None and 'Car Rig' in context.object.data

    def execute(self, context):
        if context.object.data['Car Rig']:
            self.report({'INFO'}, 'Rig already generated')
            return {"CANCELLED"}

        if 'DEF_Body' not in context.object.data.bones:
            self.report({'ERROR'}, 'No bone named DEF_Body. This is not a valid armature!')
            return {"CANCELLED"}

        armature_generator = ArmatureGenerator(context.object)
        armature_generator.generate(context.scene, context.scene.tq_adjust_origin)
        return {"FINISHED"}


class POSE_OT_carAnimationAddBrakeWheelBones(bpy.types.Operator):
    bl_idname = "pose.car_animation_add_brake_wheel_bones"
    bl_label = "Add missing brake wheel bones"
    bl_description = "Generates missing brake wheel bones for each selected wheel widget."
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.object is not None and context.object.mode == 'POSE' and \
            context.object.data is not None and \
            context.object.data.get('Car Rig')

    def execute(self, context):
        mode = context.object.mode
        # Match new naming: Wheel_FR_0, Wheel_FL_1, Wheel_BR_2, etc.
        re_wheel_bone_name = re.compile(r'^Wheel_([FB])([LR])_(\d+)$')
        for pose_bone in context.selected_pose_bones:
            matcher = re_wheel_bone_name.match(pose_bone.name)
            if matcher:
                pos, side, idx = matcher.groups()
                brake_name = f'Brake_{pos}{side}_{idx}'
                parent_name = f'MCH_Wheel_{pos}{side}_{idx}'
                self.create_wheelbrake_bone(context, pose_bone, brake_name, parent_name)
        bpy.ops.object.mode_set(mode=mode)
        return {"FINISHED"}

    def create_wheelbrake_bone(self, context, wheel_pose_bone, name, parent_name):
        obj = context.object
        amt = context.object.data
        if name not in amt.bones and parent_name in amt.bones:
            bpy.ops.object.mode_set(mode='EDIT')
            create_wheel_brake_bone(amt.edit_bones.new(name), amt.edit_bones[parent_name],
                                    amt.edit_bones[wheel_pose_bone.name])
            bpy.ops.object.mode_set(mode='POSE')
            generate_constraint_on_wheel_brake_bone(obj.pose.bones[name], wheel_pose_bone)


class POSE_OT_carSetGround(bpy.types.Operator):
    bl_idname = "pose.car_set_ground"
    bl_label = "Set Ground for All Sensors"
    bl_description = "Set the ground object for all ground sensors"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.object is not None and context.object.mode == 'POSE' and \
            context.object.data is not None and \
            context.object.data.get('Car Rig')

    def execute(self, context):
        ground = context.scene.tq_ground_object
        if ground is None:
            self.report({'WARNING'}, "No ground object set")
            return {"CANCELLED"}
        for bone in enumerate_ground_sensors(context.object.pose.bones):
            cns = bone.constraints.get('Ground projection')
            if cns:
                cns.target = ground
        return {"FINISHED"}


class POSE_OT_carFollowPath(bpy.types.Operator):
    bl_idname = "pose.car_follow_path"
    bl_label = "Follow Path"
    bl_description = "Creates follow path animation with automatic ground sensors and baking"
    bl_options = {'REGISTER', 'UNDO'}

    CONSTRAINT_NAME = "tq_follow_path"

    animation_mode: bpy.props.EnumProperty(
        name="Animation Mode",
        description="Choose between frame-based or speed-based animation",
        items=[
            ('FRAMES', "Frame Range", "Define animation using start and end frames"),
            ('SPEED', "Speed (km/h)", "Define animation using speed in kilometers per hour")
        ],
        default='FRAMES'
    )
    frame_start: bpy.props.IntProperty(
        name="Start Frame",
        description="Frame where the animation starts",
        min=1,
        default=1
    )
    frame_end: bpy.props.IntProperty(
        name="End Frame",
        description="Frame where the animation ends",
        min=1,
        default=240
    )
    speed_kmh: bpy.props.FloatProperty(
        name="Speed (km/h)",
        description="Speed of the car in kilometers per hour",
        min=0.1,
        max=500.0,
        default=50.0,
        precision=1
    )
    auto_bake_steering: bpy.props.BoolProperty(
        name="Bake Steering",
        description="Automatically bake steering animation",
        default=True
    )
    auto_bake_drift: bpy.props.BoolProperty(
        name="Bake Drift",
        description="Automatically bake drift animation",
        default=False
    )
    auto_bake_wheels: bpy.props.BoolProperty(
        name="Bake Wheel Rotation",
        description="Automatically bake wheel rotation",
        default=True
    )
    auto_reset_transforms: bpy.props.BoolProperty(
        name="Reset Transforms",
        description="Reset transforms of car, curve, and ground for proper animation",
        default=True
    )
    clear_bake: bpy.props.BoolProperty(
        name="Clear Bake and Animation",
        description="Clear all existing steering, drift, and wheel rotation animations before setting up follow path",
        default=True
    )

    @classmethod
    def poll(cls, context):
        return (context.object is not None and 
                context.object.mode in ('POSE', 'OBJECT') and
                context.object.data is not None and
                context.object.data.get('Car Rig'))

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        
        layout.label(text="Animation Mode:", icon='TIME')
        layout.prop(self, "animation_mode", text="")
        layout.separator()
        
        if self.animation_mode == 'FRAMES':
            layout.label(text="Frame Range:", icon='KEYFRAME')
            layout.prop(self, "frame_start")
            layout.prop(self, "frame_end")
        else:  # SPEED mode
            layout.label(text="Speed Settings:", icon='DRIVER')
            layout.prop(self, "speed_kmh")
            layout.prop(self, "frame_start", text="Start Frame")
            
            # Show calculated end frame
            curve = context.scene.tq_target_path_object
            if curve and curve.type == 'CURVE':
                curve_length = self.get_curve_length(curve)
                fps = context.scene.render.fps
                calculated_end = self.calculate_end_frame_from_speed(
                    self.frame_start, curve_length, self.speed_kmh, fps
                )
                box = layout.box()
                box.label(text=f"Curve Length: {curve_length:.2f} m")
                box.label(text=f"Calculated End Frame: {calculated_end}")
            else:
                layout.label(text="No valid curve selected", icon='ERROR')
        
        layout.separator()
        layout.label(text="Animation Setup:", icon='ANIM')
        layout.prop(self, "auto_bake_steering")
        layout.prop(self, "auto_bake_drift")
        layout.prop(self, "auto_bake_wheels")
        layout.prop(self, "auto_reset_transforms")
        layout.separator()
        layout.label(text="Cleanup:", icon='TRASH')
        layout.prop(self, "clear_bake")
        col = layout.column(align=True)
        col.alert = True
        if self.auto_reset_transforms:
            col.label(text="Warning: Asset transforms will be reset!")
        else:
            col.label(text="Make sure assets have valid transforms!")

    def execute(self, context):
        curve = context.scene.tq_target_path_object
        if curve is None:
            self.report({'ERROR'}, "No target path selected!")
            return {'CANCELLED'}
        
        if curve.type != 'CURVE':
            self.report({'ERROR'}, "Target path must be a curve object!")
            return {'CANCELLED'}

        # Calculate frame_end based on animation mode
        if self.animation_mode == 'SPEED':
            curve_length = self.get_curve_length(curve)
            fps = context.scene.render.fps
            self.frame_end = self.calculate_end_frame_from_speed(
                self.frame_start, curve_length, self.speed_kmh, fps
            )
            self.report({'INFO'}, f"Curve length: {curve_length:.2f}m, End frame: {self.frame_end} (Speed: {self.speed_kmh} km/h)")

        # Switch to POSE mode if needed
        if context.object.mode != 'POSE':
            bpy.ops.object.mode_set(mode='POSE')

        active_object = context.object
        root_bone = active_object.pose.bones.get('Root')
        if root_bone is None:
            self.report({'ERROR'}, f"Could not find root bone in {active_object.name}")
            return {'CANCELLED'}

        # Setup follow path constraint
        follow_path_constraint = self.setup_follow_path_constraint(root_bone, curve)

        # Reset transforms if requested
        ground_object = context.scene.tq_ground_object
        if self.auto_reset_transforms:
            self.reset_transforms(active_object, curve, ground_object)

        # Create animation data if needed
        if active_object.animation_data is None:
            active_object.animation_data_create()
        if active_object.animation_data.action is None:
            active_object.animation_data.action = bpy.data.actions.new(
                f"{active_object.name}_Action"
            )

        # Create keyframes for follow path constraint offset_factor
        # This drives the car along the curve
        offset_factor_data_path = self.get_offset_data_path(
            root_bone.name, follow_path_constraint.name
        )

        # Ensure the scene playback range includes the requested frames
        scene = context.scene
        if self.frame_start < scene.frame_start:
            scene.frame_start = self.frame_start
        if self.frame_end > scene.frame_end:
            scene.frame_end = self.frame_end

        # Drive the follow-path factor from 1 -> 0 across the chosen frame range
        follow_path_constraint.offset_factor = 1.0
        active_object.keyframe_insert(offset_factor_data_path, frame=self.frame_start)

        follow_path_constraint.offset_factor = 0.0
        active_object.keyframe_insert(offset_factor_data_path, frame=self.frame_end)

        # (No manual baking of Root required) The wheel baker will use baked visual
        # transforms of wheel bones (via bake_action) to compute wheel rotation.

        # Setup ground sensors
        if ground_object is not None:
            for bone in enumerate_ground_sensors(active_object.pose.bones):
                cns = bone.constraints.get('Ground projection')
                if cns:
                    cns.target = ground_object
                    cns.shrinkwrap_type = 'PROJECT'
        # Clear any previously generated steering/wheel animations if requested
        if self.clear_bake:
            try:
                from . import bake_operators
                clearer = bake_operators.ANIM_OT_carClearSteeringWheelsRotation()
                clearer.clear_steering = True
                clearer.clear_drift = True
                clearer.clear_wheels = True
                clearer.execute(context)
            except Exception as e:
                self.report({'WARNING'}, f"Clearing previous baked animations failed: {str(e)}")

        # Store frame range for chained baking operations
        context.scene.tq_follow_path_frame_start = self.frame_start
        context.scene.tq_follow_path_frame_end = self.frame_end
        context.scene.tq_follow_path_bake_wheels = self.auto_bake_wheels

        # Chain to steering bake dialog if requested
        if self.auto_bake_steering:
            return bpy.ops.anim.car_steering_bake('INVOKE_DEFAULT')
        
        # Chain to drift bake dialog if requested
        elif self.auto_bake_drift:
            return bpy.ops.anim.car_drift_bake('INVOKE_DEFAULT')
        
        # Chain to wheel rotation bake dialog if requested
        elif self.auto_bake_wheels:
            return bpy.ops.anim.car_wheels_rotation_bake('INVOKE_DEFAULT')
        
        # Return to OBJECT mode and finish
        bpy.ops.object.mode_set(mode='OBJECT')
        self.report({'INFO'}, f"Follow path animation created for {active_object.name}")
        return {'FINISHED'}
        return {'FINISHED'}

    def _bake_follow_path_constraint_to_keyframes(self, context, armature, root_bone, frame_start, frame_end):
        """Extract the follow path constraint's evaluated location into explicit keyframes.
        
        The follow path constraint drives both location and rotation naturally.
        We need explicit location keyframes in the action so the wheel baking algorithm
        can read the actual motion (ignoring rotation).
        """
        # Get the action
        if not armature.animation_data or not armature.animation_data.action:
            return
        
        action = armature.animation_data.action
        
        # Ensure we're in POSE mode for keyframing
        if context.object.mode != 'POSE':
            bpy.ops.object.mode_set(mode='POSE')
        
        # For each frame, read the constraint-evaluated position and store it
        for frame in range(frame_start, frame_end + 1):
            context.scene.frame_set(frame)
            
            # Get the Root bone's actual world location (driven by follow path constraint)
            world_location = root_bone.matrix.translation.copy()
            
            # Convert to armature-local space
            armature_location = armature.matrix_world.inverted() @ world_location
            
            # Set the location to what the constraint calculated
            root_bone.location = armature_location
            
            # Insert location keyframe (this overwrites any previous ones)
            root_bone.keyframe_insert('location', frame=frame)

    def _bake_wheels_rotation_direct(self, context, frame_start, frame_end):
        """Bake wheel rotation without opening operator dialogs"""
        from . import bake_operators
        
        baker = bake_operators.ANIM_OT_carWheelsRotationBake()
        baker.frame_start = frame_start
        baker.frame_end = frame_end
        baker.keyframe_tolerance = 0.01
        baker.report = self.report  # Pass our report method
        baker._bake_wheels_rotation(context)

    def _bake_steering_rotation_direct(self, context, frame_start, frame_end):
        """Bake steering rotation without opening operator dialogs"""
        from . import bake_operators
        
        steering_baker = bake_operators.ANIM_OT_carSteeringBake()
        steering_baker.frame_start = frame_start
        steering_baker.frame_end = frame_end
        steering_baker.rotation_factor = 1.0
        steering_baker.keyframe_tolerance = 0.01
        steering_baker.report = self.report  # Pass our report method
        
        active_object = context.object
        # Get steering bone and calculate offset
        if ('Steering' in active_object.data.bones and 
            'MCH_SteeringRotation' in active_object.data.bones):
            steering = active_object.data.bones['Steering']
            mch_steering_rotation = active_object.data.bones['MCH_SteeringRotation']
            bone_offset = abs(steering.head_local.y - mch_steering_rotation.head_local.y)
            steering_baker._bake_steering_rotation(context, bone_offset, mch_steering_rotation)

    @staticmethod
    def get_offset_data_path(root_bone_name, fp_constraint_name):
        return f'pose.bones["{root_bone_name}"].constraints["{fp_constraint_name}"].offset_factor'
    
    @staticmethod
    def get_curve_length(curve_object):
        """Calculate the total length of a curve object in Blender units (meters)."""
        if curve_object.type != 'CURVE':
            return 0.0
        
        total_length = 0.0
        for spline in curve_object.data.splines:
            # Calculate length by sampling points along the spline
            if spline.type == 'BEZIER':
                # For Bezier curves, approximate by summing bezier point distances
                # This is a simple approximation - for more accuracy, we'd need to sample the curve
                points = [bp.co for bp in spline.bezier_points]
                for i in range(len(points) - 1):
                    total_length += (points[i+1] - points[i]).length
                
                # Add closing segment if cyclic
                if spline.use_cyclic_u and len(points) > 1:
                    total_length += (points[0] - points[-1]).length
                    
            elif spline.type == 'NURBS':
                # For NURBS curves, use point distances
                points = [p.co.xyz for p in spline.points]
                for i in range(len(points) - 1):
                    total_length += (points[i+1] - points[i]).length
                
                # Add closing segment if cyclic
                if spline.use_cyclic_u and len(points) > 1:
                    total_length += (points[0] - points[-1]).length
                    
            elif spline.type == 'POLY':
                # For poly curves, use point distances
                points = [p.co.xyz for p in spline.points]
                for i in range(len(points) - 1):
                    total_length += (points[i+1] - points[i]).length
                
                # Add closing segment if cyclic
                if spline.use_cyclic_u and len(points) > 1:
                    total_length += (points[0] - points[-1]).length
        
        # Apply object scale
        scale = curve_object.matrix_world.to_scale()
        avg_scale = (scale.x + scale.y + scale.z) / 3.0
        
        return total_length * avg_scale
    
    @staticmethod
    def calculate_end_frame_from_speed(start_frame, curve_length_m, speed_kmh, fps):
        """Calculate end frame based on curve length and desired speed.
        
        Args:
            start_frame: Starting frame number
            curve_length_m: Length of curve in meters
            speed_kmh: Desired speed in kilometers per hour
            fps: Frames per second from scene settings
        
        Returns:
            Calculated end frame (int)
        """
        if speed_kmh <= 0:
            return start_frame + 240  # Default fallback
        
        # Convert km/h to m/s
        speed_ms = speed_kmh / 3.6
        
        # Calculate time in seconds to traverse the curve
        time_seconds = curve_length_m / speed_ms
        
        # Convert to frames
        duration_frames = int(time_seconds * fps)
        
        return start_frame + max(1, duration_frames)

    def setup_follow_path_constraint(self, root_bone, target_obj):
        follow_path_constraint = root_bone.constraints.get(self.CONSTRAINT_NAME)
        if follow_path_constraint is None:
            follow_path_constraint = root_bone.constraints.new(type='FOLLOW_PATH')
            follow_path_constraint.name = self.CONSTRAINT_NAME

        follow_path_constraint.target = target_obj
        follow_path_constraint.use_fixed_location = True
        follow_path_constraint.use_curve_follow = True  # RESTORED: Let constraint handle rotation naturally
        # Ensure object/bone forward aligns with curve tangent. Default rigs in this
        # project expect Y-forward and Z-up — set the constraint axes accordingly.
        try:
            follow_path_constraint.forward_axis = 'FORWARD_Y'
            follow_path_constraint.up_axis = 'UP_Z'
        except Exception:
            # Some Blender versions or constraint contexts may not expose these
            # enums on pose-bone constraints; ignore if unavailable.
            pass
        return follow_path_constraint

    def reset_transforms(self, owner, path, ground=None):
        owner.location = (0.0, 0.0, 0.0)
        owner.rotation_euler = (0.0, 0.0, 0.0)
        path.scale = (1.0, 1.0, 1.0)
        if ground is not None:
            ground.scale = (1.0, 1.0, 1.0)


class POSE_OT_carClearFollowPathAnimation(bpy.types.Operator):
    """Clear follow path animation and baked keyframes"""
    bl_idname = "pose.car_clear_follow_path_animation"
    bl_label = "Clear Follow Path Animation"
    bl_description = "Remove follow path animation, steering bakes, and wheel rotation bakes"
    bl_options = {'REGISTER', 'UNDO'}

    clear_follow_path: bpy.props.BoolProperty(
        name="Clear Follow Path Constraint",
        description="Remove the follow path constraint and its keyframes",
        default=True
    )
    clear_steering: bpy.props.BoolProperty(
        name="Clear Steering Animation",
        description="Remove all steering bake keyframes",
        default=True
    )
    clear_drift: bpy.props.BoolProperty(
        name="Clear Drift Animation",
        description="Remove all drift bake keyframes",
        default=True
    )
    clear_wheels: bpy.props.BoolProperty(
        name="Clear Wheel Rotation Animation",
        description="Remove all wheel rotation bake keyframes",
        default=True
    )

    @classmethod
    def poll(cls, context):
        return (context.object is not None and 
                context.object.mode in ('POSE', 'OBJECT') and
                context.object.data is not None and
                context.object.data.get('Car Rig'))

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        layout.label(text="Clear Animations:", icon='TRASH')
        layout.prop(self, "clear_follow_path")
        layout.prop(self, "clear_steering")
        layout.prop(self, "clear_drift")
        layout.prop(self, "clear_wheels")

    def execute(self, context):
        active_object = context.object
        
        # Switch to POSE mode if needed
        if context.object.mode != 'POSE':
            bpy.ops.object.mode_set(mode='POSE')

        # Clear follow path constraint and keyframes
        if self.clear_follow_path:
            root_bone = active_object.pose.bones.get('Root')
            if root_bone:
                # Remove follow path constraint
                fp_constraint = root_bone.constraints.get('tq_follow_path')
                if fp_constraint:
                    root_bone.constraints.remove(fp_constraint)
                    self.report({'INFO'}, "Removed follow path constraint")
                
                # Remove follow path keyframes
                if active_object.animation_data and active_object.animation_data.action:
                    action = active_object.animation_data.action
                    offset_factor_data_path = f'pose.bones["Root"].constraints["tq_follow_path"].offset_factor'
                    
                    # Find and remove the fcurve for follow path offset_factor
                    fcurve_to_remove = None
                    for fcurve in action.fcurves:
                        if fcurve.data_path == offset_factor_data_path:
                            fcurve_to_remove = fcurve
                            break
                    
                    if fcurve_to_remove:
                        action.fcurves.remove(fcurve_to_remove)
                        self.report({'INFO'}, "Removed follow path keyframes")

        # Clear steering animation
        if self.clear_steering:
            try:
                from . import bake_operators
                clearer = bake_operators.ANIM_OT_carClearSteeringWheelsRotation()
                clearer.clear_steering = True
                clearer.clear_drift = False
                clearer.clear_wheels = False
                clearer.execute(context)
                self.report({'INFO'}, "Cleared steering animation")
            except Exception as e:
                self.report({'WARNING'}, f"Failed to clear steering animation: {str(e)}")

        # Clear drift animation
        if self.clear_drift:
            try:
                from . import bake_operators
                clearer = bake_operators.ANIM_OT_carClearSteeringWheelsRotation()
                clearer.clear_steering = False
                clearer.clear_drift = True
                clearer.clear_wheels = False
                clearer.execute(context)
                self.report({'INFO'}, "Cleared drift animation")
            except Exception as e:
                self.report({'WARNING'}, f"Failed to clear drift animation: {str(e)}")

        # Clear wheel rotation animation
        if self.clear_wheels:
            try:
                from . import bake_operators
                clearer = bake_operators.ANIM_OT_carClearSteeringWheelsRotation()
                clearer.clear_steering = False
                clearer.clear_drift = False
                clearer.clear_wheels = True
                clearer.execute(context)
                self.report({'INFO'}, "Cleared wheel rotation animation")
            except Exception as e:
                self.report({'WARNING'}, f"Failed to clear wheel animation: {str(e)}")

        bpy.ops.object.mode_set(mode='OBJECT')
        self.report({'INFO'}, "Follow path animation cleared")
        return {'FINISHED'}


def register():
    bpy.utils.register_class(POSE_OT_carAnimationRigGenerate)
    bpy.utils.register_class(OBJECT_OT_armatureCarDeformationRig)
    bpy.utils.register_class(POSE_OT_carAnimationAddBrakeWheelBones)
    bpy.utils.register_class(POSE_OT_carSetGround)
    bpy.utils.register_class(POSE_OT_carFollowPath)
    bpy.utils.register_class(POSE_OT_carClearFollowPathAnimation)
    
    bpy.types.Scene.tq_target_path_object = bpy.props.PointerProperty(
        name="Follow Path Target",
        description="Path which rigged car should follow",
        poll=lambda self, obj: obj.type == 'CURVE',
        type=bpy.types.Object,
    )
    bpy.types.Scene.tq_ground_object = bpy.props.PointerProperty(
        name="Ground Object",
        description="Object representing the ground to be used in animation of rigged car",
        type=bpy.types.Object,
    )
    bpy.types.Scene.tq_adjust_origin = bpy.props.BoolProperty(
        name="Move Origin",
        description="Set origin of the armature at the same location as the SHP_Root bone",
        default=True
    )
    bpy.types.Scene.tq_follow_path_bake_wheels = bpy.props.BoolProperty(
        name="Follow Path Bake Wheels",
        description="Internal flag: whether to chain to wheel rotation baking after steering bake",
        default=False
    )
    bpy.types.Scene.tq_follow_path_frame_start = bpy.props.IntProperty(
        name="Follow Path Frame Start",
        description="Internal: Start frame for follow path animation from follow path operator",
        default=1
    )
    bpy.types.Scene.tq_follow_path_frame_end = bpy.props.IntProperty(
        name="Follow Path Frame End",
        description="Internal: End frame for follow path animation from follow path operator",
        default=240
    )


def unregister():
    # Safely delete Scene properties if they exist
    if hasattr(bpy.types.Scene, 'tq_follow_path_frame_end'):
        del bpy.types.Scene.tq_follow_path_frame_end
    if hasattr(bpy.types.Scene, 'tq_follow_path_frame_start'):
        del bpy.types.Scene.tq_follow_path_frame_start
    if hasattr(bpy.types.Scene, 'tq_follow_path_bake_wheels'):
        del bpy.types.Scene.tq_follow_path_bake_wheels
    if hasattr(bpy.types.Scene, 'tq_ground_object'):
        del bpy.types.Scene.tq_ground_object
    if hasattr(bpy.types.Scene, 'tq_adjust_origin'):
        del bpy.types.Scene.tq_adjust_origin
    if hasattr(bpy.types.Scene, 'tq_target_path_object'):
        del bpy.types.Scene.tq_target_path_object
    
    bpy.utils.unregister_class(POSE_OT_carClearFollowPathAnimation)
    bpy.utils.unregister_class(POSE_OT_carFollowPath)
    bpy.utils.unregister_class(POSE_OT_carSetGround)
    bpy.utils.unregister_class(POSE_OT_carAnimationAddBrakeWheelBones)
    bpy.utils.unregister_class(OBJECT_OT_armatureCarDeformationRig)
    bpy.utils.unregister_class(POSE_OT_carAnimationRigGenerate)


if __name__ == "__main__":
    register()
