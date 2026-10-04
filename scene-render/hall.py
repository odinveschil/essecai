"""The Station F / La Felicità food hall around our table.

Everything here sits behind the table and ends up in the depth-of-field blur.
It is built in a local frame where the viewer looks along +Y, then yawed to match
the camera and pitched about the camera centre (a forced-perspective cheat so the
room's eye-level appears in the top of the frame while the tray stays at ~45°).
"""
import math
import os

import bpy
import bmesh
import numpy as np
from mathutils import Vector, Matrix, Euler

from common import OUT
from util import new_mat, img_node, link, principled, emission_mat, box, sphere, cylinder, plane, set_smooth, obj_from_mesh, lathe

FLOOR = -0.76
RNG = np.random.default_rng(2026)
_MESH = {}


def coll():
    c = bpy.data.collections.get("Hall")
    if c is None:
        c = bpy.data.collections.new("Hall")
        bpy.context.scene.collection.children.link(c)
    return c


def lit(name, color, strength, camera=1.0, glossy=0.6, diffuse=0.08):
    """Emission that reads to camera + reflections, but barely lights the tray."""
    m = bpy.data.materials.new(name)
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    e = nt.nodes.new("ShaderNodeEmission")
    e.inputs["Color"].default_value = (*color, 1)
    lp = nt.nodes.new("ShaderNodeLightPath")
    a = nt.nodes.new("ShaderNodeMath")
    a.operation = "MULTIPLY"
    a.inputs[1].default_value = camera
    link(nt, lp.outputs["Is Camera Ray"], a.inputs[0])
    b = nt.nodes.new("ShaderNodeMath")
    b.operation = "MULTIPLY_ADD"
    b.name = "glossmul"
    b["bg_gloss"] = glossy
    b.inputs[1].default_value = glossy
    link(nt, lp.outputs["Is Glossy Ray"], b.inputs[0])
    link(nt, a.outputs[0], b.inputs[2])
    c = nt.nodes.new("ShaderNodeMath")
    c.operation = "MULTIPLY_ADD"
    c.name = "diffmul"
    c["fg_diffuse"] = diffuse
    c.inputs[1].default_value = diffuse
    link(nt, lp.outputs["Is Diffuse Ray"], c.inputs[0])
    link(nt, b.outputs[0], c.inputs[2])
    s = nt.nodes.new("ShaderNodeMath")
    s.operation = "MULTIPLY"
    s.inputs[1].default_value = strength
    link(nt, c.outputs[0], s.inputs[0])
    link(nt, s.outputs[0], e.inputs["Strength"])
    o = nt.nodes.new("ShaderNodeOutputMaterial")
    link(nt, e.outputs[0], o.inputs["Surface"])
    return m


def lit_image(name, file, strength):
    m = lit(name, (1, 1, 1), strength)
    nt = m.node_tree
    tex = img_node(nt, file)
    e = [n for n in nt.nodes if n.type == "EMISSION"][0]
    link(nt, tex.outputs["Color"], e.inputs["Color"])
    return m


def inst(name, key, builder, loc, rot=(0, 0, 0), scale=(1, 1, 1), mat=None):
    """Linked-duplicate instancing of a cached mesh."""
    if key not in _MESH:
        _MESH[key] = builder()
    me = _MESH[key]
    ob = bpy.data.objects.new(name, me)
    coll().objects.link(ob)
    ob.location = loc
    ob.rotation_euler = rot
    ob.scale = scale
    if mat is not None:
        ob.material_slots and None
        if not me.materials:
            me.materials.append(mat)
    return ob


def mesh_box(sx, sy, sz):
    def b():
        me = bpy.data.meshes.new("box")
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=1.0)
        for v in bm.verts:
            v.co.x *= sx
            v.co.y *= sy
            v.co.z *= sz
        bm.to_mesh(me)
        bm.free()
        return me
    return b


def mesh_sphere(r, segs=16, rings=8):
    def b():
        me = bpy.data.meshes.new("sph")
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=segs, v_segments=rings, radius=r)
        bm.to_mesh(me)
        bm.free()
        for p in me.polygons:
            p.use_smooth = True
        return me
    return b


def mesh_cyl(r, h, segs=16):
    def b():
        me = bpy.data.meshes.new("cyl")
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=True, segments=segs, radius1=r, radius2=r, depth=h)
        bm.to_mesh(me)
        bm.free()
        for p in me.polygons:
            p.use_smooth = True
        return me
    return b


def put(o):
    for c in o.users_collection:
        c.objects.unlink(o)
    coll().objects.link(o)
    return o


# ------------------------------------------------------------------ materials

def concrete(name="Concrete", tone=(0.46, 0.44, 0.41), rough=0.8, scale=3.0):
    m, nt, b = new_mat(name)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    n = nt.nodes.new("ShaderNodeTexNoise")
    n.inputs["Scale"].default_value = scale
    n.inputs["Detail"].default_value = 8
    link(nt, tc.outputs["Object"], n.inputs["Vector"])
    r = nt.nodes.new("ShaderNodeValToRGB")
    r.color_ramp.elements[0].color = (tone[0] * 0.7, tone[1] * 0.7, tone[2] * 0.7, 1)
    r.color_ramp.elements[1].color = (tone[0] * 1.15, tone[1] * 1.15, tone[2] * 1.15, 1)
    link(nt, n.outputs["Fac"], r.inputs[0])
    link(nt, r.outputs[0], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = rough
    return m


def floor_mat():
    m = concrete("Floor", (0.30, 0.28, 0.26), rough=0.28, scale=0.6)
    return m


# ------------------------------------------------------------------ pieces

def person(name, loc, seated=False, rot=0.0, palette=None):
    rng = RNG
    skin = [(0.80, 0.60, 0.47), (0.62, 0.43, 0.31), (0.42, 0.28, 0.19), (0.88, 0.70, 0.58), (0.70, 0.50, 0.36)][rng.integers(5)]
    shirt = palette or [(0.85, 0.85, 0.82), (0.10, 0.10, 0.12), (0.62, 0.12, 0.10), (0.80, 0.62, 0.20), (0.18, 0.28, 0.45),
                        (0.40, 0.45, 0.30), (0.75, 0.55, 0.45), (0.25, 0.20, 0.18), (0.55, 0.65, 0.75), (0.90, 0.75, 0.70)][rng.integers(10)]
    pants = [(0.12, 0.15, 0.25), (0.08, 0.08, 0.09), (0.55, 0.48, 0.38), (0.22, 0.30, 0.45)][rng.integers(4)]
    hair = [(0.05, 0.035, 0.025), (0.20, 0.12, 0.06), (0.45, 0.32, 0.18), (0.08, 0.06, 0.05)][rng.integers(4)]
    ms = principled(name + "_skin", skin, rough=0.5, sss=0.2)
    mc = principled(name + "_shirt", shirt, rough=0.85)
    mp = principled(name + "_pants", pants, rough=0.8)
    mh = principled(name + "_hair", hair, rough=0.6)
    root = bpy.data.objects.new(name, None)
    coll().objects.link(root)
    root.location = loc
    root.rotation_euler.z = rot
    h = rng.uniform(0.95, 1.06)
    parts = []
    if seated:
        hip = 0.46 * h
        parts.append(put(box(name + "_thighs", (0.34, 0.46, 0.15), (0, 0.18, hip), mp, bevel=0.06)))
        parts.append(put(box(name + "_shins", (0.30, 0.13, 0.46), (0, 0.38, 0.23), mp, bevel=0.05)))
    else:
        hip = 0.9 * h
        stride = rng.uniform(-0.15, 0.15)
        parts.append(put(box(name + "_legL", (0.13, 0.15, hip), (-0.09, stride, hip / 2), mp, bevel=0.05)))
        parts.append(put(box(name + "_legR", (0.13, 0.15, hip), (0.09, -stride, hip / 2), mp, bevel=0.05)))
    torso_h = 0.58 * h
    parts.append(put(box(name + "_torso", (0.40, 0.24, torso_h), (0, 0, hip + torso_h / 2), mc, bevel=0.09)))
    parts.append(put(box(name + "_armL", (0.10, 0.12, 0.55 * h), (-0.25, 0.04, hip + torso_h - 0.28), mc, bevel=0.045, rot=(0.3 if seated else 0.1, 0.08, 0))))
    parts.append(put(box(name + "_armR", (0.10, 0.12, 0.55 * h), (0.25, 0.04, hip + torso_h - 0.28), mc, bevel=0.045, rot=(0.3 if seated else -0.1, -0.08, 0))))
    hz = hip + torso_h + 0.17
    parts.append(put(sphere(name + "_neck", 0.06, (0, 0, hip + torso_h + 0.03), ms, segs=12, rings=6)))
    parts.append(put(sphere(name + "_head", 0.105, (0, 0, hz), ms, segs=16, rings=10, scale=(0.92, 1.0, 1.15))))
    hair_s = rng.uniform(0.95, 1.25)
    parts.append(put(sphere(name + "_hair", 0.114, (0, 0.025, hz + 0.035), mh, segs=16, rings=10, scale=(1.0, 1.0 * hair_s, 0.95))))
    for p in parts:
        p.parent = root
    return root


def chair(name, loc, rot, color):
    m = principled(name + "_m", color, rough=0.55)
    root = bpy.data.objects.new(name, None)
    coll().objects.link(root)
    root.location = loc
    root.rotation_euler.z = rot
    parts = [put(box(name + "_seat", (0.42, 0.42, 0.04), (0, 0, 0.45), m, bevel=0.01)),
             put(box(name + "_back", (0.42, 0.04, 0.42), (0, 0.19, 0.68), m, bevel=0.01))]
    for dx in (-0.18, 0.18):
        for dy in (-0.18, 0.18):
            parts.append(put(box(name + "_leg", (0.03, 0.03, 0.45), (dx, dy, 0.225), m)))
    for p in parts:
        p.parent = root
    return root


def long_table(name, loc, rot, wood):
    root = bpy.data.objects.new(name, None)
    coll().objects.link(root)
    root.location = loc
    root.rotation_euler.z = rot
    top = put(box(name + "_top", (3.0, 0.95, 0.05), (0, 0, 0.735), wood, bevel=0.01))
    top.parent = root
    for dx in (-1.35, 1.35):
        lg = put(box(name + "_leg", (0.08, 0.8, 0.71), (dx, 0, 0.355), principled(name + "_steel", (0.05, 0.05, 0.05), rough=0.4, metallic=1)))
        lg.parent = root
    return root


def table_clutter(root, rng):
    """Trays, glasses, plates on the other tables."""
    out = []
    cols = [(0.10, 0.27, 0.20), (0.55, 0.12, 0.10), (0.75, 0.55, 0.2), (0.12, 0.2, 0.35)]
    for k in range(rng.integers(3, 6)):
        x = rng.uniform(-1.3, 1.3)
        y = rng.choice([-0.25, 0.25])
        t = put(box(root.name + f"_tray{k}", (0.45, 0.32, 0.02), (x, y, 0.77), principled(root.name + f"_trm{k}", cols[rng.integers(4)], rough=0.4)))
        t.parent = root
        pz = put(cylinder(root.name + f"_pz{k}", 0.15, 0.02, (x, y, 0.79), principled(root.name + f"_pzm{k}", (0.78, 0.40, 0.18), rough=0.6)))
        pz.parent = root
        out += [t, pz]
        if rng.uniform() < 0.7:
            g = put(cylinder(root.name + f"_gl{k}", 0.035, 0.14, (x + 0.2, y + 0.05, 0.85), principled(root.name + f"_glm{k}", [(0.85, 0.55, 0.15), (0.05, 0.02, 0.01), (0.55, 0.05, 0.1), (0.9, 0.9, 0.85)][rng.integers(4)], rough=0.05, coat=1.0)))
            g.parent = root
            out.append(g)
    return out


def leafy(name, loc, radius, n=60, tone=(0.16, 0.30, 0.10), squash=1.0):
    """A cloud of leaves — reads as a plant once it's out of focus."""
    rng = RNG
    mats = [principled(f"{name}_leaf{i}", (tone[0] * f, tone[1] * f, tone[2] * f), rough=0.45, sss=0.15) for i, f in enumerate((0.7, 1.0, 1.35))]
    out = []
    for i in range(n):
        d = rng.normal(0, 1, 3)
        d /= np.linalg.norm(d)
        r = radius * rng.uniform(0.3, 1.0) ** 0.5
        p = (loc[0] + d[0] * r, loc[1] + d[1] * r, loc[2] + d[2] * r * squash)
        s = rng.uniform(0.6, 1.4) * radius * 0.22
        o = inst(f"{name}_{i}", f"leaf{i % 3}", mesh_sphere(1.0, 10, 6), p,
                 rot=tuple(rng.uniform(0, 3.14, 3)), scale=(s, s * 0.45, s * 0.1))
        if not o.data.materials:
            o.data.materials.append(mats[i % 3])
        out.append(o)
    return out


def potted_tree(name, loc, h=2.6):
    pot = put(cylinder(name + "_pot", 0.32, 0.6, (loc[0], loc[1], FLOOR + 0.3), principled(name + "_potm", (0.55, 0.28, 0.16), rough=0.7), segs=24))
    trunk = put(cylinder(name + "_trunk", 0.04, h, (loc[0], loc[1], FLOOR + 0.6 + h / 2), principled(name + "_bark", (0.25, 0.18, 0.12), rough=0.8), segs=8))
    leaves = leafy(name, (loc[0], loc[1], FLOOR + 0.6 + h), 0.9, n=110)
    return [pot, trunk] + leaves


def bulb(name, loc, strength=40.0, r=0.045, color=(1.0, 0.62, 0.28)):
    key = "bulbmat%.1f" % strength
    m = bpy.data.materials.get(key) or lit(key, color, strength, glossy=0.8, diffuse=0.02)
    m.name = key
    o = inst(name, "bulb", mesh_sphere(1.0, 14, 8), loc, scale=(r, r, r * 1.2))
    if not o.data.materials:
        o.data.materials.append(m)
    return o


def festoon(name, a, b, n=14, sag=0.6, strength=30):
    out = []
    wire = principled("wire", (0.02, 0.02, 0.02), rough=0.5)
    for i in range(n + 1):
        t = i / n
        p = Vector(a).lerp(Vector(b), t)
        p.z -= sag * 4 * t * (1 - t)
        out.append(bulb(f"{name}_{i}", (p.x, p.y, p.z - 0.07), strength, r=0.035))
    return out


def pendant(name, loc, drop=1.2, strength=60):
    shade = principled("shade_brass", (0.75, 0.55, 0.28), rough=0.3, metallic=1.0)
    out = [put(cylinder(name + "_cord", 0.004, drop, (loc[0], loc[1], loc[2] + drop / 2), principled("cord", (0.02, 0.02, 0.02)), segs=6)),
           put(lathe(name + "_shade", [(0.0, 0.16), (0.03, 0.16), (0.07, 0.12), (0.17, 0.0), (0.165, -0.005), (0.06, 0.115), (0.0, 0.15)], segs=32, mat=shade))]
    out[1].location = loc
    out.append(bulb(name + "_bulb", (loc[0], loc[1], loc[2] + 0.03), strength, r=0.05))
    return out


def sign(name, file, loc, width, rot=(math.radians(90), 0, 0), strength=6.0):
    from PIL import Image
    im = Image.open(os.path.join(OUT, file))
    h = width * im.height / im.width
    m = lit_image(name + "_m", file, strength)
    p = put(plane(name, width, h, loc, m, rot=rot))
    return p


def kiosk(name, x, y, w, d, h, color, sign_file, rot=0.0):
    """A market-stall/kiosk: painted box, lit counter, signboard."""
    root = bpy.data.objects.new(name, None)
    coll().objects.link(root)
    root.location = (x, y, FLOOR)
    root.rotation_euler.z = rot
    body = principled(name + "_paint", color, rough=0.5)
    parts = [put(box(name + "_back", (w, 0.2, h), (0, d / 2, h / 2), body)),
             put(box(name + "_l", (0.2, d, h), (-w / 2, 0, h / 2), body)),
             put(box(name + "_r", (0.2, d, h), (w / 2, 0, h / 2), body)),
             put(box(name + "_roof", (w + 0.3, d + 0.3, 0.25), (0, 0, h), body)),
             put(box(name + "_counter", (w, 0.6, 1.05), (0, -d / 2 + 0.3, 0.525), principled(name + "_ctr", (0.85, 0.80, 0.70), rough=0.4))),
             put(plane(name + "_glow", w - 0.3, h - 1.3, (0, d / 2 - 0.12, 1.05 + (h - 1.3) / 2), lit(name + "_in", (1.0, 0.72, 0.42), 1.8), rot=(math.radians(90), 0, 0)))]
    # bottles / jars on shelves
    for k in range(int(w * 6)):
        bx = -w / 2 + 0.25 + k * (w - 0.5) / max(int(w * 6) - 1, 1)
        c = [(0.2, 0.45, 0.15), (0.6, 0.1, 0.08), (0.9, 0.7, 0.2), (0.15, 0.1, 0.05), (0.85, 0.85, 0.8)][k % 5]
        parts.append(put(cylinder(name + f"_bt{k}", 0.04, 0.3, (bx, d / 2 - 0.3, 1.9), principled(name + f"_btm{k}", c, rough=0.1, coat=1), segs=10)))
    for p in parts:
        p.parent = root
    s = sign(name + "_sign", sign_file, (0, -d / 2 - 0.17, h + 0.35), min(w * 0.85, 3.2), strength=5.0)
    s.parent = root
    # plants on the roof
    for k in range(3):
        lv = leafy(name + f"_rp{k}", (-w / 2 + (k + 0.5) * w / 3, 0, h + 0.5), 0.5, n=40)
        for o in lv:
            o.location = (o.location.x, o.location.y, o.location.z)
            o.parent = root
    return root


def train_car(name, x, y0, length, rot=0.0):
    """Vintage rail carriage converted into seating — warm windows."""
    root = bpy.data.objects.new(name, None)
    coll().objects.link(root)
    root.location = (x, y0, FLOOR + 0.6)
    root.rotation_euler.z = rot
    green = principled(name + "_paint", (0.06, 0.20, 0.15), rough=0.35, coat=0.6)
    cream = principled(name + "_cream", (0.85, 0.78, 0.60), rough=0.4, coat=0.6)
    parts = [put(box(name + "_body", (2.9, length, 2.6), (0, length / 2, 1.3), green, bevel=0.05)),
             put(box(name + "_stripe", (2.95, length - 0.1, 0.18), (0, length / 2, 1.0), cream)),
             put(cylinder(name + "_roof", 1.5, length, (0, length / 2, 2.55), principled(name + "_roofm", (0.12, 0.12, 0.12), rough=0.5), segs=32, rot=(math.radians(90), 0, 0))),
             put(box(name + "_chassis", (2.4, length - 0.6, 0.5), (0, length / 2, -0.25), principled(name + "_ch", (0.04, 0.04, 0.04), rough=0.6)))]
    parts[2].scale = (1, 0.35, 1)
    win = lit(name + "_win", (1.0, 0.72, 0.42), 5.0)
    n = int(length / 1.6)
    for k in range(n):
        yy = 0.8 + k * (length - 1.6) / max(n - 1, 1)
        for side in (-1, 1):
            parts.append(put(plane(name + f"_w{k}{side}", 1.0, 0.85, (side * 1.46, yy, 1.65), win, rot=(math.radians(90), 0, math.radians(90 * side)))))
    for p in parts:
        p.parent = root
    return root


def build(view):
    sc = bpy.context.scene
    c = coll()
    cam_loc = None
    floor_m = floor_mat()
    wood = principled("HallWood", (0.55, 0.36, 0.20), rough=0.45, coat=0.2)
    # floor
    put(plane("HallFloor", 120, 120, (0, 40, FLOOR), floor_m))
    # concrete structure — Halle Freyssinet style columns, beams and skylit roof
    col_m = concrete("Columns", (0.62, 0.60, 0.57), rough=0.85, scale=1.5)
    for y in (5.0, 13.0, 21.0, 29.0, 37.0):
        for x in (-11.0, -3.5, 3.5, 11.0):
            put(box(f"col{x}_{y}", (0.7, 0.7, 11.5), (x, y, FLOOR + 5.75), col_m))
    beam_m = concrete("Beams", (0.70, 0.68, 0.64), rough=0.85, scale=1.0)
    for y in (5.0, 13.0, 21.0, 29.0, 37.0):
        put(box(f"beam{y}", (30, 0.9, 1.4), (0, y, FLOOR + 11.2), beam_m))
    for x in (-11.0, -3.5, 3.5, 11.0):
        put(box(f"lbeam{x}", (0.6, 60, 0.9), (x, 25, FLOOR + 11.0), beam_m))
    sky = lit("Skylight", (0.80, 0.86, 1.0), 0.9, glossy=0.5, diffuse=0.05)
    roof = concrete("Roof", (0.55, 0.53, 0.50), rough=0.9, scale=0.8)
    for k in range(-6, 7):
        put(box(f"roofslab{k}", (2.0, 60, 0.3), (k * 2.6, 25, FLOOR + 12.4), roof))
        put(plane(f"skystrip{k}", 0.55, 60, (k * 2.6 + 1.3, 25, FLOOR + 12.5), sky, rot=(math.radians(180), 0, 0)))
    # far end wall with glazing
    put(plane("farwall", 60, 14, (0, 44, FLOOR + 7), lit("glazing", (0.80, 0.76, 0.70), 0.25), rot=(math.radians(90), 0, 0)))

    # communal tables, eclectic chairs, diners
    chair_cols = [(0.70, 0.18, 0.12), (0.12, 0.35, 0.55), (0.85, 0.65, 0.18), (0.20, 0.45, 0.32), (0.92, 0.88, 0.80), (0.08, 0.08, 0.08),
                  (0.55, 0.32, 0.18), (0.85, 0.45, 0.55)]
    rows = [(-1.2, 2.4), (2.6, 2.6), (-2.0, 4.6), (2.2, 5.0), (-0.4, 7.2), (3.8, 7.6), (-4.2, 6.9), (0.6, 10.0), (-3.0, 10.5), (4.2, 11.0), (-0.5, 13.5), (3.0, 14.5)]
    for i, (x, y) in enumerate(rows):
        t = long_table(f"tbl{i}", (x, y, FLOOR), RNG.uniform(-0.06, 0.06), wood)
        table_clutter(t, RNG)
        for k in range(6):
            side = 1 if k % 2 else -1
            cx = -1.1 + (k // 2) * 1.1 + RNG.uniform(-0.15, 0.15)
            ch = chair(f"ch{i}_{k}", (x + cx, y + side * 0.75, FLOOR), (0 if side > 0 else math.pi) + RNG.uniform(-0.4, 0.4), chair_cols[RNG.integers(len(chair_cols))])
            if RNG.uniform() < 0.62:
                person(f"p{i}_{k}", (x + cx, y + side * 0.62, FLOOR), seated=True, rot=(math.pi if side > 0 else 0) + RNG.uniform(-0.5, 0.5))
        # pendant bulbs above each table
        for k in range(3):
            pendant(f"pd{i}_{k}", (x - 1.0 + k * 1.0, y, FLOOR + 2.3 + RNG.uniform(-0.1, 0.2)), drop=2.0, strength=55)
    # warm pendants hanging just beyond our own table
    for k, x in enumerate((-1.3, -0.2, 0.9, 2.0)):
        pendant(f"ours{k}", (x, 1.7 + 0.2 * (k % 2), FLOOR + 2.15), drop=2.0, strength=60)
    # people walking / queueing at the counters
    for k in range(26):
        x = RNG.uniform(-8, 8)
        y = RNG.uniform(3.5, 19)
        person(f"walk{k}", (x, y, FLOOR), seated=False, rot=RNG.uniform(0, 6.28))
    # kiosks / food stalls along the back and sides
    kiosk("k_pizza", -1.0, 18.5, 4.2, 2.6, 3.0, (0.62, 0.12, 0.10), "sign_pizza.png")
    kiosk("k_pasta", 4.6, 18.0, 3.8, 2.6, 3.0, (0.12, 0.32, 0.25), "sign_pasta.png")
    kiosk("k_bar", -6.5, 17.0, 4.0, 2.6, 3.1, (0.10, 0.10, 0.14), "sign_bar.png")
    kiosk("k_caffe", 9.6, 15.5, 3.4, 2.4, 2.9, (0.45, 0.16, 0.24), "sign_caffe.png", rot=-0.35)
    kiosk("k_fritti", 10.6, 9.5, 3.2, 2.4, 2.9, (0.15, 0.28, 0.55), "sign_fritti.png", rot=-1.2)
    kiosk("k_gelato", -10.0, 11.0, 3.0, 2.4, 2.9, (0.90, 0.80, 0.72), "sign_gelato.png", rot=1.25)
    # the big sign over the hall
    sign("felicita_sign", "sign_felicita.png", (0.4, 14.5, FLOOR + 3.55), 5.0, strength=7.0)
    sign("vino_sign", "sign_vino.png", (-6.8, 16.0, FLOOR + 4.6), 1.8, strength=6.0)
    # train carriage seating on the left
    train_car("train", -7.6, 1.0, 14.0, rot=0.05)
    # festoon lighting criss-crossing
    for k in range(9):
        y = 2.5 + k * 2.3
        festoon(f"fest{k}", (-9.5, y, FLOOR + 4.6), (9.5, y + RNG.uniform(-1.5, 1.5), FLOOR + 4.4), n=22, sag=0.8, strength=28)
    # trees, planters, hanging greenery
    for (x, y) in [(-2.8, 3.6), (4.6, 4.0), (1.0, 6.0), (-5.6, 9.0), (6.4, 8.8), (1.6, 12.0), (-1.6, 16.2), (7.4, 13.8)]:
        potted_tree(f"tree{x}_{y}", (x, y), h=RNG.uniform(1.8, 2.8))
    for k in range(18):
        x = RNG.uniform(-9, 9)
        y = RNG.uniform(3, 20)
        leafy(f"hang{k}", (x, y, FLOOR + RNG.uniform(5.5, 8.5)), 0.6, n=35, tone=(0.18, 0.34, 0.12), squash=1.8)
    return c


def place(view, cam):
    """Yaw the hall to the camera heading and pitch it about the camera centre."""
    c = coll()
    root = bpy.data.objects.new("HallRoot", None)
    bpy.context.scene.collection.objects.link(root)
    for ob in c.objects:
        if ob.parent is None:
            ob.parent = root
    yaw = 0.0 if view == "desktop" else -math.pi / 2
    alpha = math.radians(24.0 if view == "desktop" else 27.0)
    cl = cam.location.copy()
    # local hall frame -> world: put origin under the camera's horizontal position
    base = Matrix.Translation((cl.x, cl.y, 0)) @ Matrix.Rotation(yaw, 4, "Z")
    right = (Matrix.Rotation(yaw, 3, "Z") @ Vector((1, 0, 0))).normalized()
    pitch = Matrix.Translation(cl) @ Matrix.Rotation(-alpha, 4, right) @ Matrix.Translation(-cl)
    root.matrix_world = pitch @ base
    return root


def set_pass(kind):
    """'fg': hall emitters barely light the tray. 'bg': they light the hall fully."""
    for m in bpy.data.materials:
        if not m.node_tree:
            continue
        n = m.node_tree.nodes.get("diffmul")
        if n is not None:
            n.inputs[1].default_value = n["fg_diffuse"] if kind == "fg" else 1.0
        g = m.node_tree.nodes.get("glossmul")
        if g is not None:
            # fewer stray bulb reflections smeared across the table top
            g.inputs[1].default_value = g["bg_gloss"] * (0.3 if kind == "fg" else 1.0)
