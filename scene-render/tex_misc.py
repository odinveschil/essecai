"""Supporting textures: communal table wood, kraft paper, tray scuffs, coaster,
plate glaze print, receipt, notebook, back-of-house signage."""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

from common import OUT, FONTS, fbm, smoothstep, mix, save_rgb, save_gray16, blur
from scipy import ndimage as ndi

NODE_FONTS = os.path.join(os.path.dirname(FONTS), "..", "node_modules")


def font(name, size):
    return ImageFont.truetype(os.path.join(FONTS, name), size)


def wood():
    """Communal table top: 3.2 m x 1.2 m, planks running along X. Straight, oiled oak."""
    W, H = 4096, 1536
    rng = np.random.default_rng(3)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    nplank = 7
    plank_w = H / nplank
    pid = np.minimum((yy // plank_w).astype(int), nplank - 1)
    v = (yy % plank_w) / plank_w

    def aniso(cells_y, seed, octaves=4, stretch=14):
        n = fbm((H, W // stretch + 2), cells_y, seed, octaves=octaves)
        z = ndi.zoom(n, (1, stretch), order=1)
        return z[:, :W] if z.shape[1] >= W else np.pad(z, ((0, 0), (0, W - z.shape[1])), mode="edge")

    out = np.zeros((H, W, 3), np.float32)
    hgt = np.zeros((H, W), np.float32)
    for p in range(nplank):
        m = pid == p
        tone = rng.uniform(0.86, 1.10)
        hue = rng.uniform(-0.03, 0.03)
        lines = aniso(160, 200 + p, octaves=3, stretch=24)
        streak = aniso(18, 300 + p, octaves=4, stretch=10)
        broad = aniso(4, 400 + p, octaves=3, stretch=6)
        figure = 0.5 + 0.5 * np.sin(yy * 0.10 + 38.0 * broad + 5.0 * streak + p * 7)
        figure = smoothstep(0.55, 0.95, figure)
        fine_l = 0.5 + 0.5 * np.sin(yy * 0.75 + 9.0 * broad + 3.0 * streak + 4.0 * lines)
        g = 0.65 * figure + 0.35 * fine_l ** 4
        base = np.array([0.66 + hue, 0.46, 0.28 - hue]) * tone
        dark = np.array([0.42, 0.26, 0.14]) * tone
        f = np.clip(0.55 * g + 0.15 * (lines * 0.5 + 0.5) + 0.3 * (streak * 0.5 + 0.5) - 0.05, 0, 1)
        col = base[None, None, :] * (1 - f[..., None]) + dark[None, None, :] * f[..., None]
        out[m] = col[m]
        hgt[m] = (g * 0.4 + lines * 0.2)[m]
    from scipy import ndimage as _nd
    # plank seams
    seam = (v < 0.006) | (v > 0.994)
    seamf = blur(seam.astype(np.float32), 1.0)
    out = mix(out, np.array([0.10, 0.06, 0.035]), np.clip(seamf * 1.8, 0, 1))
    hgt -= seamf * 1.5
    # wear: lighter where trays slide, darker grime, scratches, water rings
    wear = smoothstep(0.1, 0.7, fbm((H, W), 4, 9, octaves=4))
    out = mix(out, out * np.array([1.12, 1.08, 1.0]), wear * 0.4)
    grime = smoothstep(0.3, 0.9, fbm((H, W), 10, 10, octaves=4))
    out = mix(out, out * 0.72, grime * 0.35)
    img = Image.new("L", (W, H), 0)
    dr = ImageDraw.Draw(img)
    for k in range(900):
        x0, y0 = rng.uniform(0, W), rng.uniform(0, H)
        a = rng.normal(0, 0.25) + (np.pi / 2 if rng.uniform() < 0.2 else 0)
        L = rng.uniform(10, 120)
        dr.line([(x0, y0), (x0 + L * np.cos(a), y0 + L * np.sin(a))], fill=int(rng.uniform(50, 170)), width=1)
    scratch = blur(np.asarray(img, np.float32) / 255, 0.5)
    out = mix(out, out * np.array([1.25, 1.18, 1.08]), scratch * 0.45)
    hgt -= scratch * 0.25
    img = Image.new("L", (W, H), 0)
    dr = ImageDraw.Draw(img)
    for k in range(16):
        cx, cy = rng.uniform(0, W), rng.uniform(0, H)
        r = rng.uniform(34, 46)
        dr.ellipse([cx - r, cy - r, cx + r, cy + r], outline=int(rng.uniform(70, 150)), width=3)
    rings = blur(np.asarray(img, np.float32) / 255, 1.5)
    out = mix(out, out * 0.84, rings)
    fine = fbm((H, W), 600, 6, octaves=2)
    out *= (1 + 0.04 * fine[..., None])
    rough = 0.42 + 0.22 * wear - 0.12 * grime + 0.08 * fine + 0.2 * scratch
    save_rgb(out, "wood_albedo.jpg")
    save_gray16((hgt - hgt.min()) / (hgt.max() - hgt.min()), "wood_height.png")
    save_rgb(np.repeat(np.clip(rough, 0, 1)[..., None], 3, -1), "wood_rough.jpg")


def paper():
    """Kraft/parchment sheet under the pizza: 0.44 m square."""
    N = 2048
    rng = np.random.default_rng(4)
    base = np.array([0.80, 0.68, 0.50], np.float32)
    n1 = fbm((N, N), 8, 11, octaves=5)
    fib = fbm((N, N), 300, 12, octaves=2)
    col = base[None, None, :] * (1 + 0.06 * n1[..., None] + 0.04 * fib[..., None])
    # crinkles: ridged noise
    cr = 1 - np.abs(fbm((N, N), 5, 13, octaves=4))
    cr2 = 1 - np.abs(fbm((N, N), 14, 14, octaves=3))
    h = 0.6 * cr ** 3 + 0.4 * cr2 ** 3 + 0.05 * fib
    # grease rings near the pizza edge (pizza radius ~0.163 m of 0.22 half-size)
    yy, xx = np.mgrid[0:N, 0:N].astype(np.float32)
    r = np.hypot(xx - N / 2, yy - N / 2) / (N / 2) * 0.22
    grease = smoothstep(0.02, 0.0, np.abs(r - 0.168 - 0.006 * fbm((N, N), 10, 15, octaves=3))) * smoothstep(0.2, 0.8, fbm((N, N), 6, 16, octaves=3) + 0.5)
    col = mix(col, col * np.array([0.78, 0.66, 0.48]), grease * 0.6)
    # oil-soaked under the pizza (only visible through the cut lines)
    col = mix(col, col * np.array([0.55, 0.40, 0.26]), smoothstep(0.168, 0.150, r) * 0.9)
    # semolina / flour
    sem = (fbm((N, N), 700, 17, octaves=1) > 0.62).astype(np.float32)
    sem *= smoothstep(0.24, 0.15, r)
    col = mix(col, np.array([0.95, 0.82, 0.48]), blur(sem, 0.7) * 0.85)
    flour = smoothstep(0.35, 0.9, fbm((N, N), 30, 18, octaves=3)) * smoothstep(0.22, 0.16, r)
    col = mix(col, np.array([0.96, 0.94, 0.90]), flour * 0.45)
    h += blur(sem, 0.7) * 0.4
    save_rgb(col, "paper_albedo.jpg")
    save_gray16(np.clip(h / h.max(), 0, 1), "paper_height.png")
    gr = np.repeat((0.75 - 0.4 * grease)[..., None], 3, -1)
    save_rgb(gr, "paper_rough.jpg")


def tray():
    """Worn bottle-green fiberglass tray: scuffs + rim wear. 0.80 x 0.50 m."""
    W, H = 2048, 1280
    rng = np.random.default_rng(5)
    base = np.array([0.10, 0.27, 0.20], np.float32)
    n = fbm((H, W), 6, 21, octaves=5)
    col = base[None, None] * (1 + 0.10 * n[..., None])
    img = Image.new("L", (W, H), 0)
    dr = ImageDraw.Draw(img)
    for k in range(1600):
        x0, y0 = rng.uniform(0, W), rng.uniform(0, H)
        a = rng.uniform(0, np.pi)
        L = rng.uniform(5, 70)
        dr.line([(x0, y0), (x0 + L * np.cos(a), y0 + L * np.sin(a))], fill=int(rng.uniform(40, 150)), width=1)
    sc = np.asarray(img, np.float32) / 255
    col = mix(col, np.array([0.30, 0.42, 0.36]), sc * 0.55)
    # edge wear
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    ed = np.minimum.reduce([xx, W - xx, yy, H - yy]) / 60
    wear = smoothstep(1.2, 0.0, ed) * smoothstep(-0.2, 0.6, fbm((H, W), 30, 22, octaves=3))
    col = mix(col, np.array([0.32, 0.40, 0.33]), wear * 0.6)
    save_rgb(col, "tray_albedo.jpg")
    save_rgb(np.repeat((0.42 + 0.25 * sc + 0.1 * n)[..., None], 3, -1), "tray_rough.jpg")


def coaster():
    """Black/red card coaster under the Coke Zero: 'Introduction'. 0.12 m square."""
    N = 1600
    img = Image.new("RGB", (N, N), (18, 16, 17))
    dr = ImageDraw.Draw(img)
    red = (196, 20, 32)
    dr.rounded_rectangle([40, 40, N - 40, N - 40], radius=60, outline=red, width=16)
    dr.rounded_rectangle([78, 78, N - 78, N - 78], radius=40, outline=(120, 16, 22), width=4)
    f1 = font("oswald700.ttf", 150)
    f2 = font("oswald500.ttf", 74)
    # front strip (towards the camera = bottom of texture)
    txt = "INTRODUCTION"
    tw = dr.textlength(txt, font=f1)
    tri = 96
    gap = 34
    total = tri * 0.86 + gap + tw
    x0 = (N - total) / 2
    yb = N - 360
    dr.polygon([(x0, yb + 28), (x0, yb + 28 + tri), (x0 + tri * 0.86, yb + 28 + tri / 2)], fill=red)
    dr.text((x0 + tri * 0.86 + gap, yb), txt, font=f1, fill=(240, 232, 222))
    t2 = "MEET ARYAMAN  ·  ESSEC  ·  2026"
    dr.text(((N - dr.textlength(t2, font=f2)) / 2, N - 165), t2, font=f2, fill=red)
    # back strip (mostly hidden under the glass)
    t3 = "ZERO SUGAR · ZERO EXCUSES"
    dr.text(((N - dr.textlength(t3, font=f2)) / 2, 120), t3, font=f2, fill=(150, 30, 34))
    a = np.asarray(img, np.float32) / 255
    a *= (1 + 0.06 * fbm((N, N), 20, 31, octaves=3))[..., None]
    # card wear / a wet ring
    yy, xx = np.mgrid[0:N, 0:N].astype(np.float32)
    rr = np.hypot(xx - N / 2, yy - N / 2)
    ring = smoothstep(18, 0, np.abs(rr - 300)) * 0.25
    a = mix(a, a * 0.8, ring)
    save_rgb(a, "coaster.jpg")


def plate_print():
    """Glaze print on the tiramisu plate rim: 'Station F — Film ▸'. Plate texture
    is planar-mapped over a 0.20 m square; rim radius ~0.072–0.095 m."""
    N = 2048
    img = Image.new("RGB", (N, N), (246, 242, 233))
    dr = ImageDraw.Draw(img)
    c = N / 2
    s = N / 0.20
    # thin terracotta rim lines
    for rad, w in ((0.0935, 10), (0.0705, 5)):
        R = rad * s
        dr.ellipse([c - R, c - R, c + R, c + R], outline=(176, 74, 46), width=w)
    # text along the front of the rim (towards camera = bottom), upright
    ser = ImageFont.truetype(os.path.join(FONTS, "fraunces_it.ttf"), 120)
    text = "Station F — Film"
    r_text = 0.0825 * s
    adv = [dr.textlength(ch, font=ser) for ch in text]
    L = sum(adv) + 150
    pos = 0
    layer = Image.new("L", (N, N), 0)
    for ch, a_ in zip(text, adv):
        mid = pos + a_ / 2
        pos += a_
        if ch == " ":
            continue
        ang = -np.pi / 2 - (L / 2 - mid) / r_text
        S = 260
        g = Image.new("L", (S, S), 0)
        gd = ImageDraw.Draw(g)
        bb = ser.getbbox("x")
        gd.text((S / 2 - a_ / 2, S / 2 - (bb[1] + bb[3]) / 2), ch, font=ser, fill=255)
        g = g.rotate(np.degrees(ang) + 90, resample=Image.BICUBIC)
        x = c + r_text * np.cos(ang)
        y = c - r_text * np.sin(ang)
        layer.paste(g, (int(x - S / 2), int(y - S / 2)), g)
    # play triangle at the end of the text
    ang = -np.pi / 2 - (L / 2 - (pos + 90)) / r_text
    x = c + r_text * np.cos(ang)
    y = c - r_text * np.sin(ang)
    t = 38
    rot = ang + np.pi / 2
    pts = []
    for px, py in ((-t * 0.6, -t), (-t * 0.6, t), (t, 0)):
        rx = px * np.cos(rot) - py * np.sin(rot)
        ry = px * np.sin(rot) + py * np.cos(rot)
        pts.append((x + rx, y - ry))
    ImageDraw.Draw(layer).polygon(pts, fill=255)
    arr = np.asarray(img, np.float32) / 255
    m = blur(np.asarray(layer, np.float32) / 255, 0.8)
    arr = mix(arr, np.array([0.62, 0.24, 0.14]), m * 0.95)
    arr *= (1 + 0.012 * fbm((N, N), 30, 41, octaves=2))[..., None]
    save_rgb(arr, "plate_print.jpg")


def receipt():
    W, H = 640, 1500
    img = Image.new("RGB", (W, H), (246, 243, 236))
    dr = ImageDraw.Draw(img)
    mono = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 34)
    monob = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", 44)
    lines = [
        ("b", "LA FELICITA"), ("", "STATION F - PARIS 13"), ("", "--------------------------"),
        ("", "TAVOLO 42    COPERTI 1"), ("", "--------------------------"),
        ("", "1 PIZZA (6 PARTI)    16,00"), ("", "1 TIRAMISU            7,50"), ("", "1 COCA ZERO           4,00"),
        ("", "--------------------------"), ("b", "TOTALE        27,50"), ("", ""),
        ("", "ESSEC"), ("", "ADVANCED ENTREPRENEURSHIP"), ("", "2026"), ("", ""), ("", "  GRAZIE E A PRESTO!"),
    ]
    y = 60
    for kind, t in lines:
        f = monob if kind == "b" else mono
        tw = dr.textlength(t, font=f)
        x = (W - tw) / 2 if kind == "b" or t.strip() in ("ESSEC", "2026", "ADVANCED ENTREPRENEURSHIP", "STATION F - PARIS 13") else 40
        dr.text((x, y), t, font=f, fill=(40, 38, 40))
        y += 62 if kind == "b" else 52
    for k in range(30):
        x = 60 + k * 18
        dr.rectangle([x, y + 40, x + (6 if k % 3 else 11), y + 140], fill=(40, 38, 40))
    a = np.asarray(img, np.float32) / 255
    a = mix(a, a * 0.93, smoothstep(0.2, 0.9, fbm((H, W), 4, 51, octaves=3)) * 0.5)
    save_rgb(a, "receipt.jpg")


def notebook():
    W, H = 1100, 1500
    img = Image.new("RGB", (W, H), (28, 52, 92))
    dr = ImageDraw.Draw(img)
    f = font("oswald700.ttf", 120)
    f2 = font("oswald500.ttf", 46)
    dr.text((90, 160), "ESSEC", font=f, fill=(236, 230, 214))
    dr.text((94, 320), "BUSINESS SCHOOL", font=f2, fill=(236, 230, 214))
    dr.rectangle([90, 400, 520, 406], fill=(200, 160, 70))
    dr.text((94, 1280), "NOTES — ADV. ENTREPRENEURSHIP", font=f2, fill=(200, 196, 186))
    a = np.asarray(img, np.float32) / 255
    a *= (1 + 0.08 * fbm((H, W), 10, 61, octaves=4))[..., None]
    save_rgb(a, "notebook.jpg")


def signs():
    """Back-of-hall signage (will be out of focus): kiosk boards and neon-ish signs."""
    specs = [
        ("sign_pizza.png", "PIZZA", (255, 214, 120), (178, 34, 30), "alfa.ttf"),
        ("sign_pasta.png", "PASTA FRESCA", (255, 236, 196), (24, 92, 70), "alfa.ttf"),
        ("sign_bar.png", "BAR", (255, 120, 150), (20, 18, 30), "alfa.ttf"),
        ("sign_caffe.png", "CAFFÈ", (255, 230, 170), (120, 40, 70), "alfa.ttf"),
        ("sign_felicita.png", "La Felicità", (255, 210, 120), (30, 30, 36), "fraunces_it.ttf"),
        ("sign_fritti.png", "FRITTI", (255, 200, 60), (40, 70, 140), "alfa.ttf"),
        ("sign_gelato.png", "GELATO", (255, 170, 200), (240, 236, 220), "alfa.ttf"),
        ("sign_vino.png", "VINO", (255, 220, 160), (110, 20, 30), "alfa.ttf"),
    ]
    for name, text, fg, bg, fnt in specs:
        f = font(fnt, 220)
        tw = int(ImageDraw.Draw(Image.new("RGB", (1, 1))).textlength(text, font=f))
        W, H = tw + 220, 420
        img = Image.new("RGB", (W, H), bg)
        dr = ImageDraw.Draw(img)
        dr.rectangle([18, 18, W - 18, H - 18], outline=fg, width=10)
        bb = f.getbbox(text)
        dr.text(((W - tw) / 2, (H - (bb[3] + bb[1])) / 2), text, font=f, fill=fg)
        img.save(os.path.join(OUT, name))


if __name__ == "__main__":
    import sys
    which = sys.argv[1:] or ["wood", "paper", "tray", "coaster", "plate_print", "receipt", "notebook", "signs"]
    for w in which:
        globals()[w]()
        print("done", w)
