bl_info = {
    "name": "Maya Pivot",
    "category": "Mesh",
    "author": "Zinkenite",
    "description": "Implements features for the 3D cursor inspired by Maya's pivot system",
    "version": (1, 0),
}

import bpy
import bmesh
from mathutils import Vector, Matrix, Euler
import math

class MayaPivotProperties(bpy.types.PropertyGroup):
    align_to_closest_z: bpy.props.BoolProperty(
        name="Align to Global Z",
        description="Align cursor's Z axis to the normal's axis that is closest to global Z",
        default=False
    )
    move_cursor: bpy.props.BoolProperty(
        name="Move Cursor",
        description="Move cursor to selection",
        default=True
    )


class OBJECT_OT_MayaPivotPlacement(bpy.types.Operator):
    bl_idname = "object.maya_pivot_placement"
    bl_label = "Maya Pivot Cursor Placement"
    bl_options = {'REGISTER', 'UNDO'}

    def get_selection_data(self, context, bm):
        location = Vector((0, 0, 0))
        normal = Vector((0, 0, 0))
        count = 0

        selected_faces = [f for f in bm.faces if f.select]

        if selected_faces:
            for face in selected_faces:
                location += face.calc_center_median()
                normal = face.normal
                count += 1

        if count == 0:
            return None, None

        location /= count
        normal = normal.normalized()

        return location, normal

    def get_closest_axis_to_z(self, selection_matrix):
        x_axis = selection_matrix.col[0].xyz.normalized()
        y_axis = selection_matrix.col[1].xyz.normalized()
        z_axis = selection_matrix.col[2].xyz.normalized()
        global_z = Vector((0, 0, 1))

        x_dot = abs(x_axis.dot(global_z))
        y_dot = abs(y_axis.dot(global_z))
        z_dot = abs(z_axis.dot(global_z))

        dots = [(x_dot, 0), (y_dot, 1), (z_dot, 2)]
        dots.sort(key=lambda x: x[0], reverse=True)

        if len(dots) >= 2 and abs(dots[0][0] - dots[1][0]) < 0.001:
            if dots[0][1] == 2 and (dots[1][1] == 0 or dots[1][1] == 1):
                closest_axis = dots[1][1]
            elif dots[1][1] == 2 and (dots[0][1] == 0 or dots[0][1] == 1):
                closest_axis = dots[0][1]
            else:
                closest_axis = dots[0][1]
        else:
            closest_axis = dots[0][1]

        self.report({'INFO'}, f"Selected axis {closest_axis} (dots: x={x_dot:.3f}, y={y_dot:.3f}, z={z_dot:.3f})")
        return closest_axis

    def execute(self, context):
        obj = context.active_object

        bm = bmesh.from_edit_mesh(obj.data)
        original_orientation = context.scene.transform_orientation_slots[0].type

        location, normal = self.get_selection_data(context, bm)

        if location is None:
            self.report({'WARNING'}, "No elements selected")
            return {'CANCELLED'}

        try:
            bpy.ops.transform.create_orientation(name="SELECTION", use=True)
        except:
            self.report({'WARNING'}, "Could not create orientation from selection")
            return {'CANCELLED'}

        world_matrix = obj.matrix_world
        world_location = world_matrix @ location
        orientation_matrix = context.scene.transform_orientation_slots[0].custom_orientation.matrix

        props = context.scene.maya_pivot_props

        if props.move_cursor:
            context.scene.cursor.location = world_location

        if props.align_to_closest_z:
            closest_axis = self.get_closest_axis_to_z(orientation_matrix)
            if closest_axis == 0:
                rot_euler = Euler((0, -math.pi/2, 0), 'XYZ')
            elif closest_axis == 1:
                rot_euler = Euler((math.pi/2, 0, 0), 'XYZ')
            else:
                rot_euler = Euler((0, 0, 0), 'XYZ')

            final_matrix = orientation_matrix.to_4x4() @ rot_euler.to_matrix().to_4x4()
            context.scene.cursor.rotation_euler = final_matrix.to_euler()
        else:
            context.scene.cursor.rotation_euler = orientation_matrix.to_4x4().to_euler()

        bpy.ops.transform.delete_orientation()
        context.scene.transform_orientation_slots[0].type = original_orientation

        return {'FINISHED'}

class VIEW3D_PT_MayaPivotPanel(bpy.types.Panel):
    bl_label = "Maya Pivot"
    bl_idname = "VIEW3D_PT_maya_pivot"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Edit"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj and obj.mode == 'EDIT'

    def draw(self, context):
        layout = self.layout
        props = context.scene.maya_pivot_props

        layout.prop(props, "align_to_closest_z")
        layout.prop(props, "move_cursor")
        layout.operator("object.maya_pivot_placement", text="Apply Maya Pivot", icon='PIVOT_CURSOR')

def register():
    bpy.utils.register_class(MayaPivotProperties)
    bpy.utils.register_class(OBJECT_OT_MayaPivotPlacement)
    bpy.utils.register_class(VIEW3D_PT_MayaPivotPanel)
    bpy.types.Scene.maya_pivot_props = bpy.props.PointerProperty(type=MayaPivotProperties)

def unregister():
    bpy.utils.unregister_class(MayaPivotProperties)
    bpy.utils.unregister_class(OBJECT_OT_MayaPivotPlacement)
    bpy.utils.unregister_class(VIEW3D_PT_MayaPivotPanel)
    del bpy.types.Scene.maya_pivot_props

if __name__ == "__main__":
    register()
