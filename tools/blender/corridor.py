"""飼育通路（ケージ含む）の見た目。

寸法は docs/blender-guide.md の「飼育通路」どおり。古いコンクリートの旧棟で、壁は湿って汚れ、格子は錆びている。
格子はゲームの当たり判定と同じ位置に立て、壊れた部分（各ケージの中心 ±0.8m）には通り道をふさぐ物を置かない。
"""
import math
import os

import bpy
import numpy as np
from mathutils import Vector

import textures as tx
from common import (H, T, box, collection, cylinder, export_glb, finish, floor, material, plane, quad_uv,
                    text, wall_x, wall_y)

ROOM = "corridor"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "assets", "models", "rooms",
                   ROOM + ".glb")

Y0, Y1 = 8.0, 38.0
CAGES = (14.0, 22.0, 30.0)
HALF = 2.5
GAP = 0.8
LOCKERS = ((-1.65, 18.0), (1.65, 26.0))   # ゲーム側のロッカー。ここには何も置かない


def bar_positions(c):
    """ゲームの _build_cage と同じ並び。壊れた所は (y, False)。"""
    out = []
    y = c - HALF + 0.2
    while y < c + HALF - 0.1:
        out.append((y, abs(y - c) > GAP))
        y += 0.35
    return out


def build():
    rng = np.random.default_rng(2)
    col = collection("Room_" + ROOM)

    m_conc = tx.concrete("cor_concrete", seed=22)
    m_floor = tx.concrete_floor("cor_floor", seed=36)
    m_rust = tx.rust_metal("cor_rust", seed=98)
    m_wood = tx.wood("cor_wood", seed=96)
    m_straw = tx.straw("cor_straw", seed=91)
    m_claw = tx.claw_marks("cor_claw", seed=62)
    m_puddle = tx.puddle("cor_puddle", seed=42)
    m_dark = material("cor_dark_metal", (0.06, 0.06, 0.06), rough=0.6, metal=0.6)
    m_pipe = material("cor_pipe", (0.18, 0.16, 0.13), rough=0.7, metal=0.6)
    m_pipe_g = material("cor_pipe_green", (0.12, 0.2, 0.14), rough=0.7, metal=0.3)
    m_red = material("cor_emergency", (0.6, 0.02, 0.01), rough=0.3, emission=(1.0, 0.05, 0.02), emit_strength=6.0)
    m_bone = material("cor_bone", (0.62, 0.58, 0.48), rough=0.7)
    m_line = material("cor_floor_line", (0.45, 0.38, 0.12), rough=0.8)
    m_sign = material("cor_sign", (0.55, 0.5, 0.2), rough=0.7, metal=0.3)
    m_sign_txt = material("cor_sign_text", (0.04, 0.04, 0.04), rough=0.6)
    m_blood = material("cor_stain", (0.07, 0.02, 0.015), rough=0.4)

    # --- 床と壁 ---------------------------------------------------------------------
    floor(col, "Floor", -2, 2, Y0, Y1, m_floor)
    for s in (-1, 1):
        x = 2.0 * s
        y_prev = Y0
        for c in CAGES:
            wall_y(col, "Wall", x, y_prev, c - HALF, m_conc, pad=0.0)
            y_prev = c + HALF
            _cage(col, rng, s, c, m_conc, m_floor, m_rust, m_straw, m_claw, m_bone, m_dark, m_sign, m_sign_txt, m_blood)
        wall_y(col, "Wall", x, y_prev, Y1, m_conc, pad=0.0)
        # 床の端の色あせた黄色い線（ケージの格子の前は途切れる）
        for a, b in ((Y0, CAGES[0] - HALF), (CAGES[0] + HALF, CAGES[1] - HALF),
                     (CAGES[1] + HALF, CAGES[2] - HALF), (CAGES[2] + HALF, Y1)):
            lx = 1.7 * s
            box(col, "Floor_Line", lx - 0.05, lx + 0.05, a + 0.1, b - 0.1, 0.0, 0.002, m_line)

    # --- 木箱（西の奥のケージ） -------------------------------------------------------------
    box(col, "Crate", -4.7, -3.7, 30.5, 31.5, 0.0, 1.0, m_wood, uv_scale=1.0)
    for z in (0.08, 0.92):
        box(col, "Crate_Band", -4.72, -3.68, 30.48, 31.52, z - 0.03, z + 0.03, m_dark)
    c2 = box(col, "Crate_Small", -0.3, 0.3, -0.3, 0.3, 0.0, 0.5, m_wood, uv_scale=1.0)
    c2.location = (-4.3, 32.3, 0.0)
    c2.rotation_euler = (0, 0, math.radians(20))

    # --- 水たまり（X -1.5〜1.5、Y 21〜24。ゲームで足音が大きくなる所） ----------------------------------
    plane(col, "Puddle", 0.0, 22.5, 0.004, 3.6, 3.8, m_puddle, rot=(0, 0, math.radians(3)))
    box(col, "Drain", -0.25, 0.25, 22.25, 22.75, 0.0, 0.006, m_dark)
    for k in range(5):
        y = 22.3 + k * 0.1
        box(col, "Drain_Slot", -0.2, 0.2, y, y + 0.03, 0.006, 0.008, m_pipe)

    # --- 天井まわり ------------------------------------------------------------------
    for x, r, m in ((-1.62, 0.09, m_pipe), (1.65, 0.06, m_pipe_g), (-1.35, 0.04, m_pipe)):
        cylinder(col, "Pipe", (x, Y0, 3.18), (x, Y1, 3.18), r, m)
    for y in np.arange(Y0 + 1.0, Y1, 2.5):
        box(col, "Pipe_Hanger", -1.8, 1.8, y - 0.03, y + 0.03, 3.3, 3.34, m_dark)
        for x in (-1.75, 1.75):
            cylinder(col, "Pipe_Rod", (x, y, 3.34), (x, y, 3.5), 0.01, m_dark, 6)
    # 水たまりの上で継ぎ目が割れて漏れている配管
    box(col, "Pipe_Leak", -1.75, -1.49, 22.35, 22.6, 3.05, 3.31, m_rust)
    # 非常灯（ゲームの赤い光の位置 y=12, 20, 28, 36）
    for y in (12.0, 20.0, 28.0, 36.0):
        box(col, "Lamp_Base", -0.18, 0.18, y - 0.12, y + 0.12, 3.38, 3.5, m_dark)
        box(col, "Lamp_Lens", -0.13, 0.13, y - 0.08, y + 0.08, 3.22, 3.38, m_red)
        for dx in (-0.14, -0.05, 0.05, 0.14):
            box(col, "Lamp_Cage", dx - 0.008, dx + 0.008, y - 0.1, y + 0.1, 3.2, 3.38, m_dark)

    # --- 通路の壁の爪痕としみ ------------------------------------------------------------
    for x, y, z, rz in ((1.845, 10.0, 1.3, -90), (-1.845, 25.6, 1.0, 90), (-1.845, 34.5, 1.6, 90)):
        plane(col, "Claw", x, y, z, 0.8, 1.0, m_claw, rot=(math.radians(90), 0, math.radians(rz)))
    plane(col, "Claw_Floor", 0.6, 16.0, 0.006, 0.8, 1.0, m_claw, rot=(0, 0, math.radians(-20)))
    plane(col, "Claw_Floor", -0.4, 33.0, 0.006, 0.7, 0.9, m_claw, rot=(0, 0, math.radians(160)))
    # 引きずった跡のような黒っぽいしみ
    for i in range(6):
        y = 13.5 + i * 0.5
        plane(col, "Stain", 2.6 - i * 0.25, y, 0.005, 0.5, 0.25, m_blood, rot=(0, 0, rng.normal(0.5, 0.2)))

    finish(col, "Room_" + ROOM)
    return col


def _cage(col, rng, s, c, m_conc, m_floor, m_rust, m_straw, m_claw, m_bone, m_dark, m_sign, m_sign_txt, m_blood):
    x_in, x_back = 2.0 * s, 5.0 * s
    floor(col, "Cage_Floor", min(x_in, x_back), max(x_in, x_back), c - HALF, c + HALF, m_floor)
    wall_y(col, "Cage_Back", x_back, c - HALF, c + HALF, m_conc)
    wall_x(col, "Cage_Side", c - HALF, x_in, x_back, m_conc)
    wall_x(col, "Cage_Side", c + HALF, x_in, x_back, m_conc)

    # 鉄格子
    bars = bar_positions(c)
    gap_lo = max(y for y, ok in bars if ok and y < c)
    gap_hi = min(y for y, ok in bars if ok and y > c)
    for y, ok in bars:
        if ok:
            if y in (gap_lo, gap_hi):
                # 壊れた所の両隣はこじ開けられたように外へ曲がっている
                away = -0.12 if y < c else 0.12
                pts = [Vector((x_in, y, 0.0)), Vector((x_in + 0.05 * s, y + away * 0.5, 0.9)),
                       Vector((x_in + 0.12 * s, y + away, 1.7)), Vector((x_in + 0.05 * s, y + away * 0.5, 2.6)),
                       Vector((x_in, y, H))]
                for a, b in zip(pts, pts[1:]):
                    cylinder(col, "Bar_Bent", a, b, 0.04, m_rust, 8)
            else:
                cylinder(col, "Bar", (x_in, y, 0.0), (x_in, y, H), 0.04, m_rust, 8)
        else:
            # 壊れた格子: 上から垂れ下がる折れた端と、床に残った根元
            top = rng.uniform(2.3, 2.9)
            lean = rng.uniform(0.1, 0.35) * s
            cylinder(col, "Bar_Stub_Top", (x_in, y, H), (x_in + lean, y + rng.normal(0, 0.05), top), 0.04, m_rust, 8)
            cylinder(col, "Bar_Stub_Bottom", (x_in, y, 0.0), (x_in, y, rng.uniform(0.04, 0.12)), 0.04, m_rust, 8)
    # 横の桟（上は全体、下と中段は壊れていない所だけ）
    for z in (3.25,):
        box(col, "Bar_Rail", x_in - 0.05, x_in + 0.05, c - HALF, c + HALF, z - 0.04, z + 0.04, m_rust)
    for ya, yb in ((c - HALF, gap_lo + 0.05), (gap_hi - 0.05, c + HALF)):
        for z in (0.15, 1.15):
            box(col, "Bar_Rail", x_in - 0.04, x_in + 0.04, ya, yb, z - 0.03, z + 0.03, m_rust)

    # ケージ番号の札（壊れた所の上）
    idx = CAGES.index(c) + 1
    side = "E" if s > 0 else "W"
    face = x_in - 0.06 * s
    box(col, "Cage_Sign", min(face, face - 0.02 * s), max(face, face - 0.02 * s), c - 0.35, c + 0.35, 2.85, 3.12, m_sign)
    text(col, "PEN %d-%s" % (idx, side), (face - 0.021 * s, c, 2.985), 0.13, m_sign_txt,
         rot=(math.radians(90), 0, math.radians(-90 if s > 0 else 90)))

    # 藁、骨、餌桶、爪痕
    for k in range(5):
        cx = (x_in + x_back) / 2 + rng.normal(0, 0.6) * s
        cy = c + rng.normal(0, 1.1)
        cx = float(np.clip(abs(cx), 2.4, 4.6)) * s
        cy = float(np.clip(cy, c - 2.0, c + 2.0))
        p = plane(col, "Straw", cx, cy, 0.007 + k * 0.001, rng.uniform(1.2, 2.0), rng.uniform(1.2, 2.0), m_straw,
                  rot=(0, 0, rng.random() * math.tau))
    for k in range(3):
        bx = float(np.clip(abs(x_back) - 0.6 + rng.normal(0, 0.3), 3.0, 4.6)) * s
        by = c + rng.uniform(-1.8, 1.8)
        a = rng.random() * math.tau
        ln = rng.uniform(0.3, 0.6)
        p0 = Vector((bx, by, 0.035))
        p1 = p0 + Vector((math.cos(a) * ln, math.sin(a) * ln, 0.0))
        cylinder(col, "Bone", p0, p1, 0.025, m_bone, 8)
        for p in (p0, p1):
            cylinder(col, "Bone_End", p - Vector((0, 0, 0.02)), p + Vector((0, 0, 0.03)), 0.045, m_bone, 8)
    tx0 = abs(x_back) - 0.65
    box(col, "Trough", min(tx0 * s, (tx0 + 0.5) * s), max(tx0 * s, (tx0 + 0.5) * s),
        c + HALF - 0.95, c + HALF - 0.25, 0.0, 0.35, m_dark)
    plane(col, "Claw", x_back - 0.155 * s, c + rng.uniform(-1, 1), rng.uniform(1.0, 1.8), 1.0, 1.2, m_claw,
          rot=(math.radians(90), rng.normal(0, 0.3), math.radians(90 if s > 0 else -90)))
    plane(col, "Claw", (x_in + x_back) / 2, c - HALF + 0.155, rng.uniform(0.8, 1.6), 0.8, 1.0, m_claw,
          rot=(math.radians(90), rng.normal(0, 0.3), 0))
    plane(col, "Stain", (x_in + x_back) / 2 + rng.normal(0, 0.3), c + rng.normal(0, 0.8), 0.006,
          rng.uniform(0.6, 1.2), rng.uniform(0.4, 0.9), m_blood, rot=(0, 0, rng.random() * math.tau))


def export():
    export_glb(bpy.data.collections["Room_" + ROOM], os.path.abspath(OUT))
    print("書き出し:", os.path.abspath(OUT))
