"""Turn Blender passes into web layers + geometry for the React scene.

For each view writes public/scene/<view>/:
  bg@{1x,2x}.webp        defocused hall
  base@{1x,2x}.webp      table/tray plate without the clickable food (alpha where the hall shows)
  <id>@{1x,2x}.webp      cut-out layers: six slices, tiramisu, glass
  lqip (inline in scene.json) tiny blurred composite for the very first paint
and src/scene/<view>.json with normalised layer rects and hit polygons.
"""
import base64
import io
import json
import os
import sys

import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage as ndi
from skimage import measure

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RENDER = os.path.join(HERE, "build", "render")
PUBLIC = os.path.join(ROOT, "public", "scene")
DATA = os.path.join(ROOT, "src", "scene")

SLICE_IDS = ["seamone", "angels", "serena", "tomcat", "freeda", "stationf"]


def load(path):
    im = Image.open(path)
    a = np.asarray(im)
    if a.dtype == np.uint16:
        return a.astype(np.float32) / 65535.0
    return a.astype(np.float32) / 255.0


def to_img(a, mode):
    return Image.fromarray((np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8), mode)


def save_variants(img, out_dir, name, scales, quality, lossless=False):
    files = {}
    for tag, sc in scales.items():
        im = img if sc == 1 else img.resize((max(1, round(img.width * sc)), max(1, round(img.height * sc))), Image.LANCZOS)
        fn = f"{name}@{tag}.webp"
        im.save(os.path.join(out_dir, fn), "WEBP", quality=quality, method=6, lossless=lossless)
        files[tag] = fn
    return files


def polygon(mask, W, H, tol=1.2):
    m = ndi.binary_closing(mask > 0.5, iterations=2)
    m = ndi.binary_fill_holes(m)
    lab, n = ndi.label(m)
    if n == 0:
        return []
    sizes = ndi.sum(m, lab, range(1, n + 1))
    keep = lab == (int(np.argmax(sizes)) + 1)
    padded = np.pad(keep.astype(np.float32), 1)
    cs = measure.find_contours(padded, 0.5)
    c = max(cs, key=len)
    c = measure.approximate_polygon(c, tolerance=tol)
    return [[round((p[1] - 1) / W, 5), round((p[0] - 1) / H, 5)] for p in c]


def lights(bg, alpha_fg, W, H, max_n=46):
    lum = bg[..., :3] @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    hall_only = alpha_fg < 0.05
    bright = (lum > 0.80) & hall_only
    bright = ndi.binary_opening(bright, iterations=1)
    lab, n = ndi.label(bright)
    out = []
    if n == 0:
        return out
    idx = range(1, n + 1)
    sizes = ndi.sum(bright, lab, idx)
    coms = ndi.center_of_mass(bright, lab, idx)
    means = ndi.mean(lum, lab, idx)
    cand = sorted(zip(sizes, coms, means), key=lambda t: -t[0])
    for s, (cy, cx), mn in cand:
        if s < (W / 1440) ** 2 * 12:
            continue
        r = np.sqrt(s / np.pi)
        col = bg[int(cy), int(cx), :3]
        out.append({"x": round(cx / W, 4), "y": round(cy / H, 4), "r": round(r / W, 4),
                    "c": "#%02x%02x%02x" % tuple(int(v * 255) for v in col)})
        if len(out) >= max_n:
            break
    return out


def horizon(alpha_fg, H):
    rows = []
    for x in range(0, alpha_fg.shape[1], 8):
        col = alpha_fg[:, x]
        hit = np.nonzero(col > 0.5)[0]
        if len(hit):
            rows.append(hit[0])
    return float(np.median(rows)) / H if rows else 0.3


def lqip(img, w=64):
    small = img.convert("RGB").resize((w, round(img.height * w / img.width)), Image.LANCZOS)
    buf = io.BytesIO()
    small.save(buf, "JPEG", quality=60)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def extract(view):
    src = os.path.join(RENDER, view)
    meta = json.load(open(os.path.join(src, "passes.json")))
    W, H = meta["size"]
    out_dir = os.path.join(PUBLIC, view)
    os.makedirs(out_dir, exist_ok=True)
    # scales relative to the render: '2x' is full res, '1x' is half
    scales = {"2x": 1.0, "1x": 0.5}

    fg = load(os.path.join(src, "fg.png"))
    bg = load(os.path.join(src, "bg.png"))[..., :3]
    base_crop = load(os.path.join(src, "base_crop.png"))
    x0, y0, x1, y1 = meta["base_border"]
    base = fg.copy()
    base[y0:y1 + 1, x0:x1 + 1] = base_crop[y0:y1 + 1, x0:x1 + 1]
    ma = load(os.path.join(src, "mask_a.png"))[..., :3]
    mb = load(os.path.join(src, "mask_b.png"))[..., :3]
    mc = load(os.path.join(src, "mask_c.png"))[..., :3]
    md = load(os.path.join(src, "mask_d.png"))[..., :3]
    masks = [ma[..., 0], ma[..., 1], ma[..., 2], mb[..., 0], mb[..., 1], mb[..., 2]]
    objects = {sid: m for sid, m in zip(meta["slices"], masks)}
    objects["tiramisu"] = mc[..., 0]
    objects["glass"] = mc[..., 1]

    full = fg[..., :3]
    base_rgb = base[..., :3] * base[..., 3:4] + bg * (1 - base[..., 3:4])
    full_rgb = full * fg[..., 3:4] + bg * (1 - fg[..., 3:4])

    layers = {}
    for oid, m in objects.items():
        m = np.clip(m, 0, 1)
        ys, xs = np.nonzero(m > 0.002)
        if len(xs) == 0:
            print("empty mask", oid)
            continue
        pad = 3
        bx0, bx1 = max(xs.min() - pad, 0), min(xs.max() + pad, W - 1)
        by0, by1 = max(ys.min() - pad, 0), min(ys.max() + pad, H - 1)
        sl = (slice(by0, by1 + 1), slice(bx0, bx1 + 1))
        mm = m[sl][..., None]
        # un-premultiply against what lies underneath in the base plate
        col = (full_rgb[sl] - (1 - mm) * base_rgb[sl]) / np.maximum(mm, 1e-3)
        col = np.where(mm > 0.03, col, full_rgb[sl])
        rgba = np.concatenate([np.clip(col, 0, 1), mm], -1)
        files = save_variants(to_img(rgba, "RGBA"), out_dir, oid, scales, 90)
        cy, cx = ndi.center_of_mass(m > 0.5)
        layers[oid] = {
            "files": files,
            "rect": [round(bx0 / W, 5), round(by0 / H, 5), round((bx1 + 1 - bx0) / W, 5), round((by1 + 1 - by0) / H, 5)],
            "polygon": polygon(m, W, H, tol=1.2 * W / 1440),
            "center": [round(cx / W, 4), round(cy / H, 4)],
        }

    bg_files = save_variants(to_img(bg, "RGB"), out_dir, "bg", scales, 80)
    base_files = save_variants(to_img(base, "RGBA"), out_dir, "base", scales, 88)
    comp = to_img(full_rgb, "RGB")
    comp.save(os.path.join(out_dir, "composite.jpg"), quality=86)
    comp.resize((1200, round(1200 * H / W)) if W > H else (round(1200 * W / H), 1200), Image.LANCZOS).save(
        os.path.join(out_dir, "og.jpg"), quality=84)

    pizza = sum(objects[s] for s in SLICE_IDS)
    ys, xs = np.nonzero(pizza > 0.5)
    data = {
        "view": view,
        "size": [W, H],
        "bg": bg_files,
        "base": base_files,
        "lqip": lqip(comp),
        "layers": layers,
        "liquid": polygon(md[..., 0], W, H, tol=1.5 * W / 1440),
        "lights": lights(bg, fg[..., 3], W, H),
        "horizon": round(horizon(fg[..., 3], H), 4),
        "pizza": {"cx": round(xs.mean() / W, 4), "cy": round(ys.mean() / H, 4),
                  "rx": round((xs.max() - xs.min()) / 2 / W, 4), "ry": round((ys.max() - ys.min()) / 2 / H, 4)},
    }
    os.makedirs(DATA, exist_ok=True)
    with open(os.path.join(DATA, f"{view}.json"), "w") as f:
        json.dump(data, f, separators=(",", ":"))
    print(view, "ok", {k: v["rect"] for k, v in layers.items()})


if __name__ == "__main__":
    for v in sys.argv[1:] or ["desktop", "mobile"]:
        extract(v)
