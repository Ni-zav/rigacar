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
import mathutils
from rna_prop_ui import rna_idprop_ui_create
from math import inf


DOOR_TYPES = [
    ('MANUAL', 'Manual Door', 'Rotation-based opening (hinge door)'),
    ('SLIDING', 'Sliding Door', 'Slight outward movement then backward slide')
]

DOOR_POSITIONS = [
    ('FL', 'Front Left', 'Front Left Door'),
    ('FR', 'Front Right', 'Front Right Door'),
    ('BL', 'Back Left', 'Back Left Door'),
    ('BR', 'Back Right', 'Back Right Door')
]

TRUNK_POSITIONS = [
    ('F', 'Front', 'Front Trunk (Frunk)'),
    ('B', 'Back', 'Back Trunk')
]


def get_widget(name):
    """Get or create a widget"""
    widget = bpy.data.objects.get(name)
    if widget is None:
        from . import widgets as widgets_module
        widgets_module.create()
        widget = bpy.data.objects.get(name)
    return widget


def define_custom_property(target, name, value, description=None, overridable=True):
    """Create a custom property on the target"""
    rna_idprop_ui_create(target, name, default=value, description=description, 
                         overridable=overridable, min=-inf, max=inf)


def create_door_bone(edit_bones, name, door_type, position_hint, parent_bone):
    """
    Create a door bone aligned to mesh bounding box Y-axis.
    Head is placed at y-max (highest Z corner), tail at y-min (lowest Z corner).
    
    Args:
        edit_bones: Armature edit bones collection
        name: Name of the door bone
        door_type: 'MANUAL' or 'SLIDING'
        position_hint: Hint for placement (FL, FR, BL, BR for doors; F, B for trunks)
        parent_bone: Parent bone (DEF_Body)
    """
    def find_matching_mesh(bone_name, position_hint):
        """Find mesh object matching door/trunk bone"""
        is_trunk = bone_name.startswith('Trunk')
        ph = position_hint.lower()
        
        # First pass: try exact match with position hint
        for obj in bpy.data.objects:
            if obj.type != 'MESH' or not obj.bound_box:
                continue
            
            obj_name_lower = obj.name.lower()
            
            if is_trunk:
                if 'trunk' in obj_name_lower:
                    return obj
            else:
                # Door: prefer mesh with both 'door' and position hint
                if 'door' in obj_name_lower and ph in obj_name_lower:
                    return obj
        
        # Second pass: any mesh with relevant keyword
        for obj in bpy.data.objects:
            if obj.type != 'MESH' or not obj.bound_box:
                continue
            
            obj_name_lower = obj.name.lower()
            
            if is_trunk and 'trunk' in obj_name_lower:
                return obj
            elif not is_trunk and 'door' in obj_name_lower:
                return obj
        
        return None
    
    def compute_bone_from_bbox(mesh_obj, armature_data, position_hint):
        """
        Compute bone head/tail from mesh bounding box Y-axis.
        Head at y-max (highest Z on that face), tail at y-min (lowest Z on that face).
        For trunk B, head at y-min (highest Z on that face), tail at y-max (lowest Z on that face).
        Returns (head, tail) in armature-local space.
        """
        # Get bounding box in world space
        bbox_world = [mesh_obj.matrix_world @ mathutils.Vector(corner) for corner in mesh_obj.bound_box]
        
        # Find armature object to transform to its local space
        arm_obj = None
        for o in bpy.data.objects:
            if o.type == 'ARMATURE' and o.data == armature_data:
                arm_obj = o
                break
        
        if arm_obj is None:
            # No armature object found, use world coordinates
            bbox_local = bbox_world
        else:
            # Transform to armature-local space
            arm_inv = arm_obj.matrix_world.inverted()
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
    
    # Create the bone
    door_bone = edit_bones.new(name)
    
    # Try to find matching mesh and compute bone from it
    mesh_obj = find_matching_mesh(name, position_hint)
    
    if mesh_obj:
        head, tail = compute_bone_from_bbox(mesh_obj, parent_bone.id_data, position_hint)
        door_bone.head = head
        door_bone.tail = tail
        door_bone.roll = 0.0
    else:
        # Fallback: use parent body dimensions
        body_center = parent_bone.head.copy()
        body_length = (parent_bone.tail - parent_bone.head).length
        
        is_left = 'L' in position_hint
        is_front = 'F' in position_hint
        is_trunk = name.startswith('Trunk')
        
        if is_trunk:
            # Trunk positioning
            if is_front:
                door_bone.head = mathutils.Vector((body_center.x, body_center.y + body_length * 0.4, body_center.z + 0.3))
                door_bone.tail = mathutils.Vector((body_center.x, body_center.y + body_length * 0.4 - 0.5, body_center.z + 0.1))
            else:
                door_bone.head = mathutils.Vector((body_center.x, body_center.y - body_length * 0.4, body_center.z + 0.3))
                door_bone.tail = mathutils.Vector((body_center.x, body_center.y - body_length * 0.4 + 0.5, body_center.z + 0.1))
        else:
            # Door positioning
            side_offset = 0.8 if is_left else -0.8
            front_back_offset = 0.3 if is_front else -0.3
            
            door_bone.head = mathutils.Vector((body_center.x + side_offset, body_center.y + front_back_offset + 0.3, body_center.z + 0.4))
            door_bone.tail = mathutils.Vector((body_center.x + side_offset, body_center.y + front_back_offset - 0.3, body_center.z + 0.1))
    
    door_bone.use_deform = False
    door_bone.parent = parent_bone
    
    return door_bone


def setup_door_constraints(obj, door_bone_name, door_type, position_hint):
    """
    Setup constraints for door bone based on type
    
    Args:
        obj: Armature object
        door_bone_name: Name of the door pose bone
        door_type: 'MANUAL' or 'SLIDING'
        position_hint: Position hint (FL, FR, BL, BR, F, B)
    """
    pose_bone = obj.pose.bones[door_bone_name]
    
    # Determine rotation axis based on position
    is_left = 'L' in position_hint
    is_trunk = door_bone_name.startswith('Trunk')
    is_front_trunk = is_trunk and 'F' in position_hint
    
    if door_type == 'MANUAL':
        # Manual door - rotation constraint
        cns = pose_bone.constraints.new('LIMIT_ROTATION')
        cns.name = 'Door Rotation Limit'
        cns.use_limit_x = False
        cns.use_limit_y = False
        cns.use_limit_z = True
        cns.owner_space = 'LOCAL'
        
        if is_trunk:
            # Trunk rotates on Y axis (pitch)
            cns.use_limit_y = True
            cns.use_limit_z = False
            if is_front_trunk:
                cns.min_y = math.radians(-90)
                cns.max_y = 0
            else:
                # For trunk B, reverse z max and min
                cns.min_y = math.radians(-90)
                cns.max_y = 0
        else:
            # Door rotates on Z axis
            if is_left:
                cns.min_z = math.radians(-90)
                cns.max_z = 0
            else:
                cns.min_z = 0
                cns.max_z = math.radians(90)
    
    else:  # SLIDING
        # Sliding door - limit location for slide movement
        cns = pose_bone.constraints.new('LIMIT_LOCATION')
        cns.name = 'Door Slide Limit'
        cns.owner_space = 'LOCAL'
        
        # Allow sliding backward along Y axis
        cns.use_min_y = True
        cns.use_max_y = True
        cns.min_y = -1.0  # Can slide 1 unit backward
        cns.max_y = 0.0
        
        # Allow slight outward movement on X
        cns.use_min_x = True
        cns.use_max_x = True
        if is_left:
            cns.min_x = 0.0
            cns.max_x = 0.2  # Slide out 0.2 units
        else:
            cns.min_x = -0.2
            cns.max_x = 0.0
        
        cns.use_min_z = True
        cns.use_max_z = True
        cns.min_z = 0.0
        cns.max_z = 0.0
    
    # Store door type as custom property
    define_custom_property(pose_bone, 'door_type', door_type, 
                          description='Type of door: MANUAL or SLIDING')


def assign_door_widget(obj, door_bone_name):
    """Assign the DoorTrunk widget to the door bone"""
    pose_bone = obj.pose.bones[door_bone_name]
    widget = get_widget('WGT-CarRig.DoorTrunk')
    pose_bone.custom_shape = widget
    pose_bone.custom_shape_scale_xyz = (0.3, 0.3, 0.3)


def assign_bone_to_collection(armature, bone_name, collection_name):
    """Assign bone to a specific bone collection"""
    bone = armature.bones[bone_name]
    collection = None
    
    # Find or create collection
    for coll in armature.collections:
        if coll.name == collection_name:
            collection = coll
            break
    
    if collection is None:
        collection = armature.collections.new(name=collection_name)
        collection.is_visible = True  # Layer 5 is visible
    
    collection.assign(bone)


def parent_meshes_to_bone(armature_obj, bone_name):
    """
    Find and parent any mesh objects matching the bone name to that bone.
    Searches for meshes with names containing the bone name.
    """
    import bpy
    
    # Find matching meshes
    matching_meshes = []
    for obj in bpy.context.scene.objects:
        if obj.type == 'MESH' and bone_name in obj.name:
            matching_meshes.append(obj)
    
    if not matching_meshes:
        return 0
    
    # Parent each mesh to the bone
    parented_count = 0
    for mesh_obj in matching_meshes:
        # Deselect all
        bpy.ops.object.select_all(action='DESELECT')
        
        # Select mesh and armature
        mesh_obj.select_set(True)
        armature_obj.select_set(True)
        bpy.context.view_layer.objects.active = armature_obj
        
        # Enter pose mode
        bpy.ops.object.mode_set(mode='POSE')
        
        # Select the bone
        for pose_bone in armature_obj.pose.bones:
            pose_bone.bone.select = False
        armature_obj.pose.bones[bone_name].bone.select = True
        bpy.context.view_layer.objects.active = armature_obj
        
        # Parent with automatic weights
        try:
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.context.view_layer.objects.active = mesh_obj
            mesh_obj.select_set(True)
            bpy.context.view_layer.objects.active = armature_obj
            armature_obj.select_set(True)
            bpy.ops.object.parent_set(type='ARMATURE_AUTO')
            parented_count += 1
        except:
            pass
    
    return parented_count


class POSE_OT_addDoor(bpy.types.Operator):
    """Add a door bone to the car rig"""
    bl_idname = "pose.rigacar_add_door"
    bl_label = "Add Door"
    bl_description = "Add a door bone with constraints"
    bl_options = {'REGISTER', 'UNDO'}
    
    door_type: bpy.props.EnumProperty(
        name="Door Type",
        description="Type of door opening mechanism",
        items=DOOR_TYPES,
        default='MANUAL'
    )
    
    door_position: bpy.props.EnumProperty(
        name="Position",
        description="Door position on the car",
        items=DOOR_POSITIONS,
        default='FL'
    )
    
    door_index: bpy.props.IntProperty(
        name="Index",
        description="Index for multiple doors in same position",
        default=0,
        min=0
    )
    
    @classmethod
    def poll(cls, context):
        return (context.object is not None and 
                context.object.type == 'ARMATURE' and
                'DEF_Body' in context.object.data.bones)
    
    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        
        layout.prop(self, 'door_type')
        layout.prop(self, 'door_position')
        layout.prop(self, 'door_index')
    
    def execute(self, context):
        obj = context.object
        
        # Generate door name
        door_name = f'Door_{self.door_position}_{self.door_index}'
        
        # Check if door already exists
        if door_name in obj.data.bones:
            self.report({'WARNING'}, f'Door {door_name} already exists')
            return {'CANCELLED'}
        
        # Switch to edit mode to create bone
        current_mode = obj.mode
        bpy.ops.object.mode_set(mode='EDIT')
        
        try:
            edit_bones = obj.data.edit_bones
            parent_bone = edit_bones['DEF_Body']
            
            # Create door bone
            create_door_bone(edit_bones, door_name, self.door_type, 
                           self.door_position, parent_bone)
            
            # Switch to pose mode for constraints
            bpy.ops.object.mode_set(mode='POSE')
            
            # Setup constraints
            setup_door_constraints(obj, door_name, self.door_type, self.door_position)
            
            # Assign widget
            assign_door_widget(obj, door_name)
            
            # Assign to Layer 5 (DoorTrunk collection)
            bpy.ops.object.mode_set(mode='OBJECT')
            assign_bone_to_collection(obj.data, door_name, 'Layer 5')
            assign_bone_to_collection(obj.data, door_name, 'DoorTrunk')
            
            # Try to parent matching meshes
            parented = parent_meshes_to_bone(obj, door_name)
            if parented > 0:
                self.report({'INFO'}, f'Created {door_name} ({self.door_type}) - parented {parented} mesh(es)')
            else:
                self.report({'INFO'}, f'Created {door_name} ({self.door_type})')
            
        finally:
            bpy.ops.object.mode_set(mode=current_mode)
        
        return {'FINISHED'}


class POSE_OT_addTrunk(bpy.types.Operator):
    """Add a trunk bone to the car rig"""
    bl_idname = "pose.rigacar_add_trunk"
    bl_label = "Add Trunk"
    bl_description = "Add a trunk bone with constraints"
    bl_options = {'REGISTER', 'UNDO'}
    
    trunk_type: bpy.props.EnumProperty(
        name="Trunk Type",
        description="Type of trunk opening mechanism",
        items=DOOR_TYPES,
        default='MANUAL'
    )
    
    trunk_position: bpy.props.EnumProperty(
        name="Position",
        description="Trunk position on the car",
        items=TRUNK_POSITIONS,
        default='B'
    )
    
    trunk_index: bpy.props.IntProperty(
        name="Index",
        description="Index for multiple trunks in same position",
        default=0,
        min=0
    )
    
    @classmethod
    def poll(cls, context):
        return (context.object is not None and 
                context.object.type == 'ARMATURE' and
                'DEF_Body' in context.object.data.bones)
    
    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        
        layout.prop(self, 'trunk_type')
        layout.prop(self, 'trunk_position')
        layout.prop(self, 'trunk_index')
    
    def execute(self, context):
        obj = context.object
        
        # Generate trunk name
        trunk_name = f'Trunk_{self.trunk_position}_{self.trunk_index}'
        
        # Check if trunk already exists
        if trunk_name in obj.data.bones:
            self.report({'WARNING'}, f'Trunk {trunk_name} already exists')
            return {'CANCELLED'}
        
        # Switch to edit mode to create bone
        current_mode = obj.mode
        bpy.ops.object.mode_set(mode='EDIT')
        
        try:
            edit_bones = obj.data.edit_bones
            parent_bone = edit_bones['DEF_Body']
            
            # Create trunk bone
            create_door_bone(edit_bones, trunk_name, self.trunk_type, 
                           self.trunk_position, parent_bone)
            
            # Switch to pose mode for constraints
            bpy.ops.object.mode_set(mode='POSE')
            
            # Setup constraints
            setup_door_constraints(obj, trunk_name, self.trunk_type, self.trunk_position)
            
            # Assign widget
            assign_door_widget(obj, trunk_name)
            
            # Assign to Layer 5 (DoorTrunk collection)
            bpy.ops.object.mode_set(mode='OBJECT')
            assign_bone_to_collection(obj.data, trunk_name, 'Layer 5')
            assign_bone_to_collection(obj.data, trunk_name, 'DoorTrunk')
            
            # Try to parent matching meshes
            parented = parent_meshes_to_bone(obj, trunk_name)
            if parented > 0:
                self.report({'INFO'}, f'Created {trunk_name} ({self.trunk_type}) - parented {parented} mesh(es)')
            else:
                self.report({'INFO'}, f'Created {trunk_name} ({self.trunk_type})')
            
        finally:
            bpy.ops.object.mode_set(mode=current_mode)
        
        return {'FINISHED'}


def register():
    # Door and trunk operators are intentionally NOT registered here.
    # Door and trunk deformation bones must be created only by the
    # deformation rig creation process in `car_rig.py` to keep
    # the rig consistent and avoid duplicate/conflicting bones.
    pass


def unregister():
    # No operator classes to unregister here since both door and trunk
    # operators are intentionally left unregistered.
    pass


if __name__ == "__main__":
    register()
