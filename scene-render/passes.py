"""Render passes + layer extraction for the web scene.

fg      sharp foreground (table, tray, food, props); hall invisible -> alpha
bg      the hall only, opened up to f/2 for a heavy, creamy defocus
base    fg with the six slices, tiramisu and Coke hidden from camera (shadows kept)
masks   flat-emission passes giving anti-aliased coverage for each clickable object
"""
import json
import os

import bpy
import numpy as np
from PIL import Image
from scipy import ndimage as ndi

FG_FSTOP = 4.5
BG_FSTOP = 1.6


def hall_objects():
    c = bpy.data.collections.get("Hall")
    return set(c.all_objects) if c else set()


def render(sc, path, transparent, samples, denoise=True, depth="8"):
    sc.render.film_transparent = transparent
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA" if transparent else "RGB"
    sc.render.image_settings.color_depth = depth
    sc.cycles.samples = samples
    sc.cycles.use_denoising = denoise
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)


def set_visibility(objs, camera=None, render=None):
    for o in objs:
        if camera is not None:
            o.visible_camera = camera
        if render is not None:
            o.hide_render = not render


def fg_and_bg(sc, out_dir, samples, view):
    hall = hall_objects()
    others = [o for o in sc.objects if o not in hall and o.type in ("MESH", "EMPTY")]
    cam = sc.camera
    # foreground
    import hall as H
    H.set_pass("fg")
    set_visibility(hall, camera=False)
    cam.data.dof.aperture_fstop = FG_FSTOP
    fg = os.path.join(out_dir, "fg.png")
    render(sc, fg, True, samples)
    # background: hall only
    set_visibility(hall, camera=True)
    set_visibility(others, render=False)
    cam.data.dof.aperture_fstop = BG_FSTOP
    H.set_pass("bg")
    bg = os.path.join(out_dir, "bg.png")
    render(sc, bg, False, max(samples // 2, 24))
    H.set_pass("fg")
    set_visibility(others, render=True)
    set_visibility(hall, camera=False)
    cam.data.dof.aperture_fstop = FG_FSTOP
    return fg, bg


def load(path):
    a = np.asarray(Image.open(path), np.float32) / (65535.0 if Image.open(path).mode.startswith("I;16") else 255.0)
    return a


def composite(fg_path, bg_path, out_path):
    fg = load(fg_path)
    bg = load(bg_path)[..., :3]
    a = fg[..., 3:4]
    out = fg[..., :3] * a + bg * (1 - a)
    Image.fromarray((np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8)).save(out_path)
    return out


def emission(name, color):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    e = nt.nodes.new("ShaderNodeEmission")
    e.inputs["Color"].default_value = (*color, 1)
    e.inputs["Strength"].default_value = 1.0
    o = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(e.outputs[0], o.inputs["Surface"])
    return m


def override_materials(objs, mat):
    for o in objs:
        if o.type != "MESH":
            continue
        for s in o.material_slots:
            s.link = "OBJECT"
            s.material = mat


def restore_materials(objs):
    for o in objs:
        if o.type != "MESH":
            continue
        for s in o.material_slots:
            s.link = "DATA"


def mask_pass(sc, out_dir, name, assignments, samples=48, hide=None):
    """assignments: list of (objects, (r,g,b)); everything else renders black."""
    hall = hall_objects()
    black = emission("MaskBlack", (0, 0, 0))
    all_fg = [o for o in sc.objects if o not in hall and o.type == "MESH"]
    override_materials(all_fg, black)
    for objs, col in assignments:
        override_materials([o for o in objs if o.type == "MESH"], emission("Mask_%.0f%.0f%.0f" % col, col))
    vs = sc.view_settings
    prev = (vs.view_transform, vs.look, sc.world.node_tree.nodes["Background"].inputs["Strength"].default_value)
    vs.view_transform = "Standard"
    vs.look = "None"
    sc.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.0
    set_visibility(hall, render=False)
    path = os.path.join(out_dir, f"mask_{name}.png")
    hidden = hide or []
    set_visibility(hidden, camera=False)
    render(sc, path, False, samples, denoise=False, depth="16")
    set_visibility(hidden, camera=True)
    set_visibility(hall, render=True)
    vs.view_transform, vs.look = prev[0], prev[1]
    sc.world.node_tree.nodes["Background"].inputs["Strength"].default_value = prev[2]
    restore_materials(all_fg)
    return path


def mask_bbox(paths, W, H, pad=48):
    m = None
    for p in paths:
        a = np.asarray(Image.open(p)).astype(np.float32)
        a = a.max(axis=2) if a.ndim == 3 else a
        m = a if m is None else np.maximum(m, a)
    ys, xs = np.nonzero(m > 0)
    x0, x1 = max(xs.min() - pad, 0), min(xs.max() + pad, W - 1)
    y0, y1 = max(ys.min() - pad, 0), min(ys.max() + pad, H - 1)
    return x0, y0, x1, y1


def render_all(sc, view, slices, groups, out_dir, args):
    samples = args.samples or 160
    tir = groups["tiramisu"]
    gl = groups["glass"]
    hall = hall_objects()
    W, H = sc.render.resolution_x, sc.render.resolution_y
    # masks first (cheap) so the base pass can be limited to the tray area
    dust = [o for o in tir if o.name.startswith("CocoaDust")]
    for d in dust:
        d.hide_render = True
    ma = mask_pass(sc, out_dir, "a", [([slices[0]], (1, 0, 0)), ([slices[1]], (0, 1, 0)), ([slices[2]], (0, 0, 1))])
    mb = mask_pass(sc, out_dir, "b", [([slices[3]], (1, 0, 0)), ([slices[4]], (0, 1, 0)), ([slices[5]], (0, 0, 1))])
    cola = [o for o in gl if o.name.startswith("Cola")]
    mc = mask_pass(sc, out_dir, "c", [(tir, (1, 0, 0)), (gl, (0, 1, 0))])
    # liquid only (glass, ice, straw, droplets hidden) — where the bubbles rise in the web layer
    mask_pass(sc, out_dir, "d", [(cola, (1, 1, 1))], hide=[o for o in gl if o not in cola and not o.name.startswith("Coaster")])
    for d in dust:
        d.hide_render = False
    if "masks" in (args.only or ""):
        return
    fg, bg = fg_and_bg(sc, out_dir, samples, view)
    composite(fg, bg, os.path.join(out_dir, "composite.png"))
    # base plate: clickable objects hidden from camera, shadows remain; tray area only
    x0, y0, x1, y1 = mask_bbox([ma, mb, mc], W, H)
    sc.render.use_border = True
    sc.render.use_crop_to_border = False
    sc.render.border_min_x = x0 / W
    sc.render.border_max_x = (x1 + 1) / W
    sc.render.border_min_y = 1 - (y1 + 1) / H
    sc.render.border_max_y = 1 - y0 / H
    set_visibility(hall, camera=False)
    set_visibility(slices + tir + gl, camera=False)
    sc.camera.data.dof.aperture_fstop = FG_FSTOP
    render(sc, os.path.join(out_dir, "base_crop.png"), True, max(samples * 2 // 3, 64))
    set_visibility(slices + tir + gl, camera=True)
    sc.render.use_border = False
    meta = {"view": view, "slices": [s["slice_id"] for s in slices], "base_border": [int(x0), int(y0), int(x1), int(y1)],
            "size": [W, H]}
    with open(os.path.join(out_dir, "passes.json"), "w") as f:
        json.dump(meta, f)
