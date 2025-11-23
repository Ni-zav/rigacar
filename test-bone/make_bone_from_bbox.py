#!/usr/bin/env python3
"""
make_bone_from_bbox.py

Create a single armature bone whose head is at the selected mesh object's
bounding-box y-max and tail at bounding-box y-min. Positions use world
coordinates; the bone is placed in a new armature object.

Usage:
- In Blender, select a mesh object (the bounding-box mesh), open the Text
  Editor, paste this file and Run Script.
- Or run Blender from the command line: `blender --background --python make_bone_from_bbox.py`
"""

import bpy
from mathutils import Vector


def main():
    obj = bpy.context.active_object
    if obj is None:
        print("No active object selected.")
        return
    if obj.type != 'MESH':
        print("Active object is not a mesh.")
        return

    # Get bounding-box corners in world space
    bbox_world = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]

    ys = [v.y for v in bbox_world]

    max_y = max(ys)
    min_y = min(ys)

    # compute center X/Z so bone has no X variance (aligned straight on Y axis)
    xs = [v.x for v in bbox_world]
    zs = [v.z for v in bbox_world]
    center_x = sum(xs) / len(xs)
    center_z = sum(zs) / len(zs)

    # Gather corners that lie on the y-max and y-min faces (use epsilon for safety)
    eps = 1e-6
    y_max_points = [v for v in bbox_world if abs(v.y - max_y) <= eps]
    y_min_points = [v for v in bbox_world if abs(v.y - min_y) <= eps]

    # Choose the corner on each face with the most extreme Z (head -> highest Z, tail -> lowest Z)
    if y_max_points:
        highest_z = max(y_max_points, key=lambda v: v.z).z
        head_world = Vector((center_x, max_y, highest_z))
    else:
        # fallback to face center (use center_z)
        head_world = Vector((center_x, max_y, center_z))

    if y_min_points:
        lowest_z = min(y_min_points, key=lambda v: v.z).z
        tail_world = Vector((center_x, min_y, lowest_z))
    else:
        # fallback to face center (use center_z)
        tail_world = Vector((center_x, min_y, center_z))

    # Ensure head is above (higher Z) than tail; swap if necessary
    if head_world.z < tail_world.z:
        head_world, tail_world = tail_world, head_world

    # Create a new armature and object
    arm_data = bpy.data.armatures.new(obj.name + "_arm")
    arm_obj = bpy.data.objects.new(obj.name + "_arm_obj", arm_data)
    bpy.context.collection.objects.link(arm_obj)

    # Make the new armature active
    bpy.context.view_layer.objects.active = arm_obj

    # Enter edit mode and create one bone. Coordinates must be in armature-local space.
    bpy.ops.object.mode_set(mode='EDIT')
    inv_mat = arm_obj.matrix_world.inverted()
    local_head = inv_mat @ head_world
    local_tail = inv_mat @ tail_world

    eb = arm_obj.data.edit_bones
    bone = eb.new('bbox_bone')
    bone.head = local_head
    bone.tail = local_tail
    bone.roll = 0.0

    bpy.ops.object.mode_set(mode='OBJECT')

    print(f"Created armature '{arm_obj.name}' with bone head at {head_world}, tail at {tail_world}")


if __name__ == '__main__':
    main()
