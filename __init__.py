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
import importlib
from . import bake_operators
from . import car_rig
from . import widgets
from . import mesh_grouper

# Module storage for late-loaded modules
_modules = {
}

# Handle reload on script re-execution
if "bpy" in locals():
    importlib.reload(bake_operators)
    importlib.reload(car_rig)
    importlib.reload(widgets)
    importlib.reload(mesh_grouper)


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


class RIGACAR_PT_mixin:

    def __init__(self):
        self.layout.use_property_split = True
        self.layout.use_property_decorate = False

    @classmethod
    def is_car_rig(cls, context):
        return context.object is not None and context.object.data is not None and 'Car Rig' in context.object.data

    @classmethod
    def is_car_rig_generated(cls, context):
        return cls.is_car_rig(context) and context.object.data['Car Rig']

    def display_generate_section(self, context):
        self.layout.operator(car_rig.POSE_OT_carAnimationRigGenerate.bl_idname, text='Generate')

    def display_bake_section(self, context):
        self.layout.operator(bake_operators.ANIM_OT_carSteeringBake.bl_idname)
        self.layout.operator(bake_operators.ANIM_OT_carWheelsRotationBake.bl_idname)
        self.layout.operator(bake_operators.ANIM_OT_carClearSteeringWheelsRotation.bl_idname)

    def display_rig_props_section(self, context):
        layout = self.layout.column()
        layout.prop(context.object, '["tq_WheelsYRolling"]', text="Wheels on Y axis")
        layout.prop(context.object, '["tq_SuspensionFactor"]', text="Pitch factor")
        layout.prop(context.object, '["tq_SuspensionRollingFactor"]', text="Roll factor")
        layout.separator()
        layout.label(text="Animation Setup:", icon='ANIM')
        layout.prop(context.scene, 'tq_ground_object', text="Ground Object")
        layout.prop(context.scene, 'tq_target_path_object', text="Path Curve")
        layout.separator()
        layout.operator(car_rig.POSE_OT_carFollowPath.bl_idname, text="Setup Follow Path Animation", icon='CURVE_PATH')
        layout.operator(car_rig.POSE_OT_carClearFollowPathAnimation.bl_idname, text="Clear Follow Path Animation", icon='TRASH')
        if context.mode == 'POSE':
            layout.separator()
            layout.label(text="Manual Setup:", icon='SETTINGS')
            layout.operator(car_rig.POSE_OT_carSetGround.bl_idname, text="Set Ground Only")
            layout.operator(car_rig.POSE_OT_carFollowPath.bl_idname, text="Follow Path Settings")

    def display_ground_sensors_section(self, context):
        for ground_sensor in enumerate_ground_sensors(context.object.pose.bones):
            ground_projection_constraint = ground_sensor.constraints.get('Ground projection')
            self.layout.label(text=ground_sensor.name, icon='BONE_DATA')
            if ground_projection_constraint is not None:
                self.layout.prop(ground_projection_constraint, 'target', text='Ground')
                if ground_projection_constraint.target is not None:
                    self.layout.prop(ground_projection_constraint, 'shrinkwrap_type')
                    if ground_projection_constraint.shrinkwrap_type == 'PROJECT':
                        self.layout.prop(ground_projection_constraint, 'project_limit')
                    self.layout.prop(ground_projection_constraint, 'influence')
            ground_projection_limit_constraint = ground_sensor.constraints.get('Ground projection limitation')
            if ground_projection_limit_constraint is not None:
                self.layout.prop(ground_projection_limit_constraint, 'min_z', text='Min local Z')
                self.layout.prop(ground_projection_limit_constraint, 'max_z', text='Max local Z')
            self.layout.separator()


class RIGACAR_PT_rigProperties(bpy.types.Panel, RIGACAR_PT_mixin):
    bl_label = "Rigacar"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "data"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        return RIGACAR_PT_mixin.is_car_rig(context)

    def draw(self, context):
        if RIGACAR_PT_mixin.is_car_rig_generated(context):
            self.display_rig_props_section(context)
            self.layout.separator()
            self.display_bake_section(context)
        else:
            self.display_generate_section(context)


class RIGACAR_PT_groundSensorsProperties(bpy.types.Panel, RIGACAR_PT_mixin):
    bl_label = "Ground Sensors"
    bl_parent_id = "RIGACAR_PT_rigProperties"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "data"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        return RIGACAR_PT_mixin.is_car_rig_generated(context)

    def draw(self, context):
        self.display_ground_sensors_section(context)


class RIGACAR_PT_animationRigView(bpy.types.Panel, RIGACAR_PT_mixin):
    bl_category = "Rigacar"
    bl_label = "Animation Rig"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"

    @classmethod
    def poll(cls, context):
        return RIGACAR_PT_mixin.is_car_rig(context)

    def draw(self, context):
        if RIGACAR_PT_mixin.is_car_rig_generated(context):
            self.display_rig_props_section(context)
        else:
            self.display_generate_section(context)


class RIGACAR_PT_wheelsAnimationView(bpy.types.Panel, RIGACAR_PT_mixin):
    bl_category = "Rigacar"
    bl_label = "Wheels animation"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"

    @classmethod
    def poll(cls, context):
        return RIGACAR_PT_mixin.is_car_rig_generated(context)

    def draw(self, context):
        # Wheel animation UI cleared - baking/clearing is now handled
        # directly when running the "Setup Follow Path Animation" operator.
        # Intentionally left blank to remove manual bake buttons.
        return


class RIGACAR_PT_groundSensorsView(bpy.types.Panel, RIGACAR_PT_mixin):
    bl_category = "Rigacar"
    bl_label = "Ground Sensors"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        return RIGACAR_PT_mixin.is_car_rig_generated(context)

    def draw(self, context):
        self.display_ground_sensors_section(context)


def menu_entries(menu, context):
    menu.layout.operator(car_rig.OBJECT_OT_armatureCarDeformationRig.bl_idname, text="Car (deformation rig)",
                         icon='AUTO')


classes = (
    RIGACAR_PT_rigProperties,
    RIGACAR_PT_groundSensorsProperties,
    RIGACAR_PT_animationRigView,
    RIGACAR_PT_wheelsAnimationView,
    RIGACAR_PT_groundSensorsView,
)


def register():
    try:
        bpy.types.VIEW3D_MT_armature_add.remove(menu_entries)
    except:
        pass
    
    # Unregister any already-registered classes (for reload support)
    for c in classes:
        try:
            bpy.utils.unregister_class(c)
        except:
            pass
    
    bpy.types.VIEW3D_MT_armature_add.append(menu_entries)
    for c in classes:
        bpy.utils.register_class(c)
    car_rig.register()
    bake_operators.register()
    mesh_grouper.register()


def unregister():
    mesh_grouper.unregister()
    bake_operators.unregister()
    car_rig.unregister()
    for c in classes:
        bpy.utils.unregister_class(c)
    bpy.types.VIEW3D_MT_armature_add.remove(menu_entries)


if __name__ == "__main__":
    register()
