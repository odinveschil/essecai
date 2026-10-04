"""Tray food other than the pizza (tiramisu, Coke Zero) and table clutter."""
import math
import os

import bpy
import bmesh
import numpy as np
from mathutils import Vector, Matrix, Euler

from common import OUT
from util import (
    new_mat, img_node, link, principled, lathe, obj_from_mesh, set_smooth, add_bevel, box, sphere,
    cylinder, plane, mesh_from_grid,
)

RNG = np.random.default_rng(99)


def obj_coords_mapping(nt, scale, loc=(0.5, 0.5, 0)):
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Location"].default_value = loc
    mp.inputs["Scale"].default_value = scale
    link(nt, tc.outputs["Object"], mp.inputs["Vector"])
    return mp


def parent_all(parent, objs):
    for o in objs:
        o.parent = parent


def empty(name, loc, rotz=0.0):
    e = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(e)
    e.location = loc
    e.rotation_euler.z = rotz
    return e


# ---------------------------------------------------------------- materials

def mat_glass(name="Glass", rough=0.0, fog=False):
    m, nt, b = new_mat(name)
    b.inputs["Base Color"].default_value = (0.98, 0.99, 0.98, 1)
    b.inputs["Transmission Weight"].default_value = 1.0
    b.inputs["IOR"].default_value = 1.5
    b.inputs["Roughness"].default_value = rough
    if fog:
        # chilled glass: the lower part (below the cola line) mists over
        tc = nt.nodes.new("ShaderNodeTexCoord")
        sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        link(nt, tc.outputs["Object"], sep.inputs[0])
        ramp = nt.nodes.new("ShaderNodeMapRange")
        ramp.inputs["From Min"].default_value = 0.112
        ramp.inputs["From Max"].default_value = 0.100
        ramp.inputs["To Min"].default_value = 0.0
        ramp.inputs["To Max"].default_value = 0.10
        link(nt, sep.outputs["Z"], ramp.inputs["Value"])
        noise = nt.nodes.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = 900
        link(nt, tc.outputs["Object"], noise.inputs["Vector"])
        mul = nt.nodes.new("ShaderNodeMath")
        mul.operation = "MULTIPLY"
        link(nt, ramp.outputs[0], mul.inputs[0])
        link(nt, noise.outputs["Fac"], mul.inputs[1])
        add = nt.nodes.new("ShaderNodeMath")
        add.operation = "ADD"
        link(nt, mul.outputs[0], add.inputs[0])
        link(nt, ramp.outputs[0], add.inputs[1])
        mul2 = nt.nodes.new("ShaderNodeMath")
        mul2.operation = "MULTIPLY"
        mul2.inputs[1].default_value = 0.5
        link(nt, add.outputs[0], mul2.inputs[0])
        link(nt, mul2.outputs[0], b.inputs["Roughness"])
        bump = nt.nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = 0.15
        link(nt, noise.outputs["Fac"], bump.inputs["Height"])
        link(nt, bump.outputs["Normal"], b.inputs["Normal"])
    return m


def mat_cola():
    m, nt, b = new_mat("Cola")
    b.inputs["Base Color"].default_value = (0.42, 0.16, 0.06, 1)
    b.inputs["Transmission Weight"].default_value = 1.0
    b.inputs["IOR"].default_value = 1.345
    b.inputs["Roughness"].default_value = 0.0
    out = nt.nodes["Material Output"]
    va = nt.nodes.new("ShaderNodeVolumeAbsorption")
    va.inputs["Color"].default_value = (0.52, 0.17, 0.05, 1)
    va.inputs["Density"].default_value = 1100.0
    link(nt, va.outputs[0], out.inputs["Volume"])
    return m


def mat_metal(name="Steel", rough=0.18, color=(0.85, 0.85, 0.83)):
    return principled(name, color, rough=rough, metallic=1.0)


def mat_tiramisu():
    m, nt, b = new_mat("Tiramisu")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    link(nt, tc.outputs["Object"], sep.inputs[0])
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 70
    noise.inputs["Detail"].default_value = 6
    link(nt, tc.outputs["Object"], noise.inputs["Vector"])
    # wobble the layer boundaries
    wob = nt.nodes.new("ShaderNodeMath")
    wob.operation = "MULTIPLY_ADD"
    wob.inputs[1].default_value = 0.0045
    wob.inputs[2].default_value = -0.00225
    link(nt, noise.outputs["Fac"], wob.inputs[0])
    zz = nt.nodes.new("ShaderNodeMath")
    zz.operation = "ADD"
    link(nt, sep.outputs["Z"], zz.inputs[0])
    link(nt, wob.outputs[0], zz.inputs[1])
    zn = nt.nodes.new("ShaderNodeMath")
    zn.operation = "DIVIDE"
    zn.inputs[1].default_value = 0.052
    link(nt, zz.outputs[0], zn.inputs[0])
    # layer colours bottom -> top
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    cr = ramp.color_ramp
    cr.interpolation = "LINEAR"
    stops = [
        (0.00, (0.13, 0.06, 0.025)), (0.07, (0.19, 0.09, 0.035)), (0.30, (0.30, 0.15, 0.06)),
        (0.335, (0.90, 0.83, 0.66)), (0.55, (0.93, 0.87, 0.71)), (0.585, (0.22, 0.11, 0.045)),
        (0.78, (0.34, 0.18, 0.08)), (0.815, (0.92, 0.85, 0.69)), (0.955, (0.90, 0.82, 0.66)), (0.985, (0.16, 0.08, 0.035)),
    ]
    cr.elements[0].position = stops[0][0]
    cr.elements[0].color = (*stops[0][1], 1)
    cr.elements[1].position = stops[1][0]
    cr.elements[1].color = (*stops[1][1], 1)
    for p, c in stops[2:]:
        e = cr.elements.new(p)
        e.color = (*c, 1)
    link(nt, zn.outputs[0], ramp.inputs[0])
    # sponge pores
    vor = nt.nodes.new("ShaderNodeTexVoronoi")
    vor.inputs["Scale"].default_value = 520
    link(nt, tc.outputs["Object"], vor.inputs["Vector"])
    pores = nt.nodes.new("ShaderNodeMapRange")
    pores.inputs["From Min"].default_value = 0.0
    pores.inputs["From Max"].default_value = 0.35
    pores.inputs["To Min"].default_value = 0.65
    pores.inputs["To Max"].default_value = 1.08
    link(nt, vor.outputs["Distance"], pores.inputs["Value"])
    mulc = nt.nodes.new("ShaderNodeMix")
    mulc.data_type = "RGBA"
    mulc.blend_type = "MULTIPLY"
    mulc.inputs["Factor"].default_value = 0.6
    link(nt, ramp.outputs[0], mulc.inputs[6])
    link(nt, pores.outputs[0], mulc.inputs[7])
    # cocoa top
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    sepn = nt.nodes.new("ShaderNodeSeparateXYZ")
    link(nt, geo.outputs["Normal"], sepn.inputs[0])
    topf = nt.nodes.new("ShaderNodeMapRange")
    topf.inputs["From Min"].default_value = 0.45
    topf.inputs["From Max"].default_value = 0.75
    link(nt, sepn.outputs["Z"], topf.inputs["Value"])
    cn = nt.nodes.new("ShaderNodeTexNoise")
    cn.inputs["Scale"].default_value = 900
    cn.inputs["Detail"].default_value = 6
    link(nt, tc.outputs["Object"], cn.inputs["Vector"])
    cocoa = nt.nodes.new("ShaderNodeValToRGB")
    cocoa.color_ramp.elements[0].position = 0.35
    cocoa.color_ramp.elements[0].color = (0.11, 0.05, 0.025, 1)
    cocoa.color_ramp.elements[1].position = 0.7
    cocoa.color_ramp.elements[1].color = (0.30, 0.16, 0.08, 1)
    link(nt, cn.outputs["Fac"], cocoa.inputs[0])
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    link(nt, topf.outputs[0], mix.inputs["Factor"])
    link(nt, mulc.outputs[2], mix.inputs[6])
    link(nt, cocoa.outputs[0], mix.inputs[7])
    link(nt, mix.outputs[2], b.inputs["Base Color"])
    # cream gets subsurface, cocoa is very matte
    creamf = nt.nodes.new("ShaderNodeValToRGB")
    ce = creamf.color_ramp
    ce.interpolation = "CONSTANT"
    ce.elements[0].position = 0.0
    ce.elements[0].color = (0, 0, 0, 1)
    ce.elements[1].position = 0.335
    ce.elements[1].color = (1, 1, 1, 1)
    e = ce.elements.new(0.57)
    e.color = (0, 0, 0, 1)
    e = ce.elements.new(0.80)
    e.color = (1, 1, 1, 1)
    e = ce.elements.new(0.97)
    e.color = (0, 0, 0, 1)
    link(nt, zn.outputs[0], creamf.inputs[0])
    sss = nt.nodes.new("ShaderNodeMath")
    sss.operation = "MULTIPLY"
    sss.inputs[1].default_value = 0.6
    link(nt, creamf.outputs[0], sss.inputs[0])
    link(nt, sss.outputs[0], b.inputs["Subsurface Weight"])
    b.inputs["Subsurface Radius"].default_value = (1.0, 0.8, 0.6)
    b.inputs["Subsurface Scale"].default_value = 0.003
    rr = nt.nodes.new("ShaderNodeMapRange")
    rr.inputs["To Min"].default_value = 0.55
    rr.inputs["To Max"].default_value = 0.95
    link(nt, topf.outputs[0], rr.inputs["Value"])
    rmix = nt.nodes.new("ShaderNodeMath")
    rmix.operation = "MULTIPLY_ADD"
    rmix.inputs[1].default_value = -0.25
    link(nt, creamf.outputs[0], rmix.inputs[0])
    link(nt, rr.outputs[0], rmix.inputs[2])
    link(nt, rmix.outputs[0], b.inputs["Roughness"])
    b.inputs["Sheen Weight"].default_value = 0.08
    b.inputs["Sheen Roughness"].default_value = 0.6
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Distance"].default_value = 0.0012
    link(nt, cn.outputs["Fac"], bump.inputs["Height"])
    link(nt, bump.outputs["Normal"], b.inputs["Normal"])
    return m


def mat_cocoa_dust():
    m, nt, b = new_mat("CocoaDust")
    b.inputs["Base Color"].default_value = (0.16, 0.08, 0.04, 1)
    b.inputs["Roughness"].default_value = 0.95
    tc = nt.nodes.new("ShaderNodeTexCoord")
    n = nt.nodes.new("ShaderNodeTexNoise")
    n.inputs["Scale"].default_value = 2600
    n.inputs["Detail"].default_value = 1
    link(nt, tc.outputs["Object"], n.inputs["Vector"])
    n2 = nt.nodes.new("ShaderNodeTexNoise")
    n2.inputs["Scale"].default_value = 30
    link(nt, tc.outputs["Object"], n2.inputs["Vector"])
    # density falls off away from the cake
    grad = nt.nodes.new("ShaderNodeTexGradient")
    grad.gradient_type = "SPHERICAL"
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (15, 15, 15)
    link(nt, tc.outputs["Object"], mp.inputs["Vector"])
    link(nt, mp.outputs["Vector"], grad.inputs["Vector"])
    a = nt.nodes.new("ShaderNodeMath")
    a.operation = "MULTIPLY"
    link(nt, n.outputs["Fac"], a.inputs[0])
    link(nt, n2.outputs["Fac"], a.inputs[1])
    a2 = nt.nodes.new("ShaderNodeMath")
    a2.operation = "MULTIPLY"
    link(nt, a.outputs[0], a2.inputs[0])
    link(nt, grad.outputs["Fac"], a2.inputs[1])
    thr = nt.nodes.new("ShaderNodeMapRange")
    thr.inputs["From Min"].default_value = 0.10
    thr.inputs["From Max"].default_value = 0.22
    link(nt, a2.outputs[0], thr.inputs["Value"])
    link(nt, thr.outputs[0], b.inputs["Alpha"])
    return m


# ---------------------------------------------------------------- tiramisu

def build_tiramisu(center, rot):
    root = empty("TiramisuRoot", (center.x, center.y, 0.004), math.radians(rot))
    objs = []
    # plate
    pm = principled("Ceramic", (0.95, 0.93, 0.88), rough=0.06, coat=0.5, spec=0.6)
    nt = pm.node_tree
    b = nt.nodes["Principled BSDF"]
    tex = img_node(nt, "plate_print.jpg")
    mp = obj_coords_mapping(nt, (1 / 0.2, 1 / 0.2, 1))
    link(nt, mp.outputs["Vector"], tex.inputs["Vector"])
    link(nt, tex.outputs["Color"], b.inputs["Base Color"])
    prof = [(0.0, 0.0035), (0.048, 0.0035), (0.052, 0.0), (0.058, 0.0), (0.062, 0.0035), (0.088, 0.0115), (0.0955, 0.0158),
            (0.0965, 0.0172), (0.0952, 0.0186), (0.092, 0.0184), (0.075, 0.0105), (0.069, 0.0082), (0.06, 0.0075), (0.0, 0.0075)]
    plate = lathe("Plate", prof, segs=128, mat=pm)
    objs.append(plate)
    # tiramisu portion: subdivided box with messy sides
    me = bpy.data.meshes.new("Tiramisu")
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=22, use_grid_fill=True)
    w, d, h = 0.078, 0.070, 0.052
    rng = np.random.default_rng(5)
    from scipy import ndimage as ndi
    nz = ndi.zoom(rng.standard_normal((9, 9, 9)), 5, order=3)
    def nval(p):
        i = np.clip(((np.array(p) + 0.6) / 1.2 * (nz.shape[0] - 1)).astype(int), 0, nz.shape[0] - 1)
        return nz[i[0], i[1], i[2]]
    for v in bm.verts:
        x, y, z = v.co
        n = nval((x, y, z))
        nx, ny = x * w, y * d
        zz = (z + 0.5) * h
        # sides bulge where cream layers are, top sags at the edges
        side = max(abs(x), abs(y)) > 0.49
        if side and z > -0.49:
            bulge = 0.0016 * math.sin((zz / h) * math.pi * 4.2) + 0.0022 * n
            k = Vector((x, y, 0)).normalized()
            nx += k.x * bulge
            ny += k.y * bulge
        if z > 0.49:
            edge = max(abs(x), abs(y)) * 2
            zz += -0.0045 * edge ** 4 + 0.0018 * n
        v.co = (nx, ny, max(zz, 0.0))
    bm.to_mesh(me)
    bm.free()
    tir = obj_from_mesh("Tiramisu", me)
    tir.location = (0.004, 0.006, 0.0076)
    tir.rotation_euler.z = math.radians(-9)
    add_bevel(tir, 0.0025, 3)
    set_smooth(tir)
    tir.data.materials.append(mat_tiramisu())
    objs.append(tir)
    # cocoa dust on the plate
    dust = plane("CocoaDust", 0.15, 0.15, loc=(0.0, 0.0, 0.0079), mat=mat_cocoa_dust())
    objs.append(dust)
    # dessert spoon resting on the plate
    sp = build_spoon()
    sp.location = (0.052, -0.020, 0.0105)
    sp.rotation_euler = Euler((0, math.radians(-6), math.radians(68)))
    objs.append(sp)
    parent_all(root, objs)
    return root, objs


def build_spoon():
    steel = mat_metal("SpoonSteel", 0.12)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, radius=1.0)
    for v in bm.verts:
        x, y, z = v.co
        v.co = (x * 0.018, y * 0.0125, (z * 0.004 if z < 0 else z * 0.0012))
    # handle
    handle = bmesh.new()
    me = bpy.data.meshes.new("Spoon")
    bm.to_mesh(me)
    bm.free()
    bowl = obj_from_mesh("Spoon", me)
    set_smooth(bowl)
    bowl.data.materials.append(steel)
    h = box("SpoonHandle", (0.085, 0.0065, 0.0016), loc=(0.058, 0, 0.0035), mat=steel, bevel=0.0007, rot=(0, math.radians(-7), 0))
    h.parent = bowl
    return bowl


# ---------------------------------------------------------------- coke zero

def glass_outer_r(z):
    return 0.0312 + (z - 0.002) / 0.148 * 0.0038


def build_coke(center, rot):
    root = empty("CokeRoot", (center.x, center.y, 0.004), math.radians(rot))
    objs = []
    # coaster
    cm, nt, b = new_mat("Coaster")
    tex = img_node(nt, "coaster.jpg")
    mp = obj_coords_mapping(nt, (1 / 0.12, 1 / 0.12, 1))
    link(nt, mp.outputs["Vector"], tex.inputs["Vector"])
    link(nt, tex.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.7
    coaster = box("Coaster", (0.12, 0.12, 0.0032), loc=(0, 0, 0.0016), mat=cm, bevel=0.0006)
    objs.append(coaster)
    z0 = 0.0032
    gm = mat_glass("GlassChilled", fog=True)
    prof = [(0.0, 0.0), (0.0296, 0.0), (0.0310, 0.0015)]
    for k in range(1, 25):
        z = 0.0015 + k / 24 * 0.1485
        prof.append((glass_outer_r(z), z))
    prof += [(0.0349, 0.1505), (0.0336, 0.1508), (0.0326, 0.1500)]
    for k in range(24, -1, -1):
        z = 0.012 + k / 24 * (0.148 - 0.012)
        prof.append((glass_outer_r(z) - 0.0027, z))
    prof += [(0.025, 0.0112), (0.0, 0.0108)]
    g = lathe("Glass", prof, segs=128, mat=gm)
    g.location.z = z0
    objs.append(g)
    # cola with a small meniscus
    level = 0.112
    lp = [(0.0, 0.0112), (0.025, 0.0114)]
    for k in range(0, 21):
        z = 0.012 + k / 20 * (level - 0.012)
        lp.append((glass_outer_r(z) - 0.0024, z))
    rt = glass_outer_r(level) - 0.0024
    lp += [(rt - 0.0006, level + 0.0012), (rt - 0.002, level + 0.0004), (0.0, level)]
    cola = lathe("Cola", lp, segs=96, mat=mat_cola())
    cola.location.z = z0
    objs.append(cola)
    # ice
    ice_m = mat_glass("Ice", rough=0.06)
    ice_m.node_tree.nodes["Principled BSDF"].inputs["IOR"].default_value = 1.31
    nti = ice_m.node_tree
    bi = nti.nodes["Principled BSDF"]
    tci = nti.nodes.new("ShaderNodeTexCoord")
    nzi = nti.nodes.new("ShaderNodeTexNoise")
    nzi.inputs["Scale"].default_value = 160
    link(nti, tci.outputs["Object"], nzi.inputs["Vector"])
    bmp = nti.nodes.new("ShaderNodeBump")
    bmp.inputs["Strength"].default_value = 0.25
    link(nti, nzi.outputs["Fac"], bmp.inputs["Height"])
    link(nti, bmp.outputs["Normal"], bi.inputs["Normal"])
    ice_specs = [((0.008, 0.006, level + 0.004), (12, 25, 30)), ((-0.010, 0.007, level + 0.002), (-18, 8, 70)),
                 ((0.002, -0.011, level + 0.0035), (6, -20, 10)), ((-0.006, -0.004, level - 0.020), (30, 40, 15)),
                 ((0.010, -0.002, level - 0.028), (-25, 15, 55))]
    for i, (p, r) in enumerate(ice_specs):
        s = 0.0205 - 0.0012 * i
        c = box(f"Ice{i}", (s, s * 0.95, s * 0.9), loc=(p[0], p[1], p[2] + z0), mat=ice_m, bevel=0.0028,
                rot=tuple(math.radians(a) for a in r))
        c.modifiers["Bevel"].segments = 3
        set_smooth(c)
        objs.append(c)
    # straw — black, a quiet Coke Zero wink
    straw_m = principled("Straw", (0.02, 0.02, 0.022), rough=0.25, coat=0.4)
    straw = cylinder("Straw", 0.0034, 0.215, loc=(-0.009, 0.012, 0.118 + z0), mat=straw_m, segs=24,
                     rot=(math.radians(-11), math.radians(-9), 0))
    set_smooth(straw)
    objs.append(straw)
    stripe = principled("StrawStripe", (0.70, 0.03, 0.05), rough=0.3, coat=0.4)
    st = cylinder("StrawBand", 0.00345, 0.006, loc=(0, 0, 0.09), mat=stripe, segs=24)
    st.parent = straw
    objs.append(st)
    # bubbles + foam ring at the meniscus
    bub_m = principled("Bubble", (1, 1, 1), rough=0.03, transmission=1.0, ior=1.1)
    foam_m = principled("Foam", (0.62, 0.45, 0.30), rough=0.25, transmission=0.4, ior=1.2)
    bub_me = None
    for i in range(70):
        z = RNG.uniform(0.02, level - 0.004)
        a = RNG.uniform(0, 2 * math.pi)
        rr = glass_outer_r(z) - 0.0024 - RNG.uniform(0.0003, 0.0012)
        rad = RNG.uniform(0.00035, 0.0009)
        s_ = sphere(f"Bub{i}", rad, loc=(rr * math.cos(a), rr * math.sin(a), z + z0), mat=bub_m, segs=10, rings=6)
        objs.append(s_)
    for i in range(170):
        a = RNG.uniform(0, 2 * math.pi)
        rr = glass_outer_r(level) - 0.0026 - RNG.uniform(0, 0.0022) ** 1.5 * 3
        rad = RNG.uniform(0.0005, 0.0013)
        s_ = sphere(f"Foam{i}", rad, loc=(rr * math.cos(a), rr * math.sin(a), level + z0 + 0.0008), mat=foam_m, segs=10, rings=6,
                    scale=(1, 1, 0.6))
        objs.append(s_)
    # condensation droplets on the outside, below the cola line
    water = principled("Droplet", (1, 1, 1), rough=0.02, transmission=1.0, ior=1.33)
    drop_me = None
    for i in range(520):
        z = RNG.uniform(0.006, level - 0.002) if i < 470 else RNG.uniform(level - 0.01, level + 0.02)
        a = RNG.uniform(0, 2 * math.pi)
        rad = RNG.choice([RNG.uniform(0.00025, 0.0006), RNG.uniform(0.0006, 0.0014), RNG.uniform(0.0014, 0.0022)], p=[0.6, 0.33, 0.07])
        rr = glass_outer_r(z) + rad * 0.1
        s_ = sphere(f"Drop{i}", rad, loc=(rr * math.cos(a), rr * math.sin(a), z + z0), mat=water, segs=12, rings=6,
                    scale=(0.45, 1, 1.15 if rad > 0.0014 else 1))
        s_.rotation_euler.z = a
        objs.append(s_)
    # a few running drips
    for i in range(5):
        a = RNG.uniform(-2.4, -0.7)
        z = RNG.uniform(0.02, 0.07)
        L = RNG.uniform(0.012, 0.03)
        rr = glass_outer_r(z)
        s_ = sphere(f"Drip{i}", 0.0011, loc=(rr * math.cos(a), rr * math.sin(a), z + z0), mat=water, segs=12, rings=8,
                    scale=(0.4, 1, L / 0.0022))
        s_.rotation_euler.z = a
        objs.append(s_)
    parent_all(root, objs)
    return root, objs


# ---------------------------------------------------------------- table clutter

def build_clutter(view):
    out = []
    white = principled("NapkinPaper", (0.93, 0.91, 0.86), rough=0.85, sss=0.1)
    # napkin, folded, crumpled slightly, with cutlery
    u = np.linspace(-0.07, 0.07, 60)
    v = np.linspace(-0.11, 0.11, 90)
    X, Y = np.meshgrid(u, -v)
    rng = np.random.default_rng(12)
    from scipy import ndimage as ndi
    nz = ndi.zoom(rng.standard_normal((8, 12)), (90 / 8, 60 / 12), order=3)[:90, :60]
    Z = 0.0025 + 0.0012 * nz + 0.002 * np.exp(-((X - 0.02) / 0.01) ** 2)
    nap = mesh_from_grid("Napkin", X, Y, Z)
    nap.data.materials.append(white)
    set_smooth(nap)
    nap.location = (-0.56, -0.12, 0)
    nap.rotation_euler.z = math.radians(-8)
    if view == "desktop":
        # folded on the empty back-left corner of the tray
        nap.scale = (0.86, 0.82, 1)
        nap.location = (-0.292, 0.112, 0.004)
        nap.rotation_euler.z = math.radians(-6)
    out.append(nap)
    steel = mat_metal("Cutlery", 0.2)
    fork = build_fork(steel)
    fork.location = (-0.545, -0.13, 0.0045)
    fork.rotation_euler.z = math.radians(84)
    knife = box("Knife", (0.21, 0.017, 0.0022), loc=(-0.585, -0.12, 0.0047), mat=steel, bevel=0.0008, rot=(0, 0, math.radians(86)))
    if view == "desktop":
        fork.location = (-0.275, 0.112, 0.0098)
        fork.rotation_euler.z = math.radians(-84)
        fork.scale = (0.85, 0.85, 1)
        knife.location = (-0.31, 0.112, 0.0098)
        knife.rotation_euler.z = math.radians(-86)
        knife.scale = (0.82, 1, 1)
    out += [fork, knife]
    # receipt, curling
    rm, nt, b = new_mat("Receipt")
    tex = img_node(nt, "receipt.jpg")
    link(nt, tex.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.6
    b.inputs["Subsurface Weight"].default_value = 0.05
    u = np.linspace(-0.032, 0.032, 30)
    v = np.linspace(-0.075, 0.075, 80)
    X, Y = np.meshgrid(u, -v)
    Z = 0.0006 + np.clip(-Y - 0.03, 0, None) ** 2 * 6.0 + np.clip(Y - 0.05, 0, None) ** 2 * 3
    rc = mesh_from_grid("Receipt", X, Y, Z, (X + 0.032) / 0.064, (Y + 0.075) / 0.15)
    rc.data.materials.append(rm)
    set_smooth(rc)
    rc.location = (0.312, -0.135, 0.004)  # tucked on the tray, front-right
    rc.rotation_euler.z = math.radians(-6 if view == "desktop" else 84)
    out.append(rc)
    # espresso cup + saucer
    cer = principled("EspressoCeramic", (0.93, 0.91, 0.86), rough=0.08, coat=0.6)
    saucer = lathe("Saucer", [(0, 0.002), (0.05, 0.002), (0.056, 0.0), (0.062, 0.006), (0.066, 0.009), (0.064, 0.0095), (0.03, 0.0055), (0, 0.0055)], 64, cer)
    cup = lathe("Cup", [(0, 0.005), (0.022, 0.005), (0.03, 0.02), (0.033, 0.055), (0.0315, 0.0555), (0.029, 0.02), (0.02, 0.012), (0, 0.012)], 64, cer)
    crema = cylinder("Crema", 0.0292, 0.001, loc=(0, 0, 0.046), mat=principled("Crema", (0.45, 0.26, 0.12), rough=0.3), segs=48)
    esp = empty("Espresso", (-0.64, 0.27, 0.0))
    for o in (saucer, cup, crema):
        o.parent = esp
    cup.location.z = 0.004
    crema.location.z = 0.046
    out += [saucer, cup, crema]
    # water glass
    wg = lathe("WaterGlass", [(0, 0), (0.033, 0), (0.036, 0.095), (0.034, 0.095), (0.031, 0.006), (0, 0.005)], 96, mat_glass("Tumbler"))
    wg.location = (0.62, 0.30, 0.0)
    water = lathe("Water", [(0, 0.0055), (0.0315, 0.006), (0.0335, 0.06), (0, 0.06)], 64, principled("Water", (1, 1, 1), rough=0, transmission=1.0, ior=1.33))
    water.location = (0.62, 0.30, 0.0)
    out += [wg, water]
    # parmesan shaker
    jar = lathe("ParmJar", [(0, 0), (0.028, 0), (0.03, 0.006), (0.03, 0.085), (0.0275, 0.085), (0.0275, 0.006), (0, 0.004)], 64, mat_glass("JarGlass"))
    parm = cylinder("Parm", 0.0272, 0.05, loc=(0, 0, 0.03), mat=principled("Parmigiano", (0.93, 0.86, 0.62), rough=0.9), segs=48)
    cap = lathe("ParmCap", [(0, 0.1), (0.026, 0.1), (0.0305, 0.096), (0.0312, 0.08), (0.0302, 0.08), (0, 0.08)], 64, mat_metal("CapSteel", 0.25))
    parm_e = empty("Parmesan", (0.10, 0.36, 0.0))
    for o in (jar, parm, cap):
        o.parent = parm_e
    out += [jar, parm, cap]
    # ESSEC notebook + pen
    nm, nt, b = new_mat("Notebook")
    tex = img_node(nt, "notebook.jpg")
    mp = obj_coords_mapping(nt, (1 / 0.15, 1 / 0.21, 1))
    link(nt, mp.outputs["Vector"], tex.inputs["Vector"])
    link(nt, tex.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.55
    nb = box("NotebookBody", (0.15, 0.21, 0.012), loc=(-0.80, 0.08, 0.006), mat=nm, bevel=0.002, rot=(0, 0, math.radians(14)))
    pen = cylinder("Pen", 0.0045, 0.14, loc=(-0.70, 0.02, 0.0045), mat=principled("PenBody", (0.05, 0.05, 0.06), rough=0.3, coat=0.5), segs=16,
                   rot=(0, math.radians(90), math.radians(70)))
    out += [nb, pen]
    # bread crumbs on the table
    crumb = principled("Crumbs", (0.82, 0.62, 0.36), rough=0.8)
    for i in range(46):
        x = RNG.uniform(-0.42, 0.46)
        y = RNG.uniform(-0.33, -0.27) if RNG.uniform() < 0.7 else RNG.uniform(-0.27, 0.3) * 0 + RNG.uniform(0.27, 0.33)
        s = RNG.uniform(0.0008, 0.0024)
        c = sphere(f"Crumb{i}", s, loc=(x, y, s * 0.5), mat=crumb, segs=6, rings=4, scale=(1, RNG.uniform(0.6, 1.2), 0.7))
        out.append(c)
    return out


def build_fork(steel):
    me = bpy.data.meshes.new("Fork")
    bm = bmesh.new()
    def add_box(cx, cy, sx, sy, sz):
        r = bmesh.ops.create_cube(bm, size=1.0)
        for v in r["verts"]:
            v.co.x = v.co.x * sx + cx
            v.co.y = v.co.y * sy + cy
            v.co.z = v.co.z * sz
    add_box(0.0, 0, 0.11, 0.012, 0.0024)
    add_box(-0.075, 0, 0.04, 0.022, 0.0018)
    for k in range(4):
        add_box(-0.11, -0.0085 + k * 0.0057, 0.035, 0.0026, 0.0016)
    bm.to_mesh(me)
    bm.free()
    ob = obj_from_mesh("Fork", me)
    add_bevel(ob, 0.0005, 2)
    ob.data.materials.append(steel)
    return ob


def build_neighbours(view):
    """Other people's trays across the communal table (soft in the focus falloff)."""
    out = []
    import scene as S  # noqa
    return out


def build_all(view, rot, plate_c, glass_c):
    t_root, t_objs = build_tiramisu(plate_c, rot)
    c_root, c_objs = build_coke(glass_c, rot)
    clutter = build_clutter(view)
    return {"tiramisu": t_objs, "glass": c_objs, "clutter": clutter}
