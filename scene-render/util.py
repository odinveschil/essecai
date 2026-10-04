"""Small bpy helpers shared by the scene modules."""
import math
import os

import bpy
import numpy as np

from common import OUT

_IMG_CACHE = {}


def link(nt, a, b):
    nt.links.new(a, b)


def new_mat(name):
    m = bpy.data.materials.new(name)
    nt = m.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    if bsdf is None:
        bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
        out = nt.nodes.get("Material Output") or nt.nodes.new("ShaderNodeOutputMaterial")
        nt.links.new(bsdf.outputs[0], out.inputs["Surface"])
    return m, nt, bsdf


def principled(name, color, rough=0.5, metallic=0.0, transmission=0.0, ior=1.45, sss=0.0, coat=0.0, spec=0.5, emission=None, estrength=0.0, alpha=1.0):
    m, nt, b = new_mat(name)
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metallic
    b.inputs["Transmission Weight"].default_value = transmission
    b.inputs["IOR"].default_value = ior
    b.inputs["Subsurface Weight"].default_value = sss
    b.inputs["Coat Weight"].default_value = coat
    b.inputs["Specular IOR Level"].default_value = spec
    b.inputs["Alpha"].default_value = alpha
    if emission is not None:
        b.inputs["Emission Color"].default_value = (*emission, 1)
        b.inputs["Emission Strength"].default_value = estrength
    return m


def emission_mat(name, color, strength):
    m = bpy.data.materials.new(name)
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    e = nt.nodes.new("ShaderNodeEmission")
    e.inputs["Color"].default_value = (*color, 1)
    e.inputs["Strength"].default_value = strength
    o = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(e.outputs[0], o.inputs["Surface"])
    return m


def img_node(nt, file, colorspace="sRGB"):
    path = file if os.path.isabs(file) else os.path.join(OUT, file)
    key = (path, colorspace)
    if key not in _IMG_CACHE:
        img = bpy.data.images.load(path)
        img.colorspace_settings.name = colorspace
        _IMG_CACHE[key] = img
    n = nt.nodes.new("ShaderNodeTexImage")
    n.image = _IMG_CACHE[key]
    n.interpolation = "Linear"
    return n


def obj_from_mesh(name, me, coll=None):
    ob = bpy.data.objects.new(name, me)
    (coll or bpy.context.scene.collection).objects.link(ob)
    return ob


def set_smooth(ob):
    me = ob.data
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    me.update()


def add_bevel(ob, width, segs=2):
    m = ob.modifiers.new("Bevel", "BEVEL")
    m.width = width
    m.segments = segs
    m.limit_method = "ANGLE"
    return m


def lathe(name, profile, segs=96, mat=None, smooth=True, coll=None):
    """Revolve [(r, z), ...] around Z. Profile should run 'outside-in' for outward normals."""
    P = len(profile)
    verts = []
    for i in range(segs):
        a = 2 * math.pi * i / segs
        ca, sa = math.cos(a), math.sin(a)
        for (r, z) in profile:
            verts.append((r * ca, r * sa, z))
    faces = []
    for i in range(segs):
        i2 = (i + 1) % segs
        for j in range(P - 1):
            faces.append((i * P + j, i2 * P + j, i2 * P + j + 1, i * P + j + 1))
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    ob = obj_from_mesh(name, me, coll)
    if smooth:
        set_smooth(ob)
    if mat:
        ob.data.materials.append(mat)
    return ob


def mesh_from_grid(name, X, Y, Z, U=None, V=None, coll=None):
    nr, nc = X.shape
    verts = np.stack([X, Y, Z], -1).reshape(-1, 3)
    idx = np.arange(nr * nc).reshape(nr, nc)
    quads = np.stack([idx[:-1, :-1], idx[1:, :-1], idx[1:, 1:], idx[:-1, 1:]], -1).reshape(-1, 4)
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(verts))
    me.vertices.foreach_set("co", verts.ravel())
    me.loops.add(quads.size)
    me.loops.foreach_set("vertex_index", quads.ravel())
    me.polygons.add(len(quads))
    me.polygons.foreach_set("loop_start", np.arange(0, quads.size, 4))
    me.update(calc_edges=True)
    # make normals face +Z
    if U is not None:
        uvs = np.stack([U, V], -1).reshape(-1, 2)
        uvl = me.uv_layers.new(name="UVMap")
        uvl.data.foreach_set("uv", uvs[quads.ravel()].ravel())
    me.validate()
    ob = obj_from_mesh(name, me, coll)
    return ob


def box(name, size, loc=(0, 0, 0), mat=None, bevel=0.0, coll=None, rot=(0, 0, 0)):
    import bmesh
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x *= size[0]
        v.co.y *= size[1]
        v.co.z *= size[2]
    bm.to_mesh(me)
    bm.free()
    ob = obj_from_mesh(name, me, coll)
    ob.location = loc
    ob.rotation_euler = rot
    if bevel:
        add_bevel(ob, bevel, 2)
    if mat:
        ob.data.materials.append(mat)
    return ob


def sphere(name, r, loc=(0, 0, 0), mat=None, coll=None, segs=24, rings=12, scale=(1, 1, 1)):
    import bmesh
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segs, v_segments=rings, radius=r)
    bm.to_mesh(me)
    bm.free()
    ob = obj_from_mesh(name, me, coll)
    ob.location = loc
    ob.scale = scale
    set_smooth(ob)
    if mat:
        ob.data.materials.append(mat)
    return ob


def cylinder(name, r, h, loc=(0, 0, 0), mat=None, coll=None, segs=32, rot=(0, 0, 0)):
    import bmesh
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=segs, radius1=r, radius2=r, depth=h)
    bm.to_mesh(me)
    bm.free()
    ob = obj_from_mesh(name, me, coll)
    ob.location = loc
    ob.rotation_euler = rot
    if mat:
        ob.data.materials.append(mat)
    return ob


def plane(name, w, h, loc=(0, 0, 0), mat=None, coll=None, rot=(0, 0, 0)):
    verts = [(-w / 2, -h / 2, 0), (w / 2, -h / 2, 0), (w / 2, h / 2, 0), (-w / 2, h / 2, 0)]
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], [(0, 1, 2, 3)])
    uvl = me.uv_layers.new(name="UVMap")
    uvl.data.foreach_set("uv", [0, 0, 1, 0, 1, 1, 0, 1])
    me.update()
    ob = obj_from_mesh(name, me, coll)
    ob.location = loc
    ob.rotation_euler = rot
    if mat:
        ob.data.materials.append(mat)
    return ob
