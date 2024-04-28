import bpy
import gpu
import bgl
import numpy as np
from gpu_extras.batch import batch_for_shader

object = bpy.context.active_object
mesh = object.data
mesh.calc_loop_triangles()s

vertices = np.empty((len(mesh.vertices), 3), 'f')
indices = np.empty((len(mesh.loop_triangles), 3), 'i')

mesh.vertices.foreach_get(
    "co", np.reshape(vertices, len(mesh.vertices) * 3))
mesh.loop_triangles.foreach_get(
    "vertices", np.reshape(indices, len(mesh.loop_triangles) * 3))

red = (170/255, 57/255, 57/255, 1)
orange = (219/255, 99/255, 0, 1)
yellow = (236/255, 196/255, 0, 1)
green = (41/255, 199/255, 0, 1)
blue = (20/255, 9/255, 165/255, 1)
vertex_colors = []

vert_groups = object.vertex_groups

sel_vert_group = vert_groups["hand_r"]

for v in mesh.vertices:
    found = False
    for w in v.groups:
        if vert_groups[w.group] == sel_vert_group:
            if w.weight == 0.0:
                vertex_colors.append(yellow)
            if w.weight > 0:
                vertex_colors.append(green)
            found = True
    if not found:
        vertex_colors.append(blue)

shader = gpu.shader.from_builtin('3D_FLAT_COLOR')
batch = batch_for_shader(
    shader, 'TRIS',
    {"pos": vertices, "color": vertex_colors},
    indices=indices,
)


def draw():
    bgl.glEnable(bgl.GL_DEPTH_TEST)
    batch.draw(shader)
    bgl.glDisable(bgl.GL_DEPTH_TEST)


bpy.types.SpaceView3D.draw_handler_add(draw, (), 'WINDOW', 'POST_VIEW')