"""部屋のテクスチャを numpy で作る。

壁のテクスチャは横 2m で1周、縦は床（下端）から天井（上端）まで。
だから床際の汚れや天井からの結露の垂れが、どの壁でも同じ高さに来る。
床のテクスチャは 2m 四方で1周。
"""
import numpy as np

from common import (H, TEX, dots_mask, lines_mask, mix, noise, normal_from_height, save_image,
                    smoothstep, streaks, textured_material)

WALL_H = TEX * 2   # 壁テクスチャの縦の画素数


def _heights(ny):
    """各行の床からの高さ（m）。行 0 が天井。"""
    return (1.0 - (np.arange(ny) + 0.5) / ny)[:, None] * H


def _orm(rough, metal, ao=None):
    ao = np.ones_like(rough) if ao is None else ao
    return np.dstack([ao, np.clip(rough, 0.02, 1), np.clip(metal, 0, 1)])


def metal_panel(name="panel", seed=10, tint=(0.30, 0.34, 0.36), dirt=1.0):
    """新しい研究棟の金属パネル壁。1m 幅のパネル、高さ 1.1m と 2.6m に横の継ぎ目。"""
    n, ny = TEX, WALL_H
    z = _heights(ny)
    seams_v = lines_mask(n, [0.0, 0.5], 0.004, 0, ny)
    seams_h = lines_mask(n, [1 - 1.1 / H, 1 - 2.6 / H], 0.0025, 1, ny)
    seams = np.maximum(seams_v, seams_h)
    rivet_x = [0.02, 0.48, 0.52, 0.98]
    rivet_y = [1 - zz / H for zz in (0.08, 1.02, 1.18, 1.9, 2.52, 2.68, 3.42)]
    rivets = dots_mask(n, rivet_x, rivet_y, 0.006, ny)

    big = noise(n, 2.4, seed, ny)
    mid = noise(n, 1.6, seed + 1, ny)
    fine = noise(n, 0.8, seed + 2, ny)
    # パネルごとに少しずつ色が違う
    panel_id = ((np.arange(n) // (n // 2))[None, :] * 3 + (z > 1.1) + (z > 2.6)).astype(float)
    panel_shift = (np.sin(panel_id * 12.9898) * 43758.5453) % 1.0

    col = np.zeros((ny, n, 3)) + np.array(tint)[None, None, :]
    col *= (0.88 + 0.16 * panel_shift + 0.10 * (mid - 0.5))[..., None]
    # 床際の汚れ（泥と水の跡）
    grime = smoothstep(0.9, 0.0, z) * (0.55 + 0.45 * big) * dirt
    grime += smoothstep(0.25, 0.0, z) * 0.4 * dirt
    col = mix(col, (0.09, 0.075, 0.055), np.clip(grime, 0, 0.92))
    # 天井から垂れる結露と錆の筋
    drip = streaks(n, seed + 3, 0.35, ny) * smoothstep(0.4, 3.4, z) * dirt
    col = mix(col, (0.16, 0.12, 0.09), drip * 0.55)
    rust = np.clip((big * 0.6 + fine * 0.4 - 0.62) * 4, 0, 1) * (0.3 + seams * 0.7 + rivets) * dirt
    rust = np.clip(rust + streaks(n, seed + 4, 0.15, ny) * smoothstep(1.3, 2.6, z) * 0.4 * dirt, 0, 1)
    col = mix(col, (0.32, 0.15, 0.06), rust * 0.8)
    col = mix(col, (0.05, 0.05, 0.05), seams * 0.85)
    col = mix(col, (0.42, 0.44, 0.45), rivets * 0.5)
    # 細かい傷
    scratch = np.clip((noise(n, 0.3, seed + 5, ny) - 0.8) * 6, 0, 1)
    col = mix(col, (0.5, 0.52, 0.53), scratch * 0.25)

    rough = 0.42 + 0.25 * fine + 0.3 * grime + 0.25 * rust - 0.25 * drip
    metal = 0.75 - 0.6 * np.clip(grime + rust, 0, 1)
    ao = 1.0 - seams * 0.6
    height = -seams * 1.0 + rivets * 0.8 + fine * 0.05 + (mid - 0.5) * 0.1
    base = save_image(name + "_base", col)
    orm = save_image(name + "_orm", _orm(rough, metal, ao), non_color=True)
    nrm = save_image(name + "_nrm", normal_from_height(height, 3.0), non_color=True)
    return textured_material(name, base, orm, nrm, 1.0)


def concrete(name="concrete", seed=20, tint=(0.36, 0.35, 0.32), wet=1.0):
    """古い旧棟のコンクリート壁。型枠の跡、湿ったしみ、カビ、垂れた水の跡。"""
    n, ny = TEX, WALL_H
    z = _heights(ny)
    big = noise(n, 2.6, seed, ny)
    mid = noise(n, 1.8, seed + 1, ny)
    fine = noise(n, 0.9, seed + 2, ny)
    pores = np.clip((noise(n, 0.2, seed + 3, ny) - 0.75) * 5, 0, 1)
    forms_v = lines_mask(n, [0.0, 0.6], 0.0025, 0, ny)
    forms_h = lines_mask(n, [1 - zz / H for zz in (1.2, 2.4)], 0.0015, 1, ny)
    ties = dots_mask(n, [0.15, 0.45, 0.75], [1 - zz / H for zz in (0.6, 1.8, 3.0)], 0.007, ny)

    col = np.zeros((ny, n, 3)) + np.array(tint)[None, None, :]
    col *= (0.8 + 0.3 * mid + 0.1 * fine)[..., None]
    damp = np.clip(smoothstep(1.4, 0.0, z) * (0.5 + 0.7 * big) * wet, 0, 1)
    col = mix(col, (0.12, 0.12, 0.10), damp * 0.75)
    mold = np.clip((big - 0.55) * 3, 0, 1) * smoothstep(1.2, 0.1, z) * wet
    col = mix(col, (0.10, 0.13, 0.07), mold * 0.6)
    drip = streaks(n, seed + 4, 0.45, ny) * smoothstep(0.2, 3.3, z) * wet
    col = mix(col, (0.15, 0.14, 0.12), drip * 0.6)
    rust = streaks(n, seed + 5, 0.08, ny) * ties.max(axis=0)[None, :] * smoothstep(0.0, 3.0, z)
    col = mix(col, (0.30, 0.16, 0.08), np.clip(rust * 2 + ties, 0, 1) * 0.6)
    col = mix(col, (0.08, 0.08, 0.07), np.maximum(forms_v, forms_h) * 0.4 + pores * 0.35)

    rough = 0.9 - 0.45 * damp - 0.35 * drip + 0.05 * fine
    height = mid * 0.3 + fine * 0.15 - pores * 0.6 - np.maximum(forms_v, forms_h) * 0.4 - ties * 0.5
    base = save_image(name + "_base", col)
    orm = save_image(name + "_orm", _orm(rough, np.zeros_like(rough), 1 - pores * 0.4), non_color=True)
    nrm = save_image(name + "_nrm", normal_from_height(height, 4.0), non_color=True)
    return textured_material(name, base, orm, nrm, 1.0)


def lab_floor(name="floor_new", seed=30, wet=1.0):
    """新棟の床。50cm 角の樹脂タイル、泥の足跡、ところどころ濡れて光る。"""
    n = TEX
    big = noise(n, 2.4, seed)
    mid = noise(n, 1.5, seed + 1)
    fine = noise(n, 0.7, seed + 2)
    grid = [i / 4 for i in range(4)]
    seams = np.maximum(lines_mask(n, grid, 0.003, 0), lines_mask(n, grid, 0.003, 1))
    # 線は v 方向にもタイルさせる（lines_mask の横線は端で切れるので、上下を足す）
    seams = np.maximum(seams, lines_mask(n, [0.0, 1.0], 0.003, 1))
    tile_id = ((np.arange(n) // (n // 4))[None, :] * 7 + (np.arange(n) // (n // 4))[:, None] * 3).astype(float)
    tile_shift = (np.sin(tile_id * 78.233) * 43758.5453) % 1.0

    col = np.zeros((n, n, 3)) + np.array([0.20, 0.21, 0.21])[None, None, :]
    col *= (0.85 + 0.2 * tile_shift + 0.15 * (mid - 0.5))[..., None]
    dirt = np.clip((big - 0.45) * 2.0, 0, 1)
    col = mix(col, (0.08, 0.065, 0.05), dirt * 0.7)
    scuff = np.clip((noise(n, 0.4, seed + 3) - 0.7) * 4, 0, 1)
    col = mix(col, (0.32, 0.32, 0.31), scuff * 0.3)
    col = mix(col, (0.05, 0.05, 0.05), seams * 0.8)
    water = np.clip((noise(n, 2.2, seed + 4) - (0.62 - 0.12 * wet)) * 6, 0, 1) * wet
    col = mix(col, (0.05, 0.05, 0.05), water * 0.35)

    rough = 0.55 + 0.25 * dirt + 0.1 * fine - 0.5 * water
    height = -seams + fine * 0.1 + water * 0.0
    base = save_image(name + "_base", col)
    orm = save_image(name + "_orm", _orm(rough, np.zeros_like(rough), 1 - seams * 0.5), non_color=True)
    nrm = save_image(name + "_nrm", normal_from_height(height, 3.0), non_color=True)
    return textured_material(name, base, orm, nrm, 1.0)


def concrete_floor(name="floor_old", seed=35, wet=1.0):
    """旧棟の床。打ちっぱなしのコンクリートにひび、泥、水の流れた跡。"""
    n = TEX
    big = noise(n, 2.5, seed)
    mid = noise(n, 1.6, seed + 1)
    fine = noise(n, 0.8, seed + 2)
    joints = np.maximum(lines_mask(n, [0.0], 0.003, 0), lines_mask(n, [0.0, 1.0], 0.003, 1))
    crack = np.clip(1 - np.abs(noise(n, 2.0, seed + 3) - 0.5) * 60, 0, 1) * np.clip((mid - 0.45) * 4, 0, 1)

    col = np.zeros((n, n, 3)) + np.array([0.27, 0.26, 0.24])[None, None, :]
    col *= (0.8 + 0.3 * mid + 0.1 * fine)[..., None]
    mud = np.clip((big - 0.5) * 2.5, 0, 1)
    col = mix(col, (0.10, 0.08, 0.05), mud * 0.8)
    water = np.clip((noise(n, 2.2, seed + 4) - (0.6 - 0.15 * wet)) * 5, 0, 1) * wet
    col = mix(col, (0.06, 0.06, 0.055), water * 0.45)
    col = mix(col, (0.05, 0.05, 0.045), np.maximum(joints, crack) * 0.8)

    rough = 0.85 - 0.6 * water + 0.05 * fine
    height = mid * 0.2 + fine * 0.2 - joints - crack * 0.8
    base = save_image(name + "_base", col)
    orm = save_image(name + "_orm", _orm(rough, np.zeros_like(rough)), non_color=True)
    nrm = save_image(name + "_nrm", normal_from_height(height, 4.0), non_color=True)
    return textured_material(name, base, orm, nrm, 1.0)


def straw(name="straw", seed=90):
    """ケージの床に散らばった藁。細い線をたくさん重ねた透過付きの絵。"""
    n = TEX // 2
    rng = np.random.default_rng(seed)
    a = np.zeros((n, n))
    col = np.zeros((n, n, 3))
    yy, xx = np.mgrid[0:n, 0:n]
    for _ in range(900):
        x0, y0 = rng.random(2) * n
        ang = rng.random() * np.pi
        ln = rng.uniform(20, 70)
        c = np.array([0.55, 0.45, 0.22]) * rng.uniform(0.45, 1.0)
        for t in np.linspace(0, 1, int(ln)):
            x = int(x0 + np.cos(ang) * ln * t) % n
            y = int(y0 + np.sin(ang) * ln * t) % n
            a[y, x] = 1
            col[y, x] = c
            a[y, (x + 1) % n] = 1
            col[y, (x + 1) % n] = c * 0.8
    # 中央に集まり、縁へ向かって少なくなる
    r = np.sqrt(((xx + 0.5) / n - 0.5) ** 2 + ((yy + 0.5) / n - 0.5) ** 2) * 2
    a *= smoothstep(1.0, 0.6, r + noise(n, 2.0, seed + 1) * 0.4 - 0.2)
    base = save_image(name + "_base", np.dstack([col, a]))
    m = textured_material(name, base, alpha_from_base=True)
    bsdf = next(nd for nd in m.node_tree.nodes if nd.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Roughness"].default_value = 0.9
    return m


def wood(name="wood", seed=95):
    """木箱の板。木目と、湿って黒ずんだ下側。uv は 1m で1周。"""
    n = TEX // 2
    yy, xx = np.mgrid[0:n, 0:n]
    grain = noise(n, 1.0, seed, n)
    warp = noise(n, 2.4, seed + 1)
    rings = 0.5 + 0.5 * np.sin((yy / n * 40 + warp * 6) * np.pi)
    boards = lines_mask(n, [0.0, 0.25, 0.5, 0.75], 0.004, 1)
    col = np.zeros((n, n, 3)) + np.array([0.36, 0.25, 0.14])[None, None, :]
    col *= (0.75 + 0.2 * rings + 0.15 * grain)[..., None]
    col = mix(col, (0.08, 0.06, 0.04), boards * 0.9)
    col = mix(col, (0.12, 0.10, 0.07), np.clip((noise(n, 2.2, seed + 2) - 0.55) * 3, 0, 0.8))
    rough = 0.8 + 0.1 * grain
    height = rings * 0.2 - boards
    base = save_image(name + "_base", col)
    orm = save_image(name + "_orm", _orm(rough, np.zeros_like(rough)), non_color=True)
    nrm = save_image(name + "_nrm", normal_from_height(height, 3.0), non_color=True)
    return textured_material(name, base, orm, nrm, 1.0)


def rust_metal(name="rust", seed=97):
    """錆びた鉄（格子や配管用）。uv は 1m で1周。"""
    n = TEX // 2
    big = noise(n, 2.2, seed)
    fine = noise(n, 0.7, seed + 1)
    flakes = np.clip((noise(n, 1.2, seed + 2) - 0.5) * 4, 0, 1)
    col = np.zeros((n, n, 3)) + np.array([0.20, 0.19, 0.18])[None, None, :]
    col = mix(col, (0.30, 0.13, 0.05), np.clip(big * 0.8 + flakes * 0.5, 0, 1))
    col = mix(col, (0.12, 0.06, 0.03), np.clip((fine - 0.6) * 3, 0, 0.6))
    rough = 0.6 + 0.35 * flakes
    metal = 0.8 - 0.7 * flakes
    base = save_image(name + "_base", col)
    orm = save_image(name + "_orm", _orm(rough, metal), non_color=True)
    nrm = save_image(name + "_nrm", normal_from_height(fine * 0.5 + flakes * 0.5, 3.0), non_color=True)
    return textured_material(name, base, orm, nrm, 1.0)


def puddle(name="puddle", seed=40):
    """水たまり。縁が透けて薄くなる、ほぼ鏡のような面。"""
    n = TEX // 2
    yy, xx = np.mgrid[0:n, 0:n]
    r = np.sqrt(((xx + 0.5) / n - 0.5) ** 2 + ((yy + 0.5) / n - 0.5) ** 2) * 2
    wobble = noise(n, 2.0, seed) * 0.35
    a = smoothstep(1.0, 0.55, r + wobble - 0.1)
    col = np.dstack([np.full((n, n), 0.03), np.full((n, n), 0.035), np.full((n, n), 0.035), a])
    base = save_image(name + "_base", col)
    # 半透明（BLEND）は Godot で黒い四角になったので、輪郭で切り抜く（MASK）
    m = textured_material(name, base, alpha_from_base=True, blend=False)
    bsdf = next(nd for nd in m.node_tree.nodes if nd.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Roughness"].default_value = 0.03
    return m


def paper(name="paper", seed=50):
    """散らばった書類（4枚分を 2×2 に並べた画像）。"""
    n = TEX // 2
    rng = np.random.default_rng(seed)
    col = np.ones((n, n, 3)) * np.array([0.78, 0.76, 0.70])
    q = n // 2
    for i in range(2):
        for j in range(2):
            y0, x0 = i * q, j * q
            for k in range(int(rng.integers(10, 16))):
                ly = y0 + 30 + k * 13
                if ly > y0 + q - 25:
                    break
                lw = int(rng.integers(q // 3, q - 60))
                col[ly:ly + 3, x0 + 24:x0 + 24 + lw] = (0.25, 0.25, 0.27)
            if (i + j) % 2 == 0:   # 表やグラフの枠
                col[y0 + q // 2:y0 + q // 2 + 2, x0 + 24:x0 + q - 24] = (0.3, 0.3, 0.32)
                col[y0 + 20:y0 + q - 20, x0 + q // 2:x0 + q // 2 + 2] = (0.3, 0.3, 0.32)
            col[y0 + 12:y0 + 22, x0 + 24:x0 + 90] = (0.55, 0.12, 0.10)   # 赤い判子のような印
    stain = noise(n, 2.0, seed + 1)
    col = mix(col, (0.45, 0.38, 0.26), np.clip((stain - 0.6) * 2.5, 0, 0.7))
    base = save_image(name + "_base", col)
    m = textured_material(name, base)
    bsdf = next(nd for nd in m.node_tree.nodes if nd.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Roughness"].default_value = 0.85
    return m


def claw_marks(name="claw", seed=60):
    """恐竜の爪痕（3本の深い溝）。透過付きで壁や床に貼る。"""
    n = TEX // 2
    yy, xx = np.mgrid[0:n, 0:n]
    u = (xx + 0.5) / n
    v = (yy + 0.5) / n
    a = np.zeros((n, n))
    rng = np.random.default_rng(seed)
    for k, off in enumerate((-0.22, 0.0, 0.2)):
        cx = 0.5 + off + (v - 0.5) * 0.35 + 0.02 * np.sin(v * 9 + k)
        width = 0.035 * np.sin(np.clip(v, 0.05, 0.95) * np.pi) ** 0.7 * (0.8 + 0.4 * rng.random())
        d = np.abs(u - cx)
        a = np.maximum(a, smoothstep(width, width * 0.3, d) * smoothstep(0.02, 0.15, v) * smoothstep(0.98, 0.8, v))
    rough_edge = noise(n, 1.0, seed + 1)
    a = np.clip(a * (0.7 + 0.6 * rough_edge), 0, 1)
    col = np.dstack([np.full((n, n), 0.05), np.full((n, n), 0.045), np.full((n, n), 0.04), a])
    base = save_image(name + "_base", col)
    nrm = save_image(name + "_nrm", normal_from_height(-a, 6.0), non_color=True)
    m = textured_material(name, base, normal=nrm, alpha_from_base=True)
    bsdf = next(nd for nd in m.node_tree.nodes if nd.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Roughness"].default_value = 0.9
    return m


def cracked_screen(name="screen_broken", seed=70):
    """割れて消えたモニター。ひびの線がかすかに光る。"""
    n = TEX // 2
    rng = np.random.default_rng(seed)
    col = np.zeros((n, n, 3)) + 0.015
    crack = np.zeros((n, n))
    cx, cy = rng.integers(n // 3, 2 * n // 3, 2)
    for k in range(14):
        ang = rng.random() * 2 * np.pi
        x, y = float(cx), float(cy)
        for s in range(int(rng.integers(40, 120))):
            ang += rng.normal(0, 0.25)
            x += np.cos(ang) * 3
            y += np.sin(ang) * 3
            if not (1 <= x < n - 1 and 1 <= y < n - 1):
                break
            crack[int(y) - 1:int(y) + 1, int(x) - 1:int(x) + 1] = 1
    yy, xx = np.mgrid[0:n, 0:n]
    ring = np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * 18.0 ** 2))
    crack = np.clip(crack + ring * 0.8, 0, 1)
    col = mix(col, (0.35, 0.38, 0.40), crack * 0.7)
    base = save_image(name + "_base", col)
    rough = 0.05 + crack * 0.6
    orm = save_image(name + "_orm", _orm(rough, np.zeros_like(rough)), non_color=True)
    emit = save_image(name + "_emit", np.dstack([crack * 0.05, crack * 0.09, crack * 0.11]))
    return textured_material(name, base, orm, emission=emit, emit_strength=1.0)


def hazard(name="hazard", seed=80):
    """出入口の枠に貼る黄色と黒の警告ストライプ（はがれと汚れ付き）。"""
    n = TEX // 2
    yy, xx = np.mgrid[0:n, 0:n]
    stripe = (((xx + yy) / (n / 4)) % 1.0) < 0.5
    col = np.where(stripe[..., None], np.array([0.75, 0.55, 0.05]), np.array([0.04, 0.04, 0.04]))
    wear = np.clip((noise(n, 1.4, seed) - 0.6) * 3, 0, 1)
    col = mix(col, (0.28, 0.29, 0.30), wear)
    dirt = noise(n, 2.2, seed + 1)
    col = col * (0.6 + 0.4 * dirt)[..., None]
    base = save_image(name + "_base", col)
    rough = 0.6 + 0.3 * wear
    orm = save_image(name + "_orm", _orm(rough, wear * 0.7), non_color=True)
    return textured_material(name, base, orm)
