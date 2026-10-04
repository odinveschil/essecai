"""Procedural Neapolitan pizza textures (albedo, height, material props) with the
six section names branded into the cornicione.

Texture space: square covering [-EXT, EXT] metres, row 0 = +Y (far side from the
desktop camera), column 0 = -X. Writes into scene-render/build/.
"""
import json
import os
import sys
import numpy as np
from scipy import ndimage as ndi
from PIL import Image, ImageDraw, ImageFont

from common import OUT, FONTS, fbm, smoothstep, mix, save_rgb, save_gray16, blur, angular_noise

N = int(os.environ.get("PIZZA_RES", 4096))
EXT = 0.19
PX = 2 * EXT / N  # metres per pixel
R0 = 0.163  # nominal pizza radius
SEED = 7

# Section slices — clockwise from the top (far side). Angle = slice centre, maths convention.
SLICES = [
    ("seamone", "Seamone Paris", 90),
    ("angels", "Business Angels", 30),
    ("serena", "Serena VC", -30),
    ("tomcat", "TOMCAT", -90),
    ("freeda", "Freeda", -150),
    ("stationf", "Station F", 150),
]


def m2px(m):
    return m / PX


def grid():
    c = (np.arange(N, dtype=np.float32) + 0.5) * PX - EXT
    x = c[None, :].repeat(N, 0)
    y = -c[:, None].repeat(N, 1)
    return x, y


def window(cx, cy, rad):
    """Pixel window (slices) around metric centre with metric radius."""
    j = int((cx + EXT) / PX)
    i = int((EXT - cy) / PX)
    rp = int(m2px(rad)) + 3
    i0, i1 = max(i - rp, 0), min(i + rp, N)
    j0, j1 = max(j - rp, 0), min(j + rp, N)
    return slice(i0, i1), slice(j0, j1)


def local_coords(sl, cx, cy):
    ii = np.arange(sl[0].start, sl[0].stop, dtype=np.float32)
    jj = np.arange(sl[1].start, sl[1].stop, dtype=np.float32)
    lx = (jj[None, :] + 0.5) * PX - EXT - cx
    ly = EXT - (ii[:, None] + 0.5) * PX - cy
    return np.broadcast_to(lx, (len(ii), len(jj))), np.broadcast_to(ly, (len(ii), len(jj)))


def blob_mask(lx, ly, rad, rng, irregular=0.3, soft=0.0006, kmax=9, aspect=1.0, rot=0.0, falloff=1.7):
    c, s = np.cos(rot), np.sin(rot)
    ux = (lx * c + ly * s) / aspect
    uy = -lx * s + ly * c
    rr = np.hypot(ux, uy)
    th = np.arctan2(uy, ux)
    edge = rad * (1 + irregular * angular_noise(th, int(rng.integers(1e9)), kmax=kmax, falloff=falloff))
    return smoothstep(soft, -soft, rr - edge), rr / np.maximum(edge, 1e-6)


def main():
    rng = np.random.default_rng(SEED)
    x, y = grid()
    r = np.hypot(x, y)
    th = np.arctan2(y, x)

    # --- pizza outline: hand stretched, slightly oval and lumpy ---------------
    edge_r = R0 * (1 + 0.022 * angular_noise(th, 11, kmax=10, falloff=1.1) + 0.012 * np.cos(2 * (th - 0.6)))
    d = r / edge_r
    inside = smoothstep(1.002, 0.996, d)

    # inner edge of the cornicione
    d_in = 0.815 + 0.035 * angular_noise(th, 12, kmax=18, falloff=0.7)
    t = np.clip((d - d_in) / (1 - d_in), 0, 1)
    u = np.where(t < 0.52, 0.5 * t / 0.52, 0.5 + 0.5 * (t - 0.52) / 0.48)
    prof = np.sqrt(np.clip(1 - (2 * u - 1) ** 2, 0, 1))
    prof = np.where(d < d_in, 0, prof)

    n_lo = fbm((N, N), 6, 21, octaves=3)
    n_mid = fbm((N, N), 40, 22, octaves=3)
    n_hi = fbm((N, N), 260, 23, octaves=2)

    crust_h = (0.0175 + 0.005 * angular_noise(th, 13, kmax=16, falloff=0.6)) * (1 + 0.15 * n_lo)
    H = 0.0042 + 0.0006 * n_lo
    H = H + crust_h * prof

    # blisters / airy bubbles on the cornicione
    bubble_top = np.zeros((N, N), np.float32)
    for k in range(95):
        a = rng.uniform(-np.pi, np.pi)
        er = R0 * (1 + 0.022 * angular_noise(np.array([a]), 11, kmax=10, falloff=1.1)[0] + 0.012 * np.cos(2 * (a - 0.6)))
        din = 0.815
        tt = rng.uniform(0.2, 0.85)
        rr_ = er * (din + (1 - din) * tt)
        cx, cy = rr_ * np.cos(a), rr_ * np.sin(a)
        rad = rng.uniform(0.003, 0.0085)
        hgt = rng.uniform(0.0015, 0.0055) * (1.0 if tt < 0.75 else 0.6)
        sl = window(cx, cy, rad * 2.2)
        lx, ly = local_coords(sl, cx, cy)
        q = (lx ** 2 + ly ** 2) / rad ** 2
        bump = np.exp(-q * 1.4)
        H[sl] += hgt * bump * (prof[sl] > 0.05)
        bubble_top[sl] = np.maximum(bubble_top[sl], bump * (hgt / 0.0055))

    H += 0.0004 * n_mid * prof + 0.00015 * n_hi

    # --- base colours --------------------------------------------------------
    pale = np.array([0.93, 0.84, 0.66], np.float32)
    golden = np.array([0.85, 0.62, 0.35], np.float32)
    brown = np.array([0.60, 0.35, 0.15], np.float32)
    char = np.array([0.09, 0.055, 0.035], np.float32)

    hn = np.clip((H - 0.004) / 0.024, 0, 1)
    brown_amt = np.clip(0.15 + 0.75 * hn + 0.3 * n_mid + 0.25 * n_lo + 0.6 * bubble_top, 0, 1)
    A = mix(np.broadcast_to(pale, (N, N, 3)), golden, smoothstep(0.0, 0.55, brown_amt))
    A = mix(A, brown, smoothstep(0.55, 1.05, brown_amt) * 0.85)
    # the outer foot of the crust stays pale and floury
    A = mix(A, pale * 1.02, smoothstep(0.93, 0.995, d) * 0.55)

    rough = np.full((N, N), 0.72, np.float32)
    sss = np.zeros((N, N), np.float32)

    # leopard spotting — concentrated on high points & bubble tops
    spot = np.zeros((N, N), np.float32)
    halo = np.zeros((N, N), np.float32)
    count = 0
    tries = 0
    while count < 330 and tries < 6000:
        tries += 1
        a = rng.uniform(-np.pi, np.pi)
        tt = rng.uniform(0.05, 0.98)
        rr_ = R0 * (0.815 + 0.185 * tt)
        cx, cy = rr_ * np.cos(a), rr_ * np.sin(a)
        i = int((EXT - cy) / PX); j = int((cx + EXT) / PX)
        w = 0.05 + 0.55 * hn[i, j] ** 2 + 1.2 * bubble_top[i, j]
        if rng.uniform() > w:
            continue
        count += 1
        rad = rng.choice([rng.uniform(0.0004, 0.0011), rng.uniform(0.0011, 0.0024), rng.uniform(0.0024, 0.0042)], p=[0.6, 0.32, 0.08])
        sl = window(cx, cy, rad * 3)
        lx, ly = local_coords(sl, cx, cy)
        m, _ = blob_mask(lx, ly, rad, rng, irregular=0.35, soft=rad * 0.5, aspect=rng.uniform(0.7, 1.4), rot=rng.uniform(0, 3.14))
        hm, _ = blob_mask(lx, ly, rad * 2.1, rng, irregular=0.3, soft=rad * 0.9)
        spot[sl] = np.maximum(spot[sl], m * rng.uniform(0.55, 0.95))
        halo[sl] = np.maximum(halo[sl], hm * 0.45)
    spot *= (prof > 0.02)
    halo *= (prof > 0.02)
    A = mix(A, brown * 0.85, halo * 0.55)
    A = mix(A, char, spot)
    rough = mix(rough, 0.92, spot)

    # flour dust on the crust foot
    flour = (fbm((N, N), 900, 31, octaves=1) > 0.55).astype(np.float32) * smoothstep(0.86, 1.0, d) * inside
    flour = blur(flour, 0.6)
    A = mix(A, np.array([0.97, 0.95, 0.90], np.float32), flour * 0.7)

    # crust micro texture: tiny blisters + pores, floury matte
    micro = fbm((N, N), 700, 81, octaves=2)
    blist = smoothstep(0.35, 0.75, fbm((N, N), 380, 82, octaves=2)) * prof
    H += (0.00018 * micro + 0.0004 * blist) * (prof > 0)
    A = mix(A, A * np.array([1.06, 1.04, 0.98], np.float32), blist * 0.5)
    A = mix(A, A * np.array([0.80, 0.70, 0.60], np.float32), smoothstep(0.4, 0.9, micro) * 0.25 * (prof > 0))

    # --- tomato sauce --------------------------------------------------------
    sauce_edge = d_in - 0.015 + 0.03 * fbm((N, N), 30, 41, octaves=3)
    S = smoothstep(sauce_edge + 0.008, sauce_edge - 0.004, d)
    S = np.maximum(S, smoothstep(0.55, 0.85, fbm((N, N), 24, 42, octaves=3)) * smoothstep(d_in + 0.08, d_in, d) * 0.85)
    sn = fbm((N, N), 60, 43, octaves=5)
    sn2 = fbm((N, N), 14, 46, octaves=3)
    s_red = np.array([0.52, 0.06, 0.03], np.float32)
    s_or = np.array([0.70, 0.17, 0.05], np.float32)
    s_dk = np.array([0.30, 0.035, 0.02], np.float32)
    sauceC = mix(np.broadcast_to(s_red, (N, N, 3)), s_or, smoothstep(-0.5, 0.8, 0.5 * sn + 0.9 * sn2))
    sauceC = mix(sauceC, s_dk, smoothstep(0.3, 0.85, fbm((N, N), 35, 44, octaves=3)) * 0.75)
    # crushed tomato pulp + baked, reduced edges near the crust
    pulp_n = fbm((N, N), 120, 45, octaves=3)
    pulp = smoothstep(0.45, 0.75, pulp_n)
    sauceC = mix(sauceC, np.array([0.78, 0.22, 0.07], np.float32), pulp * 0.55)
    sauceC = mix(sauceC, np.array([0.34, 0.07, 0.03], np.float32), smoothstep(d_in - 0.06, d_in, d) * 0.6)
    gran = fbm((N, N), 500, 47, octaves=2)
    sauceC *= (1 + 0.10 * gran)[..., None]
    A = mix(A, sauceC, S)
    sh = fbm((N, N), 26, 48, octaves=3)
    H += S * (0.0005 + 0.00025 * sh + 0.0003 * pulp * smoothstep(0.4, 0.9, pulp_n))
    rough = mix(rough, np.clip(0.26 - 0.12 * sn + 0.12 * pulp, 0.08, 0.5), S)

    # --- toppings (painted on top in order) ---------------------------------
    def place(nmax, minsep, existing, dmax=0.72, dmin=0.0):
        pts = []
        tries = 0
        while len(pts) < nmax and tries < 6000:
            tries += 1
            rr_ = R0 * np.sqrt(rng.uniform((dmin / 1.0) ** 2, dmax ** 2))
            a = rng.uniform(-np.pi, np.pi)
            p = (rr_ * np.cos(a), rr_ * np.sin(a))
            if all(np.hypot(p[0] - q[0], p[1] - q[1]) > minsep for q in pts + existing):
                pts.append(p)
        return pts

    # mozzarella (fior di latte) — torn pieces melted into lobed pools
    cheese = np.zeros((N, N), np.float32)
    cheese_h = np.zeros((N, N), np.float32)
    cpos = place(13, 0.044, [], dmax=0.76)
    for (cx, cy) in cpos:
        rad = rng.uniform(0.012, 0.019)
        sl = window(cx, cy, rad * 2.6)
        lx, ly = local_coords(sl, cx, cy)
        m = np.zeros(lx.shape, np.float32)
        hh = np.zeros(lx.shape, np.float32)
        for lob in range(rng.integers(2, 5)):
            ox, oy = rng.normal(0, rad * 0.45, 2)
            r2 = rad * rng.uniform(0.55, 1.0)
            mm, rn = blob_mask(lx - ox, ly - oy, r2, rng, irregular=0.22, soft=0.0018, kmax=6,
                               aspect=rng.uniform(0.7, 1.4), rot=rng.uniform(0, 3.14))
            m = np.maximum(m, mm)
            hh = np.maximum(hh, mm * np.sqrt(np.clip(1 - rn ** 2, 0, 1)))
        cheese[sl] = np.maximum(cheese[sl], m)
        cheese_h[sl] = np.maximum(cheese_h[sl], hh)
    cheese *= smoothstep(0.86, 0.8, d)
    cheese_h *= cheese
    cn = fbm((N, N), 90, 51, octaves=3)
    thin = 1 - smoothstep(0.05, 0.55, cheese_h)
    milk = np.array([0.95, 0.91, 0.80], np.float32)
    cheeseC = mix(np.broadcast_to(milk, (N, N, 3)), np.array([0.93, 0.80, 0.62], np.float32), thin * 0.55)
    # golden blisters, a few browned spots
    bl = np.zeros((N, N), np.float32)
    for (cx, cy) in cpos:
        for k in range(rng.integers(6, 14)):
            px_, py_ = cx + rng.normal(0, 0.008), cy + rng.normal(0, 0.008)
            rr = rng.uniform(0.0007, 0.0028)
            sl = window(px_, py_, rr * 2.5)
            lx, ly = local_coords(sl, px_, py_)
            mm, rn = blob_mask(lx, ly, rr, rng, irregular=0.35, soft=rr * 0.6)
            bl[sl] = np.maximum(bl[sl], mm * rng.uniform(0.4, 1.0))
    bl *= smoothstep(0.2, 0.6, cheese_h)
    cheeseC = mix(cheeseC, np.array([0.86, 0.66, 0.36], np.float32), bl * 0.8)
    cheeseC = mix(cheeseC, np.array([0.58, 0.36, 0.15], np.float32), smoothstep(0.6, 1.0, bl) * 0.6)
    cheeseC *= (1 + 0.04 * cn)[..., None]
    A = mix(A, cheeseC, cheese)
    H += cheese * 0.0003 + cheese_h * (0.0026 + 0.0004 * cn) + bl * 0.0004
    rough = mix(rough, 0.30 + 0.12 * cn + 0.25 * bl, cheese)
    sss = np.maximum(sss, cheese * (0.55 - 0.3 * bl))

    # pepperoni — thin, cupped, crispy edges, pooled orange grease
    pep_pos = place(17, 0.036, [], dmax=0.74)
    for (cx, cy) in pep_pos:
        rad = rng.uniform(0.0115, 0.0145)
        sl = window(cx, cy, rad * 1.5)
        lx, ly = local_coords(sl, cx, cy)
        m, rn = blob_mask(lx, ly, rad, rng, irregular=0.07, soft=0.0004, kmax=8)
        meat = fbm(m.shape, 9, int(rng.integers(1e9)), octaves=4)
        fat = smoothstep(0.35, 0.6, fbm(m.shape, 22, int(rng.integers(1e9)), octaves=2))
        base = np.array([0.46, 0.075, 0.04], np.float32) * rng.uniform(0.9, 1.1)
        col = mix(np.broadcast_to(base, m.shape + (3,)), np.array([0.33, 0.045, 0.025], np.float32), smoothstep(-0.2, 0.6, meat) * 0.7)
        col = mix(col, np.array([0.80, 0.47, 0.36], np.float32), fat * 0.45)
        # crisp, curled rim: darker, uneven char
        rimw = smoothstep(0.78, 1.0, rn)
        charn = smoothstep(0.0, 0.6, fbm(m.shape, 6, int(rng.integers(1e9)), octaves=2))
        col = mix(col, np.array([0.22, 0.05, 0.03], np.float32), rimw * (0.5 + 0.4 * charn))
        col = mix(col, np.array([0.07, 0.025, 0.015], np.float32), smoothstep(0.93, 1.0, rn) * charn * 0.8)
        oil = smoothstep(0.55, 0.15, rn) * rng.uniform(0.4, 0.9)
        col = mix(col, np.array([0.70, 0.17, 0.04], np.float32), oil * 0.45)
        A[sl] = mix(A[sl], col, m)
        cup = 0.0007 + 0.0036 * rn ** 3 + 0.0003 * meat
        H[sl] = H[sl] * (1 - m) + (np.maximum(H[sl], 0.0046) + cup) * m
        rough[sl] = mix(rough[sl], np.clip(0.30 - 0.22 * oil + 0.35 * rimw, 0.05, 0.8), m)
        # grease halo bleeding into the cheese/sauce around it
        ho, _ = blob_mask(lx, ly, rad * 1.35, rng, irregular=0.25, soft=0.003)
        hal = ho * (1 - m) * 0.5
        A[sl] = mix(A[sl], A[sl] * np.array([1.0, 0.70, 0.40], np.float32), hal)
        rough[sl] = mix(rough[sl], 0.12, hal)

    # chicken — torn roast pieces, seared edges
    chk_pos = place(9, 0.034, pep_pos, dmax=0.70)
    for (cx, cy) in chk_pos:
        rad = rng.uniform(0.0065, 0.0095)
        sl = window(cx, cy, rad * 2.2)
        lx, ly = local_coords(sl, cx, cy)
        rot = rng.uniform(0, 3.14)
        m, rn = blob_mask(lx, ly, rad, rng, irregular=0.3, soft=0.0005, kmax=7, aspect=rng.uniform(1.2, 1.9), rot=rot)
        c, s = np.cos(rot), np.sin(rot)
        along = lx * c + ly * s
        fib = fbm(m.shape, 4, int(rng.integers(1e9)), octaves=3)
        streak = 0.5 + 0.5 * np.sin(m2px(along) * 0.25 + 6 * fib)
        col = mix(np.broadcast_to(np.array([0.93, 0.87, 0.78], np.float32), m.shape + (3,)), np.array([0.84, 0.74, 0.60], np.float32), streak * 0.4)
        col = mix(col, np.array([0.56, 0.35, 0.16], np.float32), smoothstep(0.5, 1.0, rn) * 0.8)
        sear = smoothstep(0.3, 0.8, fbm(m.shape, 6, int(rng.integers(1e9)), octaves=2))
        col = mix(col, np.array([0.42, 0.25, 0.11], np.float32), sear * 0.55)
        A[sl] = mix(A[sl], col, m)
        H[sl] += m * (0.0034 * np.sqrt(np.clip(1 - rn ** 2, 0, 1)) + 0.0003 * fib)
        rough[sl] = mix(rough[sl], 0.55 - 0.2 * sear, m)

    # basil — a few leaves, one or two wilted by the oven
    bas_pos = place(6, 0.06, [], dmax=0.66)
    for k, (cx, cy) in enumerate(bas_pos):
        L = rng.uniform(0.017, 0.026)
        sl = window(cx, cy, L * 1.2)
        lx, ly = local_coords(sl, cx, cy)
        rot = rng.uniform(0, 2 * np.pi)
        c, s = np.cos(rot), np.sin(rot)
        uu = (lx * c + ly * s) / L
        vv = (-lx * s + ly * c) / L
        curve = 0.08 * uu ** 2
        width = 0.40 * np.clip(1 - uu ** 2, 0, 1) ** 0.65 * (1 + 0.35 * uu)
        dist = np.abs(vv - curve)
        m = smoothstep(0.015, -0.015, dist - width) * (np.abs(uu) < 1)
        g1 = np.array([0.13, 0.30, 0.07], np.float32) if k % 3 else np.array([0.09, 0.20, 0.05], np.float32)
        col = mix(np.broadcast_to(g1, m.shape + (3,)), np.array([0.25, 0.45, 0.12], np.float32), smoothstep(0.025, 0.0, dist) * 0.55)
        side = (vv - curve) / np.maximum(width, 1e-3)
        veins = np.abs(np.sin(uu * 9 - np.abs(side) * 2.2)) < 0.12
        col = mix(col, g1 * 1.45, veins * (np.abs(side) < 0.9) * 0.35)
        col = mix(col, g1 * 0.55, smoothstep(0.6, 1.0, np.abs(side)) * 0.5)
        wilt = smoothstep(0.2, 0.8, fbm(m.shape, 4, int(rng.integers(1e9)), octaves=2)) * (0.9 if k % 3 == 0 else 0.3)
        col = mix(col, np.array([0.05, 0.08, 0.03], np.float32), wilt)
        A[sl] = mix(A[sl], col, m)
        H[sl] += m * (0.0005 + 0.0008 * (1 - np.abs(side)) * (np.abs(side) < 1))
        rough[sl] = mix(rough[sl], 0.25, m)

    # olive oil drizzle — glossy streaks across the top
    drizzle = np.zeros((N, N), np.float32)
    for k in range(6):
        a0 = rng.uniform(-np.pi, np.pi)
        pts = []
        cx, cy = R0 * 0.6 * np.cos(a0), R0 * 0.6 * np.sin(a0)
        ang = a0 + np.pi + rng.uniform(-0.6, 0.6)
        for s_ in range(160):
            pts.append((cx, cy))
            ang += rng.normal(0, 0.07)
            cx += 0.0012 * np.cos(ang)
            cy += 0.0012 * np.sin(ang)
            if np.hypot(cx, cy) > R0 * 0.8:
                break
        img = Image.new("L", (N, N), 0)
        dr = ImageDraw.Draw(img)
        pp = [((p[0] + EXT) / PX, (EXT - p[1]) / PX) for p in pts]
        dr.line(pp, fill=255, width=int(m2px(0.0026)))
        drizzle = np.maximum(drizzle, np.asarray(img, np.float32) / 255)
    drizzle = blur(drizzle, m2px(0.0014)) * 0.9 * inside
    rough = mix(rough, 0.05, drizzle)
    A = mix(A, A * np.array([1.06, 0.97, 0.75], np.float32), drizzle * 0.35)

    # cavity / contact shading so toppings sit in the sauce
    ao1 = np.clip((blur(H, m2px(0.0015)) - H) / 0.0012, 0, 1)
    ao2 = np.clip((blur(H, m2px(0.005)) - H) / 0.003, 0, 1) * (prof < 0.05)
    A *= (1 - 0.35 * ao1 - 0.25 * ao2)[..., None]

    # --- branded section names ----------------------------------------------
    labels_meta = brand_labels(A, H, rough, d, th, prof)

    # crumbs of semolina on the crust foot
    grains = (fbm((N, N), 1400, 61, octaves=1) > 0.7).astype(np.float32) * smoothstep(0.95, 1.0, d) * inside
    A = mix(A, np.array([0.95, 0.80, 0.45], np.float32), blur(grains, 0.5) * 0.6)

    # fine colour variation
    A = A * (1 + 0.04 * n_hi[..., None])

    alpha = inside
    rgba = np.concatenate([np.clip(A, 0, 1), alpha[..., None]], -1)
    save_rgb(rgba, "pizza_albedo.png", mode="RGBA")
    Hn = H / 0.032
    save_gray16(Hn, "pizza_height.png")
    det = H - blur(H, 4)
    save_gray16(det / 0.002 + 0.5, "pizza_detail.png")
    np.save(os.path.join(OUT, "pizza_height.npy"), H.astype(np.float32)[::2, ::2])
    props = np.stack([np.clip(rough, 0, 1), np.clip(sss, 0, 1), np.zeros_like(sss)], -1)
    save_rgb(props, "pizza_props.png")

    # outline as polar samples (for meshing)
    angs = np.linspace(-np.pi, np.pi, 2048, endpoint=False)
    er = R0 * (1 + 0.022 * angular_noise(angs, 11, kmax=10, falloff=1.1) + 0.012 * np.cos(2 * (angs - 0.6)))
    meta = {"ext": EXT, "res": N, "height_scale": 0.032, "edge_angles": angs.tolist(), "edge_r": er.tolist(),
            "slices": [{"id": s[0], "label": s[1], "angle": s[2]} for s in SLICES], "labels": labels_meta}
    with open(os.path.join(OUT, "pizza_meta.json"), "w") as f:
        json.dump(meta, f)
    # preview
    prev = Image.fromarray((np.clip(A, 0, 1) * 255).astype(np.uint8)).resize((1024, 1024), Image.LANCZOS)
    prev.save(os.path.join(OUT, "pizza_preview.jpg"), quality=90)
    print("done")


def brand_labels(A, H, rough, d, th, prof):
    font_path = os.path.join(FONTS, os.environ.get("BRAND_FONT", "oswald700.ttf"))
    probe = ImageFont.truetype(font_path, 1000)
    cap_ratio = (probe.getbbox("H")[3] - probe.getbbox("H")[1]) / 1000.0
    mask = np.zeros((N, N), np.float32)
    meta = []
    for sid, text, ang in SLICES:
        top = np.sin(np.radians(ang)) > 0
        # sit on the side of the crest the camera sees
        r_text = R0 * (0.905 if top else 0.918)
        cap = 0.0118
        size_px = int(m2px(cap) / cap_ratio)
        font = ImageFont.truetype(font_path, size_px)
        tracking = 0.06 * size_px
        advs = [font.getlength(ch) + tracking for ch in text]
        L = sum(advs) * PX
        max_arc = r_text * np.radians(60) - 0.016
        if L > max_arc:
            scale = max_arc / L
            size_px = int(size_px * scale)
            font = ImageFont.truetype(font_path, size_px)
            tracking = 0.06 * size_px
            advs = [font.getlength(ch) + tracking for ch in text]
            L = sum(advs) * PX
        cap_px = cap_ratio * size_px
        pos = 0.0
        for ch, adv in zip(text, advs):
            mid = (pos + adv / 2) * PX
            pos += adv
            if ch == " ":
                continue
            off = (L / 2 - mid) / r_text
            a = np.radians(ang) + (off if top else -off)
            rot = np.degrees(a) - 90 if top else np.degrees(a) + 90
            S = int(size_px * 1.8)
            g = Image.new("L", (S, S), 0)
            dr = ImageDraw.Draw(g)
            # place glyph: advance centre at S/2, cap middle at S/2
            gx = S / 2 - (adv - tracking) / 2
            bb = font.getbbox("H")
            gy = S / 2 - (bb[1] + bb[3]) / 2
            dr.text((gx, gy), ch, font=font, fill=255)
            g = g.rotate(rot, resample=Image.BICUBIC)
            cx, cy = r_text * np.cos(a), r_text * np.sin(a)
            j = int(round((cx + EXT) / PX)) - S // 2
            i = int(round((EXT - cy) / PX)) - S // 2
            arr = np.asarray(g, np.float32) / 255
            mask[i:i + S, j:j + S] = np.maximum(mask[i:i + S, j:j + S], arr)
        meta.append({"id": sid, "font_px": size_px, "arc_m": L})

    rough_n = fbm((N, N), 900, 71, octaves=2)
    mid_n = fbm((N, N), 160, 72, octaves=3)
    # roughen the brand edges — irons never stamp clean
    soft = blur(mask, 2.2)
    core = smoothstep(0.38, 0.62, soft + 0.18 * rough_n + 0.12 * mid_n)
    inner = smoothstep(0.55, 0.95, blur(core, 3) + 0.15 * rough_n)
    halo = blur(core, m2px(0.0011)) * 1.4
    halo2 = blur(core, m2px(0.0026))
    scorch = np.array([0.36, 0.17, 0.06], np.float32)
    burnt = np.array([0.11, 0.055, 0.03], np.float32)
    black = np.array([0.04, 0.025, 0.02], np.float32)
    A[:] = mix(A, A * np.array([0.78, 0.62, 0.45], np.float32), np.clip(halo2 * 1.2, 0, 1) * 0.8)
    A[:] = mix(A, scorch, np.clip(halo, 0, 1) * 0.85)
    A[:] = mix(A, burnt, core)
    A[:] = mix(A, black, inner * 0.85 * (0.7 + 0.3 * mid_n))
    # branded depression with a slightly crisped lip
    H[:] = H - core * 0.0009 + np.clip(halo - core, 0, 1) * 0.00025 + inner * rough_n * 0.00015
    rough[:] = mix(rough, 0.95, core)
    return meta


if __name__ == "__main__":
    main()
