"""Builds the La Felicità table scene in Blender (bpy) and renders it.

Usage:
  python3 scene.py --view desktop --mode preview      # quick look
  python3 scene.py --view desktop --mode final        # beauty + base + masks
"""
import argparse
import json
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Vector, Matrix, Euler
from scipy import ndimage as ndi

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import OUT  # noqa: E402

import hall  # noqa: E402
import props  # noqa: E402
from util import (  # noqa: E402
    lathe, mesh_from_grid, new_mat, img_node, link, principled, obj_from_mesh, set_smooth, add_bevel,
)

TRAY_TOP = 0.004  # tray floor height above table
PAPER_Z = TRAY_TOP + 0.0006
PIZZA_C = Vector((0.0, 0.0))
PLATE_C = Vector((-0.262, -0.115))
GLASS_C = Vector((0.300, 0.100))
GAP = 0.0010


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.use_denoising = True
    sc.cycles.denoiser = "OPENIMAGEDENOISE"
    sc.cycles.caustics_reflective = False
    sc.cycles.caustics_refractive = False
    sc.cycles.max_bounces = 12
    sc.cycles.diffuse_bounces = 3
    sc.cycles.glossy_bounces = 4
    sc.cycles.transmission_bounces = 14
    sc.cycles.transparent_max_bounces = 16
    sc.cycles.volume_bounces = 0
    sc.cycles.blur_glossy = 1.0
    sc.cycles.sample_clamp_indirect = 6.0
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.adaptive_threshold = 0.012
    sc.view_settings.view_transform = os.environ.get("VT", "AgX")
    if sc.view_settings.view_transform == "AgX":
        sc.view_settings.look = os.environ.get("LOOK", "AgX - Medium High Contrast")
    sc.view_settings.exposure = 0.0
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_depth = "8"
    world = bpy.data.worlds.new("World")
    sc.world = world
    nt = world.node_tree
    bg = nt.nodes["Background"]
    bg.inputs["Color"].default_value = (0.05, 0.035, 0.022, 1)
    bg.inputs["Strength"].default_value = 0.22
    return sc


# --------------------------------------------------------------------------
# materials
# --------------------------------------------------------------------------

def mat_pizza():
    m, nt, bsdf = new_mat("Pizza")
    alb = img_node(nt, "pizza_albedo.png", "sRGB")
    props_ = img_node(nt, "pizza_props.png", "Non-Color")
    det = img_node(nt, "pizza_detail.png", "Non-Color")
    for n in (alb, props_, det):
        n.interpolation = "Cubic"
    link(nt, alb.outputs["Color"], bsdf.inputs["Base Color"])
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    link(nt, props_.outputs["Color"], sep.inputs[0])
    link(nt, sep.outputs[0], bsdf.inputs["Roughness"])
    sssm = nt.nodes.new("ShaderNodeMath")
    sssm.operation = "MULTIPLY"
    sssm.inputs[1].default_value = 1.0
    link(nt, sep.outputs[1], sssm.inputs[0])
    link(nt, sssm.outputs[0], bsdf.inputs["Subsurface Weight"])
    bsdf.inputs["Subsurface Radius"].default_value = (1.0, 0.55, 0.3)
    bsdf.inputs["Subsurface Scale"].default_value = 0.004
    bsdf.inputs["Specular IOR Level"].default_value = 0.55
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Distance"].default_value = 0.002
    bump.inputs["Strength"].default_value = 0.7
    sub = nt.nodes.new("ShaderNodeMath")
    sub.operation = "SUBTRACT"
    sub.inputs[1].default_value = 0.5
    link(nt, det.outputs["Color"], sub.inputs[0])
    link(nt, sub.outputs[0], bump.inputs["Height"])
    link(nt, bump.outputs["Normal"], bsdf.inputs["Normal"])
    return m


def mat_crumb():
    m, nt, bsdf = new_mat("Crumb")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    vor = nt.nodes.new("ShaderNodeTexVoronoi")
    vor.inputs["Scale"].default_value = 900
    link(nt, tc.outputs["Object"], vor.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.05
    ramp.color_ramp.elements[0].color = (0.22, 0.13, 0.07, 1)
    ramp.color_ramp.elements[1].position = 0.25
    ramp.color_ramp.elements[1].color = (0.42, 0.22, 0.12, 1)
    link(nt, vor.outputs["Distance"], ramp.inputs[0])
    link(nt, ramp.outputs[0], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.85
    return m


def mat_image(name, file, rough=0.6, rough_file=None, height_file=None, bump_dist=0.001, colorspace="sRGB", coat=0.0, spec=0.5):
    m, nt, bsdf = new_mat(name)
    alb = img_node(nt, file, colorspace)
    link(nt, alb.outputs["Color"], bsdf.inputs["Base Color"])
    if rough_file:
        r = img_node(nt, rough_file, "Non-Color")
        link(nt, r.outputs["Color"], bsdf.inputs["Roughness"])
    else:
        bsdf.inputs["Roughness"].default_value = rough
    if height_file:
        h = img_node(nt, height_file, "Non-Color")
        b = nt.nodes.new("ShaderNodeBump")
        b.inputs["Distance"].default_value = bump_dist
        link(nt, h.outputs["Color"], b.inputs["Height"])
        link(nt, b.outputs["Normal"], bsdf.inputs["Normal"])
    bsdf.inputs["Coat Weight"].default_value = coat
    bsdf.inputs["Specular IOR Level"].default_value = spec
    return m


# --------------------------------------------------------------------------
# objects
# --------------------------------------------------------------------------

def build_table(view="desktop"):
    import bmesh
    me = bpy.data.meshes.new("Table")
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x *= 3.2
        v.co.y *= 0.92
        v.co.z = (v.co.z + 0.5) * 0.055 - 0.055
    bm.to_mesh(me)
    bm.free()
    ob = obj_from_mesh("Table", me)
    ob.location = (0.25, 0.06, 0)
    if view == "mobile":
        # looking down the length of the table: let it end so the hall shows
        for v in ob.data.vertices:
            v.co.x = min(v.co.x, 0.50)
    add_bevel(ob, 0.006, 3)
    mat = mat_image("Wood", "wood_albedo.jpg", rough_file="wood_rough.jpg", height_file="wood_height.png", bump_dist=0.0012, coat=0.15)
    nt = mat.node_tree
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Location"].default_value = (0.5, 0.5, 0)
    mp.inputs["Scale"].default_value = (1 / 3.2, 1 / 1.2, 1)
    link(nt, tc.outputs["Object"], mp.inputs["Vector"])
    for n in nt.nodes:
        if n.type == "TEX_IMAGE":
            link(nt, mp.outputs["Vector"], n.inputs["Vector"])
    ob.data.materials.append(mat)
    # legs (rarely seen)
    return ob


def rounded_rect(w, h, rc, n_corner=24):
    pts, nrm = [], []
    cs = [(w / 2 - rc, h / 2 - rc, 0), (-w / 2 + rc, h / 2 - rc, 90), (-w / 2 + rc, -h / 2 + rc, 180), (w / 2 - rc, -h / 2 + rc, 270)]
    for cx, cy, a0 in cs:
        for k in range(n_corner):
            a = math.radians(a0 + 90 * k / (n_corner - 1))
            pts.append((cx + rc * math.cos(a), cy + rc * math.sin(a)))
            nrm.append((math.cos(a), math.sin(a)))
    return np.array(pts), np.array(nrm)


def build_tray():
    w, h, rc = 0.80, 0.49, 0.045
    pts, nrm = rounded_rect(w - 0.05, h - 0.05, rc - 0.02)
    prof = [(0.0, TRAY_TOP), (0.008, TRAY_TOP + 0.002), (0.014, 0.012), (0.019, 0.0175), (0.023, 0.019), (0.027, 0.0178), (0.029, 0.012), (0.027, 0.002), (0.022, 0.0)]
    verts = []
    P = len(prof)
    n = len(pts)
    for i in range(n):
        for (o, z) in prof:
            verts.append((pts[i][0] + nrm[i][0] * o, pts[i][1] + nrm[i][1] * o, z))
    faces = []
    for i in range(n):
        i2 = (i + 1) % n
        for j in range(P - 1):
            faces.append((i * P + j, i2 * P + j, i2 * P + j + 1, i * P + j + 1))
    # floor
    c = len(verts)
    verts.append((0, 0, TRAY_TOP))
    for i in range(n):
        i2 = (i + 1) % n
        faces.append((c, i2 * P, i * P))
    me = bpy.data.meshes.new("Tray")
    me.from_pydata(verts, [], faces)
    me.update()
    ob = obj_from_mesh("Tray", me)
    set_smooth(ob)
    mat = mat_image("TrayMat", "tray_albedo.jpg", rough_file="tray_rough.jpg", spec=0.5)
    nt = mat.node_tree
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Location"].default_value = (0.5, 0.5, 0)
    mp.inputs["Scale"].default_value = (1 / 0.80, 1 / 0.50, 1)
    link(nt, tc.outputs["Object"], mp.inputs["Vector"])
    for nd in nt.nodes:
        if nd.type == "TEX_IMAGE":
            link(nt, mp.outputs["Vector"], nd.inputs["Vector"])
    ob.data.materials.append(mat)
    return ob


def build_paper(rot):
    from PIL import Image
    S = 0.44
    hm = np.asarray(Image.open(os.path.join(OUT, "paper_height.png")), np.float32) / 65535
    hm = ndi.zoom(hm, 220 / hm.shape[0], order=1)
    n = hm.shape[0]
    u = np.linspace(-S / 2, S / 2, n)
    X, Y = np.meshgrid(u, -u)
    r = np.hypot(X, Y)
    # paper lifts slightly at the corners, crinkle amplitude ~1.2 mm
    Z = PAPER_Z + (hm - 0.5) * 0.0016 + np.clip(r - 0.2, 0, None) ** 2 * 0.6
    Z = np.maximum(Z, TRAY_TOP + 0.0002)
    U = (X + S / 2) / S
    V = (Y + S / 2) / S
    ob = mesh_from_grid("Paper", X, Y, Z, U, V)
    ob.rotation_euler.z = math.radians(rot)
    mat = mat_image("PaperMat", "paper_albedo.jpg", rough_file="paper_rough.jpg", height_file="paper_height.png", bump_dist=0.0004, spec=0.3)
    ob.data.materials.append(mat)
    set_smooth(ob)
    return ob


def build_pizza(rot_deg):
    meta = json.load(open(os.path.join(OUT, "pizza_meta.json")))
    H = np.load(os.path.join(OUT, "pizza_height.npy"))
    ext = meta["ext"]
    M = H.shape[0]
    angs = np.array(meta["edge_angles"])
    ers = np.array(meta["edge_r"])

    def edge_r(phi):
        p = (phi + np.pi) % (2 * np.pi) - np.pi
        return np.interp(p, angs, ers, period=2 * np.pi)

    def sampleH(x, y):
        cols = (x + ext) / (2 * ext) * M - 0.5
        rows = (ext - y) / (2 * ext) * M - 0.5
        return ndi.map_coordinates(H, [rows, cols], order=1, mode="nearest")

    pm = mat_pizza()
    cm = mat_crumb()
    slices = []
    rot = math.radians(rot_deg)
    for sl in meta["slices"]:
        ang = math.radians(sl["angle"])
        na, nr = 240, 210
        phis = ang + np.linspace(-np.pi / 6, np.pi / 6, na)
        s = np.linspace(0, 1, nr) ** 0.85
        R = edge_r(phis)[None, :] * s[:, None]
        X = R * np.cos(phis)[None, :]
        Y = R * np.sin(phis)[None, :]
        Z = sampleH(X, Y)
        Z[-1, :] = 0.0012
        Z[-2, :] = np.minimum(Z[-2, :], 0.006)
        U = (X + ext) / (2 * ext)
        V = (Y + ext) / (2 * ext)
        bx, by = math.cos(ang) * GAP, math.sin(ang) * GAP
        verts = np.stack([X + bx, Y + by, Z], -1).reshape(-1, 3)
        uvs = np.stack([U, V], -1).reshape(-1, 2)
        idx = np.arange(nr * na).reshape(nr, na)
        quads = np.stack([idx[:-1, :-1], idx[1:, :-1], idx[1:, 1:], idx[:-1, 1:]], -1).reshape(-1, 4)
        faces = [tuple(q) for q in quads]
        mats = [0] * len(faces)
        # side walls at both cut edges (bread crumb)
        verts = list(map(tuple, verts))
        uvs = list(map(tuple, uvs))
        for col in (0, na - 1):
            base_ids = []
            for i in range(nr):
                vx, vy, vz = verts[idx[i, col]]
                verts.append((vx, vy, 0.0004))
                uvs.append((0.0, 0.0))
                base_ids.append(len(verts) - 1)
            for i in range(nr - 1):
                a, b = idx[i, col], idx[i + 1, col]
                c, d = base_ids[i + 1], base_ids[i]
                f = (b, a, d, c) if col == 0 else (a, b, c, d)
                faces.append(f)
                mats.append(1)
        me = bpy.data.meshes.new("Slice_" + sl["id"])
        me.from_pydata(verts, [], faces)
        uvl = me.uv_layers.new(name="UVMap")
        uva = np.array(uvs, np.float32)
        lv = np.zeros(len(me.loops), np.int64)
        me.loops.foreach_get("vertex_index", lv)
        uvl.data.foreach_set("uv", uva[lv].ravel())
        me.polygons.foreach_set("material_index", mats)
        me.update()
        ob = obj_from_mesh("Slice_" + sl["id"], me)
        ob.data.materials.append(pm)
        ob.data.materials.append(cm)
        set_smooth(ob)
        ob.location = (PIZZA_C.x, PIZZA_C.y, PAPER_Z + 0.0002)
        ob.rotation_euler.z = rot
        ob["slice_id"] = sl["id"]
        slices.append(ob)
    return slices


def build_camera(view):
    cam_data = bpy.data.cameras.new("Cam")
    cam = bpy.data.objects.new("Cam", cam_data)
    bpy.context.scene.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    cam_data.sensor_fit = "HORIZONTAL" if view == "desktop" else "VERTICAL"
    cam_data.sensor_width = 36
    cam_data.sensor_height = 36
    cam_data.dof.use_dof = True
    if view == "desktop":
        loc = Vector((0.0, -0.4604, 0.4446))  # 0.64 m from the pizza at 44 deg
        pitch = 38.0  # degrees below horizontal
        cam_data.lens = 23
        cam_data.shift_y = 0.0
        yaw = 0.0
    else:
        loc = Vector((-0.5395, 0.0, 0.5210))  # 0.75 m at 44 deg, looking along the tray
        pitch = 44.0
        cam_data.lens = 32
        cam_data.shift_y = 0.0
        yaw = -90.0
    cam.location = loc
    cam.rotation_euler = Euler((math.radians(90 - pitch), 0, math.radians(yaw)), "XYZ")
    target = Vector((PIZZA_C.x, PIZZA_C.y, 0.01))
    cam_data.dof.focus_distance = (target - loc).length
    cam_data.dof.aperture_fstop = 4.5
    return cam


def lights(view):
    sc = bpy.context.scene

    def area(name, loc, rot, size, energy, color):
        ld = bpy.data.lights.new(name, "AREA")
        ld.shape = "DISK"
        ld.size = size
        ld.energy = energy
        ld.color = color
        ob = bpy.data.objects.new(name, ld)
        sc.collection.objects.link(ob)
        ob.location = loc
        ob.rotation_euler = rot
        return ob

    def aim(ob, target):
        d = Vector(target) - ob.location
        ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()

    k = area("Key", (-0.45, 0.50, 1.25), (0, 0, 0), 0.7, 42, (1.0, 0.78, 0.55))
    aim(k, (0, 0, 0))
    f = area("Fill", (0.9, -0.9, 0.9), (0, 0, 0), 1.6, 7, (1.0, 0.86, 0.70))
    aim(f, (0, 0, 0))
    r = area("Rim", (0.6, 1.3, 0.7), (0, 0, 0), 0.8, 38, (1.0, 0.68, 0.40))
    aim(r, (0, 0, 0.05))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--view", default="desktop")
    ap.add_argument("--mode", default="preview")
    ap.add_argument("--res", type=float, default=None)
    ap.add_argument("--samples", type=int, default=None)
    ap.add_argument("--nohall", action="store_true")
    ap.add_argument("--only", default="")
    args = ap.parse_args()

    sc = reset()
    view = args.view
    rot = 0.0 if view == "desktop" else -90.0
    build_table(view)
    build_tray()
    build_paper(7.0 + rot)
    slices = build_pizza(rot)
    pc, gc = (PLATE_C, GLASS_C) if view == "desktop" else (Vector((-0.258, -0.035)), Vector((0.27, 0.075)))
    groups = props.build_all(view, rot, pc, gc)
    lights(view)
    cam = build_camera(view)
    if not args.nohall:
        hall.build(view)
        hall.place(view, cam)

    if view == "desktop":
        W, H = 2880, 1800
    else:
        W, H = 1290, 2580
    scale = args.res or (0.33 if args.mode == "preview" else 1.0)
    sc.render.resolution_x = int(W * scale)
    sc.render.resolution_y = int(H * scale)
    sc.render.resolution_percentage = 100
    sc.cycles.samples = args.samples or (48 if args.mode == "preview" else 160)

    out_dir = os.path.join(OUT, "render", view)
    os.makedirs(out_dir, exist_ok=True)
    import passes
    if args.mode == "preview":
        fg, bg = passes.fg_and_bg(sc, out_dir, sc.cycles.samples, view)
        passes.composite(fg, bg, os.path.join(out_dir, "preview.png"))
        return
    passes.render_all(sc, view, slices, groups, out_dir, args)


if __name__ == "__main__":
    main()
