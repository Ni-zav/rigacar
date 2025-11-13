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
from typing import List, Optional

# Available rig groups with their suffixes
RIG_GROUPS = {
    'Body': 'Body',
    'Wheel Front Left': 'Wheel_FL_0',
    'Wheel Front Right': 'Wheel_FR_0',
    'Wheel Back Left': 'Wheel_BL_0',
    'Wheel Back Right': 'Wheel_BR_0',
    'Wheel Back Left Extra': 'Wheel_BL_1',
    'Wheel Back Right Extra': 'Wheel_BR_1',
    'WheelBrake Front Left': 'Brake_FL_0',
    'WheelBrake Front Right': 'Brake_FR_0',
    'WheelBrake Back Left': 'Brake_BL_0',
    'WheelBrake Back Right': 'Brake_BR_0',
    'WheelBrake Back Left Extra': 'Brake_BL_1',
    'WheelBrake Back Right Extra': 'Brake_BR_1',
    'Steering': 'Steering',
}


def get_selected_meshes(context) -> List[bpy.types.Object]:
    """Get all selected mesh objects"""
    return [obj for obj in context.selected_objects if obj.type == 'MESH']


def get_base_mesh_name(mesh_name: str) -> str:
    """
    Extract base name from mesh.
    Examples:
    - 'bmw-z4' -> 'bmw-z4'
    - 'bmw-z4.001' -> 'bmw-z4'
    - 'bmw-z4.002' -> 'bmw-z4'
    """
    # Remove trailing .00X suffixes
    import re
    match = re.match(r'^(.*?)(?:\.\d+)?$', mesh_name)
    return match.group(1) if match else mesh_name


def join_meshes_and_set_origin(meshes: List[bpy.types.Object], context, name: str):
    """Join multiple meshes together and set origin to grouped geometry"""
    # Deselect all first
    bpy.ops.object.select_all(action='DESELECT')
    
    # Select all meshes
    for mesh in meshes:
        mesh.select_set(True)
    
    # Set first mesh as active (required for join operation)
    context.view_layer.objects.active = meshes[0]
    
    # Join all meshes (Ctrl+J)
    bpy.ops.object.join()
    
    # The joined object is now the active object (first mesh)
    joined_object = context.view_layer.objects.active
    joined_object.name = name
    
    # Set origin to geometry
    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY')
    
    # Deselect all
    bpy.ops.object.select_all(action='DESELECT')
    
    return joined_object


# Dynamically create operators for each rig group
def create_group_operator(group_label: str, suffix: str):
    class MESH_GROUPER_OT_group(bpy.types.Operator):
        bl_idname = f"mesh_grouper.group_{suffix.lower().replace('.', '_')}"
        bl_label = f"Assign to {group_label}"
        bl_options = {'REGISTER', 'UNDO'}
        
        @classmethod
        def poll(cls, context):
            return context.mode == 'OBJECT' and len(get_selected_meshes(context)) > 0
        
        def execute(self, context):
            selected_meshes = get_selected_meshes(context)
            
            if not selected_meshes:
                self.report({'WARNING'}, "No meshes selected")
                return {'CANCELLED'}
            
            # Get prefix based on source
            if context.scene.prefix_source == 'BLEND':
                import os
                if bpy.data.filepath:
                    prefix = os.path.splitext(os.path.basename(bpy.data.filepath))[0]
                else:
                    prefix = "Untitled"
            elif context.scene.prefix_source == 'CUSTOM':
                prefix = context.scene.custom_prefix or get_base_mesh_name(selected_meshes[0].name)
            else:  # MESH
                prefix = get_base_mesh_name(selected_meshes[0].name)
            
            # Create combined object name with auto-increment for duplicates
            base_name = f"{prefix}_{suffix}"
            combined_name = base_name
            
            # If the suffix ends with a number (like Wheel_FR_0), increment it
            import re
            match = re.match(r'^(.+)_(\d+)$', suffix)
            if match:
                base_suffix = match.group(1)
                start_num = int(match.group(2))
                counter = start_num
                while bpy.data.objects.get(combined_name) is not None:
                    counter += 1
                    combined_name = f"{prefix}_{base_suffix}_{counter}"
            else:
                # For non-numbered suffixes (like Body), just ensure uniqueness
                counter = 1
                while bpy.data.objects.get(combined_name) is not None:
                    combined_name = f"{base_name}_{counter}"
                    counter += 1
            
            # Join all selected meshes and set origin
            join_meshes_and_set_origin(selected_meshes, context, combined_name)
            
            self.report({'INFO'}, f"Combined {len(selected_meshes)} mesh(es) into {combined_name}")
            return {'FINISHED'}
    
    return MESH_GROUPER_OT_group


class MESH_GROUPER_PT_mesh_grouping(bpy.types.Panel):
    """Panel for mesh grouping tools"""
    bl_label = "Mesh Grouping"
    bl_idname = "MESH_GROUPER_PT_mesh_grouping"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Rigacar'
    
    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'
    
    def draw(self, context):
        layout = self.layout
        layout.use_property_split = False
        layout.use_property_decorate = False
        
        selected_meshes = get_selected_meshes(context)
        
        if selected_meshes:
            # Show selected mesh info
            box = layout.box()
            box.label(text="Selected Meshes", icon='OBJECT_DATA')
            col = box.column(align=True)
            for mesh in selected_meshes[:5]:  # Show first 5
                col.label(text=f"  - {mesh.name}", icon='DOT')
            if len(selected_meshes) > 5:
                col.label(text=f"  ... and {len(selected_meshes) - 5} more", icon='DOT')
            
            # Base name
            base_name = get_base_mesh_name(selected_meshes[0].name)
            box.separator()
            box.label(text=f"Base Name: '{base_name}'", icon='INFO')
            
            # Prefix source selection
            box.separator()
            box.prop(context.scene, "prefix_source")
            
            # Custom prefix input (only show if CUSTOM selected)
            if context.scene.prefix_source == 'CUSTOM':
                box.prop(context.scene, "custom_prefix")
            
            # Rig group buttons
            box.separator()
            box.label(text="Assign to Rig Group:", icon='ARMATURE_DATA')
            
            # Body button
            row = box.row()
            row.operator("mesh_grouper.group_body", text="Body")
            
            # Wheel buttons on one line
            row = box.row()
            row.operator("mesh_grouper.group_wheel_fl_0", text="Wheel FL")
            row.operator("mesh_grouper.group_wheel_fr_0", text="Wheel FR")
            row.operator("mesh_grouper.group_wheel_bl_0", text="Wheel BL")
            row.operator("mesh_grouper.group_wheel_br_0", text="Wheel BR")
            
            # Extra back wheel buttons on one line
            row = box.row()
            row.operator("mesh_grouper.group_wheel_bl_1", text="Wheel BL Extra")
            row.operator("mesh_grouper.group_wheel_br_1", text="Wheel BR Extra")
            
            # WheelBrake buttons on one line
            row = box.row()
            row.operator("mesh_grouper.group_brake_fl_0", text="Brake FL")
            row.operator("mesh_grouper.group_brake_fr_0", text="Brake FR")
            row.operator("mesh_grouper.group_brake_bl_0", text="Brake BL")
            row.operator("mesh_grouper.group_brake_br_0", text="Brake BR")
            
            # Extra back WheelBrake buttons on one line
            row = box.row()
            row.operator("mesh_grouper.group_brake_bl_1", text="Brake BL Extra")
            row.operator("mesh_grouper.group_brake_br_1", text="Brake BR Extra")
            
            # Steering button
            row = box.row()
            row.operator("mesh_grouper.group_steering", text="Steering")
        else:
            box = layout.box()
            box.label(text="Select meshes to assign to rig groups", icon='INFO')


# Create operator classes for all rig groups
_operator_classes = [MESH_GROUPER_PT_mesh_grouping]
for group_label, suffix in RIG_GROUPS.items():
    operator_class = create_group_operator(group_label, suffix)
    _operator_classes.append(operator_class)

classes = tuple(_operator_classes)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    
    # Add prefix source property to Scene
    bpy.types.Scene.prefix_source = bpy.props.EnumProperty(
        name="Prefix Source",
        description="Choose the source for the empty name prefix",
        items=[
            ('BLEND', "Blend File", "Use .blend file name as prefix"),
            ('CUSTOM', "Custom", "Use custom prefix"),
            ('MESH', "Mesh Name", "Use mesh base name as prefix"),
        ],
        default='BLEND'
    )
    
    # Add custom prefix property to Scene
    bpy.types.Scene.custom_prefix = bpy.props.StringProperty(
        name="Custom Prefix",
        default="",
        description="Custom prefix for empty names."
    )


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    
    # Remove properties from Scene
    del bpy.types.Scene.prefix_source
    del bpy.types.Scene.custom_prefix
