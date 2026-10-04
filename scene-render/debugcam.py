"""Close-up debug renders: python3 debugcam.py x y z dist pitch yaw lens out.png"""
import sys, math, os
sys.argv = [sys.argv[0]] + sys.argv[1:]
import bpy
from mathutils import Vector, Euler
import scene as S, props
x, y, z, dist, pitch, yaw, lens = map(float, sys.argv[1:8])
out = sys.argv[8]
sc = S.reset()
S.build_table(); S.build_tray(); S.build_paper(7.0)
S.build_pizza(0.0)
props.build_all("desktop", 0.0, S.PLATE_C, S.GLASS_C)
S.lights("desktop")
cam = S.build_camera("desktop")
t = Vector((x, y, z))
d = Vector((0, -math.cos(math.radians(pitch)), math.sin(math.radians(pitch))))
d.rotate(Euler((0, 0, math.radians(yaw))))
cam.location = t + d * dist
cam.rotation_euler = Euler((math.radians(90 - pitch), 0, math.radians(yaw)))
cam.data.lens = lens
cam.data.shift_y = 0
cam.data.dof.focus_distance = dist
sc.render.resolution_x = 900; sc.render.resolution_y = 700
sc.cycles.samples = int(os.environ.get("SAMPLES", 32))
sc.render.filepath = out
bpy.ops.render.render(write_still=True)
