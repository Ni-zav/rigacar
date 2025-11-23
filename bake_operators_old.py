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
import bpy_extras.anim_utils
import mathutils
import math
import itertools
import re
from math import inf


def cursor(cursor_mode):
    def cursor_decorator(func):
        def wrapper(self, context, *args, **kwargs):
            context.window.cursor_modal_set(cursor_mode)
            try:
                return func(self, context, *args, **kwargs)
            finally:
                context.window.cursor_modal_restore()

        return wrapper

    return cursor_decorator


def bone_name(prefix, position, side, index=0):
    """Generate bone name in new Traffiq format: Prefix_PositionSide_Index (e.g., Wheel_FR_0)"""
    # New format: position is already 'F' or 'B', side is 'L' or 'R'
    return f"{prefix}_{position}{side}_{index}"


def bone_range(bones, name_prefix, position, side):
    """Find all bones matching pattern Prefix_PositionSide_Index"""
    for index in itertools.count():
        name = bone_name(name_prefix, position, side, index)
        if name in bones:
            yield bones[name]
        else:
            break


def find_wheelbrake_bone(bones, position, side, index):
    """Find brake bone for wheel baking - returns Brake control bone or MCH_Brake if available"""
    other_side = 'R' if side == 'L' else 'L'
    
    # First try to find the Brake control bone (new format)
    name_prefix = 'Brake'
    bone = bones.get(bone_name(name_prefix, position, side, index))
    if bone:
        return bone
    bone = bones.get(bone_name(name_prefix, position, other_side, index))
    if bone:
        return bone
    
    # Fallback to MCH_Brake if Brake control bone doesn't exist
    name_prefix = 'MCH_Brake'
    bone = bones.get(bone_name(name_prefix, position, side, index))
    if bone:
        return bone
    bone = bones.get(bone_name(name_prefix, position, other_side, index))
    if bone:
        return bone
    
    # Legacy fallback
    if index > 0:
        bone = bones.get(bone_name('Brake', position, side, 0))
        if bone:
            return bone
        bone = bones.get(bone_name('Brake', position, other_side, 0))
        if bone:
            return bone
    
    # Very old backward compatibility
    backward_compatible_bone_name = '%s Wheels' % ('Front' if position == 'Ft' else 'Back')
    return bones.get(backward_compatible_bone_name)


def clear_property_animation(context, property_name, remove_keyframes=True):
    if remove_keyframes and context.object.animation_data and context.object.animation_data.action:
        fcurve_datapath = '["%s"]' % property_name
        action = context.object.animation_data.action
        fcurve = action.fcurves.find(fcurve_datapath)
        if fcurve is not None:
            action.fcurves.remove(fcurve)
    context.object[property_name] = .0


def create_property_animation(context, property_name):
    action = context.object.animation_data.action
    fcurve_datapath = '["%s"]' % property_name
    return action.fcurves.new(fcurve_datapath, index=0, action_group='Wheels rotation')


class FCurvesEvaluator(object):
    """Encapsulates a bunch of FCurves for vector animations."""

    def __init__(self, fcurves, default_value):
        self.default_value = default_value
        self.fcurves = fcurves

    def evaluate(self, f):
        result = []
        for fcurve, value in zip(self.fcurves, self.default_value):
            if fcurve is not None:
                result.append(fcurve.evaluate(f))
            else:
                result.append(value)
        return result


class VectorFCurvesEvaluator(object):

    def __init__(self, fcurves_evaluator):
        self.fcurves_evaluator = fcurves_evaluator

    def evaluate(self, f):
        return mathutils.Vector(self.fcurves_evaluator.evaluate(f))


class EulerToQuaternionFCurvesEvaluator(object):

    def __init__(self, fcurves_evaluator):
        self.fcurves_evaluator = fcurves_evaluator

    def evaluate(self, f):
        return mathutils.Euler(self.fcurves_evaluator.evaluate(f)).to_quaternion()


class QuaternionFCurvesEvaluator(object):

    def __init__(self, fcurves_evaluator):
        self.fcurves_evaluator = fcurves_evaluator

    def evaluate(self, f):
        return mathutils.Quaternion(self.fcurves_evaluator.evaluate(f))


def fix_old_steering_rotation(rig_object):
    """
    Fix armature generated with Rigacar version < 6.0
    """
    if rig_object.pose and rig_object.pose.bones:
        if 'MCH_SteeringRotation' in rig_object.pose.bones:
            rig_object.pose.bones['MCH_SteeringRotation'].rotation_mode = 'QUATERNION'


def serialize_bake_options():
    # For older versions than 4.1
    if bpy.app.version < (4, 1, 0):
        return dict(
            only_selected=True,
            do_pose=True,
            do_object=False,
            do_visual_keying=True
        )
    # For latest versions
    return dict(bake_options=bpy_extras.anim_utils.BakeOptions(
            only_selected=True,
            do_pose=True,
            do_object=False,
            do_visual_keying=True,
            do_constraint_clear=False,
            do_parents_clear=False,
            do_clean=False,
            do_location=True,
            do_scale=True,
            do_rotation=True,
            do_bbone=True,
            do_custom_props=True
        )
    )


class BakingOperator(object):
    frame_start: bpy.props.IntProperty(name='Start Frame', min=1)
    frame_end: bpy.props.IntProperty(name='End Frame', min=1)
    keyframe_tolerance: bpy.props.FloatProperty(name='Keyframe tolerance', min=0, default=.01)

    @classmethod
    def poll(cls, context):
        return (context.object is not None and
                context.object.data is not None and
                'Car Rig' in context.object.data and
                context.object.data.get('Car Rig') is not None and
                context.object.mode in ('POSE', 'OBJECT'))

    def invoke(self, context, event):
        try:
            if context.object.animation_data is None:
                context.object.animation_data_create()
            if context.object.animation_data.action is None:
                context.object.animation_data.action = bpy.data.actions.new("%sAction" % context.object.name)

            action = context.object.animation_data.action
            if action is None:
                self.report({'ERROR'}, "Failed to create or access animation action")
                return {'CANCELLED'}
            
            self.frame_start = int(action.frame_range[0])
            self.frame_end = int(action.frame_range[1])

            return context.window_manager.invoke_props_dialog(self)
        except Exception as e:
            self.report({'ERROR'}, f"Failed to initialize bake operator: {str(e)}")
            return {'CANCELLED'}

    def draw(self, context):
        self.layout.use_property_split = True
        self.layout.use_property_decorate = False
        self.layout.prop(self, 'frame_start')
        self.layout.prop(self, 'frame_end')
        self.layout.prop(self, 'keyframe_tolerance')

    def _create_euler_evaluator(self, action, source_bone):
        fcurve_name = 'pose.bones["%s"].rotation_euler' % source_bone.name
        fc_root_rot = [action.fcurves.find(fcurve_name, index=i) for i in range(3)]
        return EulerToQuaternionFCurvesEvaluator(FCurvesEvaluator(fc_root_rot, default_value=(.0, .0, .0)))

    def _create_quaternion_evaluator(self, action, source_bone):
        fcurve_name = 'pose.bones["%s"].rotation_quaternion' % source_bone.name
        fc_root_rot = [action.fcurves.find(fcurve_name, index=i) for i in range(4)]
        return QuaternionFCurvesEvaluator(FCurvesEvaluator(fc_root_rot, default_value=(1.0, .0, .0, .0)))

    def _create_location_evaluator(self, action, source_bone):
        fcurve_name = 'pose.bones["%s"].location' % source_bone.name
        fc_root_loc = [action.fcurves.find(fcurve_name, index=i) for i in range(3)]
        return VectorFCurvesEvaluator(FCurvesEvaluator(fc_root_loc, default_value=(.0, .0, .0)))

    def _create_scale_evaluator(self, action, source_bone):
        fcurve_name = 'pose.bones["%s"].scale' % source_bone.name
        fc_root_loc = [action.fcurves.find(fcurve_name, index=i) for i in range(3)]
        return VectorFCurvesEvaluator(FCurvesEvaluator(fc_root_loc, default_value=(1.0, 1.0, 1.0)))

    def _bake_action(self, context, *source_bones):
        action = context.object.animation_data.action
        nla_tweak_mode = context.object.animation_data.use_tweak_mode if hasattr(context.object.animation_data,
                                                                                 'use_tweak_mode') else False

        # saving context
        selected_bones = [b for b in context.object.data.bones if b.select]
        mode = context.object.mode
        source_bones_matrix_basis = []
        
        try:
            for b in selected_bones:
                b.select = False

            bpy.ops.object.mode_set(mode='OBJECT')
            for source_bone in source_bones:
                source_bones_matrix_basis.append(context.object.pose.bones[source_bone.name].matrix_basis.copy())
                source_bone.select = True

            bake_options = serialize_bake_options()
            baked_action = bpy_extras.anim_utils.bake_action(
                context.object,
                action=None,
                frames=range(self.frame_start, self.frame_end + 1),
                **bake_options
            )

            return baked_action
        finally:
            # restoring context - guaranteed to run even on exception
            try:
                for source_bone, matrix_basis in zip(source_bones, source_bones_matrix_basis):
                    context.object.pose.bones[source_bone.name].matrix_basis = matrix_basis
                    source_bone.select = False
                for b in selected_bones:
                    b.select = True

                bpy.ops.object.mode_set(mode=mode)

                if nla_tweak_mode:
                    context.object.animation_data.use_tweak_mode = nla_tweak_mode
                else:
                    context.object.animation_data.action = action
            except Exception as e:
                print(f"Warning: Failed to fully restore context: {str(e)}")


class ANIM_OT_carWheelsRotationBake(bpy.types.Operator, BakingOperator):
    bl_idname = 'anim.car_wheels_rotation_bake'
    bl_label = 'Bake wheels rotation'
    bl_description = 'Automatically generates wheels animation based on Root bone animation.'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        context.object['tq_WheelsYRolling'] = False
        self._bake_wheels_rotation(context)
        return {'FINISHED'}

    @cursor('WAIT')
    def _bake_wheels_rotation(self, context):
        bones = context.object.data.bones
        
        # Ensure the armature has an action to store properties in
        if context.object.animation_data is None or context.object.animation_data.action is None:
            self.report({'ERROR'}, "No animation action found on armature. Run Follow Path to create animation first.")
            return

        wheel_bones = []
        brake_bones = []
        
        # Find Wheel control bones (Wheel_FR_0, Wheel_BL_1, etc.)
        for position, side in itertools.product(('F', 'B'), ('L', 'R')):
            for index, wheel_bone in enumerate(bone_range(bones, 'Wheel', position, side)):
                wheel_bones.append(wheel_bone)
                brake_bones.append(find_wheelbrake_bone(bones, position, side, index) or wheel_bone)

        # Validate that wheel bones were found
        if not wheel_bones:
            self.report({'ERROR'}, "No Wheel control bones found. Rig may not be properly set up.")
            return

        # Clear existing wheel rotation animations - use consistent tq_ prefix
        for wheel_bone in wheel_bones:
            property_name = wheel_bone.name.replace('Wheel_', 'tq_WheelRotation_')
            clear_property_animation(context, property_name)

        self.report({'INFO'}, f"Found {len(wheel_bones)} wheel bones to bake")

        # CRITICAL: Bake the Wheel control bones (they have animation from rig constraints)
        baked_action = self._bake_action(context, *wheel_bones)

        if baked_action is None:
            self.report({'WARNING'}, "Failed to bake Wheel bones animation. Won't bake wheel rotation")
            return

        try:
            for wheel_bone, brake_bone in zip(wheel_bones, brake_bones):
                self._bake_wheel_rotation(context, baked_action, wheel_bone, brake_bone)
        finally:
            bpy.data.actions.remove(baked_action)

    def _evaluate_distance_per_frame(self, action, bone, brake_bone):
        """Evaluate wheel rotation distance for each frame.
        
        Returns (frame, cumulative_distance) tuples where distance is in radians.
        Uses tolerance to drop redundant keyframes (based on distance change, not speed).
        2π radians (6.28) = 1 full wheel rotation, π (3.14) = half rotation.
        """
        # Use Root bone's animated location (it moves with the car body during animation)
        # Root location directly represents how far the car has traveled
        reference_bone_name = 'Root'
        
        # Create a dummy bone object with Root's name for the location evaluator
        class DummyBone:
            def __init__(self, name):
                self.name = name
        
        reference_bone = DummyBone(reference_bone_name)
        reference_loc_evaluator = self._create_location_evaluator(action, reference_bone)
        rot_evaluator = self._create_euler_evaluator(action, bone)
        brake_evaluator = self._create_scale_evaluator(action, brake_bone)

        # Use wheel bone's length as the effective radius for rotation calculation
        radius = bone.length if bone.length > .0 else 1.0
        bone_init_vector = (bone.head_local - bone.tail_local).normalized()
        
        prev_pos = reference_loc_evaluator.evaluate(self.frame_start)
        prev_speed = 0.0
        cumulative_distance = 0.0
        last_keyframe_distance = 0.0  # Track distance at last keyframe
        
        # Always yield frame 1 with distance=0 (starting point)
        yield self.frame_start, cumulative_distance
        
        # Process each frame
        for f in range(self.frame_start + 1, self.frame_end + 1):
            pos = reference_loc_evaluator.evaluate(f)
            # Calculate speed from motion vector
            speed_vector = pos - prev_pos
            # Apply brake influence: brakes reduce forward motion
            brake_scale = 2 * brake_evaluator.evaluate(f).y - 1
            speed_vector *= brake_scale
            
            # Get rotation quaternion to determine bone orientation
            rotation_quaternion = rot_evaluator.evaluate(f)
            bone_orientation = rotation_quaternion @ bone_init_vector
            
            # Calculate signed speed (positive = forward, negative = backward)
            speed = math.copysign(speed_vector.magnitude, bone_orientation.dot(speed_vector))

            # Convert linear distance to rotation in radians
            # radians = distance / radius (since distance = radius * angle)
            rotation_speed = speed / radius

            # Accumulate rotation (total rotation in radians so far)
            # rotation_speed is already signed (direction kept by `speed`), so use it
            cumulative_distance += rotation_speed
            
            # Decide whether to create a keyframe based on distance change OR speed transition
            should_create_keyframe = False
            
            # Calculate distance traveled since last keyframe
            distance_since_last_keyframe = abs(cumulative_distance - last_keyframe_distance)
            
            if f == self.frame_end:
                # Always create keyframe at the final frame
                should_create_keyframe = True
            elif speed == 0.0 and prev_speed != 0.0:
                # Stopping: transition from motion to no motion
                should_create_keyframe = True
            elif speed != 0.0 and prev_speed == 0.0:
                # Starting: transition from no motion to motion
                should_create_keyframe = True
            elif distance_since_last_keyframe >= self.keyframe_tolerance:
                # Distance has changed enough since last keyframe
                # keyframe_tolerance (default 0.01) controls keyframe density
                should_create_keyframe = True
            elif prev_speed != 0.0 and rotation_speed != 0.0:
                # Also check for significant speed changes (acceleration/braking)
                relative_speed_change = abs(1.0 - (prev_speed / rotation_speed))
                should_create_keyframe = relative_speed_change > 0.1  # 10% speed change
            
            if should_create_keyframe:
                prev_speed = rotation_speed
                last_keyframe_distance = cumulative_distance
                yield f, cumulative_distance
            
            prev_pos = pos

    def _bake_wheel_rotation(self, context, baked_action, bone, brake_bone):
        # Convert bone name from 'Wheel_FR_0' to 'tq_WheelRotation_FR_0'
        bone_name = bone.name.replace('Wheel_', 'tq_WheelRotation_')
        clear_property_animation(context, bone_name, remove_keyframes=False)
        fc_rot = create_property_animation(context, bone_name)

        # Reset the transform of the wheel bone, otherwise baking yields wrong results
        pb: bpy.types.PoseBone = context.object.pose.bones[bone.name]
        pb.matrix_basis.identity()

        # Collect all distance values from the evaluator
        distance_per_frame = list(self._evaluate_distance_per_frame(baked_action, bone, brake_bone))
        
        if not distance_per_frame:
            self.report({'WARNING'}, f"No distance data calculated for {bone_name}")
            return
        
        # Insert keyframes for all collected distance points
        keyframe_count = 0
        for f, distance in distance_per_frame:
            kf = fc_rot.keyframe_points.insert(f, distance)
            kf.interpolation = 'LINEAR'
            keyframe_count += 1
        
        # Set fcurve extrapolation to LINEAR for smooth continuation
        if fc_rot.modifiers:
            for modifier in fc_rot.modifiers:
                fc_rot.modifiers.remove(modifier)
        
        # Report the number of keyframes created for this wheel
        if keyframe_count > 0:
            # Calculate total rotation in revolutions (2π radians = 1 revolution)
            total_rotation_radians = distance_per_frame[-1][1] if distance_per_frame else 0
            total_rotations = total_rotation_radians / (2 * math.pi)
            self.report({'INFO'}, f"Created {keyframe_count} keyframes for {bone_name}: {total_rotations:.2f} rotations ({total_rotation_radians:.2f} rad)")
        else:
            self.report({'WARNING'}, f"No keyframes created for {bone_name}")
class ANIM_OT_carSteeringBake(bpy.types.Operator, BakingOperator):
    bl_idname = 'anim.car_steering_bake'
    bl_label = 'Bake car steering'
    bl_description = 'Automatically generates steering animation based on Root bone animation.'
    bl_options = {'REGISTER', 'UNDO'}

    rotation_factor: bpy.props.FloatProperty(name='Rotation factor', min=.1, default=1)

    def draw(self, context):
        self.layout.use_property_split = True
        self.layout.use_property_decorate = False
        self.layout.prop(self, 'frame_start')
        self.layout.prop(self, 'frame_end')
        self.layout.prop(self, 'rotation_factor')
        self.layout.prop(self, 'keyframe_tolerance')

    def execute(self, context):
        if self.frame_end > self.frame_start:
            if 'Steering' in context.object.data.bones and 'MCH_SteeringRotation' in context.object.data.bones:
                steering = context.object.data.bones['Steering']
                mch_steering_rotation = context.object.data.bones['MCH_SteeringRotation']
                bone_offset = abs(steering.head_local.y - mch_steering_rotation.head_local.y)
                self._bake_steering_rotation(context, bone_offset, mch_steering_rotation)
        
        # Check if we should chain to wheel rotation baking (set by follow_path operator)
        if context.scene.get('tq_follow_path_bake_wheels', False):
            context.scene.tq_follow_path_bake_wheels = False  # Reset flag
            return bpy.ops.anim.car_wheels_rotation_bake('INVOKE_DEFAULT')
        
        return {'FINISHED'}

    def _evaluate_rotation_per_frame(self, action, bone_offset, bone):
        loc_evaluator = self._create_location_evaluator(action, bone)
        rot_evaluator = self._create_quaternion_evaluator(action, bone)

        distance_threshold = pow(bone_offset * max(self.keyframe_tolerance, .001), 2)
        steering_threshold = bone_offset * self.keyframe_tolerance * .1
        bone_direction_vector = (bone.head_local - bone.tail_local).normalized()
        bone_normal_vector = mathutils.Vector((1, 0, 0))

        current_pos = loc_evaluator.evaluate(self.frame_start)
        previous_steering_position = None
        for f in range(self.frame_start, self.frame_end - 1):
            next_pos = loc_evaluator.evaluate(f + 1)
            steering_direction_vector = next_pos - current_pos

            if steering_direction_vector.length_squared < distance_threshold:
                continue

            rotation_quaternion = rot_evaluator.evaluate(f)
            world_space_bone_direction_vector = rotation_quaternion @ bone_direction_vector
            world_space_bone_normal_vector = rotation_quaternion @ bone_normal_vector

            projected_steering_direction = steering_direction_vector.dot(world_space_bone_direction_vector)
            if projected_steering_direction == 0:
                continue

            length_ratio = bone_offset * self.rotation_factor / projected_steering_direction
            steering_direction_vector *= length_ratio

            steering_position = mathutils.geometry.distance_point_to_plane(steering_direction_vector,
                                                                           world_space_bone_direction_vector,
                                                                           world_space_bone_normal_vector)

            if previous_steering_position is not None \
                    and abs(steering_position - previous_steering_position) < steering_threshold:
                continue

            yield f, steering_position
            current_pos = next_pos
            previous_steering_position = steering_position

    @cursor('WAIT')
    def _bake_steering_rotation(self, context, bone_offset, bone):
        clear_property_animation(context, 'tq_SteeringRotation')
        fix_old_steering_rotation(context.object)
        fc_rot = create_property_animation(context, 'tq_SteeringRotation')

        baked_action = self._bake_action(context, bone)
        if baked_action is None:
            self.report({'WARNING'}, "Existing action failed to bake. Won't bake steering rotation")
            return

        try:
            # Reset the transform of the steering bone, because baking action manipulates the transform
            # and evaluate_rotation_frame expects it at it's default position
            pb: bpy.types.PoseBone = context.object.pose.bones[bone.name]
            pb.matrix_basis.identity()

            for f, steering_pos in self._evaluate_rotation_per_frame(baked_action, bone_offset, bone):
                kf = fc_rot.keyframe_points.insert(f, steering_pos)
                kf.type = 'JITTER'
                kf.interpolation = 'LINEAR'
        finally:
            bpy.data.actions.remove(baked_action)


class ANIM_OT_carClearSteeringWheelsRotation(bpy.types.Operator):
    bl_idname = "anim.car_clear_steering_wheels_rotation"
    bl_label = "Clear baked animation"
    bl_description = "Clear generated rotation for steering and wheels"
    bl_options = {'REGISTER', 'UNDO'}

    clear_steering: bpy.props.BoolProperty(name="Steering", description="Clear generated animation for steering",
                                           default=True)
    clear_wheels: bpy.props.BoolProperty(name="Wheels", description="Clear generated animation for wheels",
                                         default=True)

    def draw(self, context):
        self.layout.use_property_decorate = False
        self.layout.label(text='Clear generated keyframes for')
        self.layout.prop(self, property='clear_steering')
        self.layout.prop(self, property='clear_wheels')

    @classmethod
    def poll(cls, context):
        return (context.object is not None and 
                context.object.data is not None and 
                'Car Rig' in context.object.data and
                context.object.data.get('Car Rig') is not None and
                context.object.mode in ('POSE', 'OBJECT'))

    def execute(self, context):
        # Match Traffiq property names: tq_WheelRotation_FR_0, tq_WheelRotation_BL_1, etc.
        re_wheel_propname = re.compile(r'^tq_WheelRotation_[FB][LR]_\d+$')
        for prop in context.object.keys():
            if prop == 'tq_SteeringRotation':
                clear_property_animation(context, prop, remove_keyframes=self.clear_steering)
            elif re_wheel_propname.match(prop):
                clear_property_animation(context, prop, remove_keyframes=self.clear_wheels)
        # this is a hack to force Blender to take into account the modification
        # of the properties by changing the object mode.
        # Don't know yet if it is specific to blender 2.80
        mode = context.object.mode
        bpy.ops.object.mode_set(mode='OBJECT' if mode == 'POSE' else 'POSE')
        bpy.ops.object.mode_set(mode=mode)
        return {'FINISHED'}


def register():
    bpy.utils.register_class(ANIM_OT_carWheelsRotationBake)
    bpy.utils.register_class(ANIM_OT_carSteeringBake)
    bpy.utils.register_class(ANIM_OT_carClearSteeringWheelsRotation)


def unregister():
    bpy.utils.unregister_class(ANIM_OT_carClearSteeringWheelsRotation)
    bpy.utils.unregister_class(ANIM_OT_carSteeringBake)
    bpy.utils.unregister_class(ANIM_OT_carWheelsRotationBake)


if __name__ == "__main__":
    register()
