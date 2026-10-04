"""Shared helpers for the procedural texture generators."""
import os
import numpy as np
from scipy import ndimage as ndi
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "build")
FONTS = os.path.join(HERE, "fonts")
os.makedirs(OUT, exist_ok=True)


def fbm(shape, base, seed, octaves=4, persistence=0.5, lacunarity=2.0):
    """Fractal value noise in roughly [-1, 1]. `base` = cells across the short side."""
    rng = np.random.default_rng(seed)
    h, w = shape
    out = np.zeros(shape, np.float32)
    amp, total, cells = 1.0, 0.0, float(base)
    for _ in range(octaves):
        gh = int(np.ceil(cells * h / min(h, w))) + 4
        gw = int(np.ceil(cells * w / min(h, w))) + 4
        g = rng.standard_normal((gh, gw)).astype(np.float32)
        zy = (h + 1) / (gh - 3)
        zx = (w + 1) / (gw - 3)
        up = ndi.zoom(g, (zy, zx), order=3, mode="wrap")
        oy = int(zy * 1.5)
        ox = int(zx * 1.5)
        out += amp * up[oy:oy + h, ox:ox + w]
        total += amp
        amp *= persistence
        cells *= lacunarity
    out /= total
    return out / (np.abs(out).max() + 1e-6)


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def mix(a, b, t):
    t = np.asarray(t, np.float32)
    if t.ndim == 2 and np.ndim(a) >= 2 and np.shape(a)[-1] == 3:
        t = t[..., None]
    elif t.ndim == 2 and np.ndim(b) >= 1 and np.shape(b)[-1] == 3:
        t = t[..., None]
    return a * (1 - t) + np.asarray(b, np.float32) * t


def save_rgb(arr, name, mode="RGB"):
    a = np.clip(arr, 0, 1)
    img = Image.fromarray((a * 255 + 0.5).astype(np.uint8), mode)
    img.save(os.path.join(OUT, name))
    return os.path.join(OUT, name)


def save_gray16(arr, name):
    a = np.clip(arr, 0, 1)
    img = Image.fromarray((a * 65535 + 0.5).astype(np.uint16))
    img.save(os.path.join(OUT, name))
    return os.path.join(OUT, name)


def blur(a, s):
    return ndi.gaussian_filter(a, s)


def angular_noise(theta, seed, kmax=14, amp=1.0, falloff=0.9):
    rng = np.random.default_rng(seed)
    out = np.zeros_like(theta, dtype=np.float32)
    for k in range(2, kmax):
        out += (rng.uniform(0.4, 1.0) / k ** falloff) * np.sin(k * theta + rng.uniform(0, 2 * np.pi))
    return amp * out / (np.abs(out).max() + 1e-6)
