"""給餌室の見た目。

寸法は docs/blender-guide.md の「給餌室」どおり。新しい研究棟の金属パネルの壁で、
ステンレスの調理台、棚、餌のバケツ、散らばった肉の箱、天井の肉吊りレールがある。
冷蔵庫 (7.25, 50)、ロッカー (-7.55, 41)、カードキー（(-4, 51) の台の上）、北の扉はゲーム側で置くので空けておく。
"""
import math
import os

import bpy
import numpy as np
from mathutils import Vector

import textures as tx
from common import (H, T, assign_faces, box, collection, cylinder, export_glb, finish, floor, material, plane,
                    text, wall_x, wall_y)

ROOM = "feeding"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "assets", "models", "rooms",
                   ROOM + ".glb")

COUNTERS = ((-4.0, 44.0), (4.0, 44.0), (-4.0, 51.0))


def build():
    rng = np.random.default_rng(3)
    col = collection("Room_" + ROOM)

    m_panel = tx.metal_panel("feed_panel", seed=12, tint=(0.33, 0.36, 0.35))
    m_conc = tx.concrete("feed_concrete", seed=23)
    m_floor = tx.lab_floor("feed_floor", seed=32)
    m_puddle = tx.puddle("feed_puddle", seed=43)
    m_claw = tx.claw_marks("feed_claw", seed=63)
    m_hazard = tx.hazard("feed_hazard", seed=82)
    m_card = tx.wood("feed_cardboard", seed=99)   # 段ボールの代わりに木目を薄茶で使う
    m_steel = material("feed_stainless", (0.55, 0.56, 0.57), rough=0.28, metal=1.0)
    m_dark = material("feed_dark_metal", (0.06, 0.065, 0.07), rough=0.5, metal=0.7)
    m_bucket = material("feed_bucket", (0.55, 0.12, 0.05), rough=0.5)
    m_bucket2 = material("feed_bucket_blue", (0.08, 0.2, 0.4), rough=0.5)
    m_meat = material("feed_meat", (0.32, 0.05, 0.04), rough=0.35)
    m_stain = material("feed_stain", (0.08, 0.015, 0.01), rough=0.3)
    m_red = material("feed_emergency", (0.6, 0.02, 0.01), rough=0.3, emission=(1.0, 0.05, 0.02), emit_strength=6.0)
    m_sign = material("feed_sign", (0.8, 0.8, 0.76), rough=0.5)
    m_sign_txt = material("feed_sign_text", (0.05, 0.05, 0.05), rough=0.5)

    # --- 床と壁 ---------------------------------------------------------------------
    floor(col, "Floor", -8, 8, 38, 54, m_floor)
    south = [wall_x(col, "Wall_S", 38, -8, -2, [m_panel, m_conc], pad=0.0),
             wall_x(col, "Wall_S", 38, 2, 8, [m_panel, m_conc], pad=0.0)]
    for w in south:   # 通路側（旧棟）から見える面はコンクリート
        assign_faces(w, 1, lambda n, c: n.y < -0.5)
    wall_y(col, "Wall_W", -8, 38, 54, m_panel)
    wall_y(col, "Wall_E", 8, 38, 54, m_panel)
    wall_x(col, "Wall_N", 54, -8, -1, m_panel)
    wall_x(col, "Wall_N", 54, 1, 8, m_panel)
    # 開口の縁
    for x0, x1 in ((-2.0, -1.98), (1.98, 2.0)):
        box(col, "Opening_Jamb", x0, x1, 37.85, 38.15, 0, H, m_dark)
    for x0, x1 in ((-1.2, -1.0), (1.0, 1.2)):
        box(col, "Door_Frame", x0, x1, 53.82, 53.85, 0, 3.0, m_hazard, uv_scale=1.0)
    box(col, "Door_Frame", -1.2, 1.2, 53.82, 53.85, 3.0, 3.15, m_hazard, uv_scale=1.0)
    box(col, "Sign", -0.6, 0.6, 53.83, 53.85, 3.2, 3.4, m_sign)
    text(col, "LEVEL B2  ELEVATOR", (0.0, 53.825, 3.3), 0.08, m_sign_txt)
    # 幅木
    for x0, x1, y0, y1 in ((-7.85, -2, 38.15, 38.17), (2, 7.85, 38.15, 38.17), (-7.85, -7.83, 38.15, 53.85),
                           (7.83, 7.85, 38.15, 53.85), (-7.85, -1.2, 53.83, 53.85), (1.2, 7.85, 53.83, 53.85)):
        box(col, "Kick", x0, x1, y0, y1, 0, 0.15, m_dark)

    # --- 調理台（幅3×奥行1.2×高さ0.9） -------------------------------------------------------
    for i, (cx, cy) in enumerate(COUNTERS):
        box(col, "Counter_Top", cx - 1.5, cx + 1.5, cy - 0.6, cy + 0.6, 0.86, 0.9, m_steel, uv_scale=1.0)
        box(col, "Counter_Body", cx - 1.45, cx + 1.45, cy - 0.55, cy + 0.55, 0.12, 0.86, m_steel, uv_scale=1.0)
        box(col, "Counter_Kick", cx - 1.4, cx + 1.4, cy - 0.5, cy + 0.5, 0.0, 0.12, m_dark)
        for dx in (-0.73, 0.0, 0.73):
            box(col, "Counter_Door_Line", cx + dx - 0.005, cx + dx + 0.005, cy - 0.556, cy - 0.55, 0.15, 0.82, m_dark)
            box(col, "Counter_Handle", cx + dx + 0.1, cx + dx + 0.3, cy - 0.58, cy - 0.556, 0.75, 0.77, m_dark)
        if i < 2:
            # まな板、肉切り包丁、肉のかたまり（カードキーの台 (-4, 51) には置かない）
            box(col, "Board", cx - 0.9, cx - 0.2, cy - 0.3, cy + 0.2, 0.9, 0.93, m_card, uv_scale=1.0)
            box(col, "Meat", cx - 0.75, cx - 0.35, cy - 0.2, cy + 0.1, 0.93, 1.02, m_meat)
            box(col, "Cleaver", cx + 0.2, cx + 0.5, cy + 0.05, cy + 0.15, 0.9, 0.905, m_steel)
            plane(col, "Stain", cx - 0.2, cy, 0.902, 0.9, 0.6, m_stain, rot=(0, 0, rng.normal(0, 0.3)))

    # --- 棚（中心 (-7.45, 47)、幅0.8×奥行4×高さ2.4） -----------------------------------------------
    sx0, sx1, sy0, sy1 = -7.85, -7.05, 45.0, 49.0
    for x in (sx0 + 0.02, sx1 - 0.04):
        for y in (sy0 + 0.02, sy1 - 0.04):
            box(col, "Shelf_Post", x, x + 0.04, y, y + 0.04, 0, 2.4, m_dark)
    for z in (0.1, 0.7, 1.3, 1.9, 2.38):
        box(col, "Shelf_Board", sx0, sx1, sy0, sy1, z - 0.02, z, m_steel)
    for z in (0.1, 0.7, 1.3, 1.9):
        y = sy0 + 0.1
        while y < sy1 - 0.4:
            w = rng.uniform(0.3, 0.6)
            h = rng.uniform(0.25, 0.45)
            if rng.random() < 0.8:
                b = box(col, "Shelf_Box", -0.33, 0.33, -w / 2, w / 2, 0, h, m_card, uv_scale=1.0)
                b.location = (-7.45 + rng.normal(0, 0.03), y + w / 2, z)
                b.rotation_euler = (0, 0, rng.normal(0, 0.06))
            y += w + rng.uniform(0.05, 0.2)

    # --- 天井の肉吊りレール（中央を東西に） ----------------------------------------------------------
    cylinder(col, "Rail", (-6.0, 47.5, 3.0), (6.0, 47.5, 3.0), 0.03, m_steel)
    for x in (-5.5, -2.0, 2.0, 5.5):
        cylinder(col, "Rail_Rod", (x, 47.5, 3.0), (x, 47.5, 3.5), 0.012, m_dark, 6)
    for x in np.arange(-5.0, 5.5, 1.1):
        dz = rng.uniform(0.0, 0.25)
        cylinder(col, "Hook_Chain", (x, 47.5, 3.0), (x, 47.5, 2.55 - dz), 0.006, m_dark, 4)
        cylinder(col, "Hook", (x, 47.5, 2.55 - dz), (x + 0.06, 47.5, 2.4 - dz), 0.008, m_steel, 4)

    # --- 床の物（通り道と、冷蔵庫・ロッカーの場所はあける） ------------------------------------------------
    for i, (x, y, m) in enumerate(((-6.6, 39.0, m_bucket), (-6.1, 39.3, m_bucket2), (6.8, 39.2, m_bucket),
                                   (5.9, 52.9, m_bucket2), (-2.8, 52.8, m_bucket))):
        tipped = i == 1
        if tipped:
            cylinder(col, "Bucket", (x, y, 0.15), (x + 0.38, y + 0.1, 0.15), 0.15, m, 12)
            plane(col, "Stain", x + 0.7, y + 0.2, 0.006, 1.0, 0.7, m_stain, rot=(0, 0, 0.4))
        else:
            cylinder(col, "Bucket", (x, y, 0.0), (x, y, 0.38), 0.16, m, 12)
            cylinder(col, "Bucket_Meat", (x, y, 0.3), (x, y, 0.36), 0.14, m_meat, 10)
    for x, y, rz, tip in ((6.3, 41.5, 0.3, 0), (6.9, 42.3, -0.2, 0), (6.5, 42.0, 0.5, 1), (-6.4, 52.5, 0.1, 0),
                          (1.5, 41.0, 0.8, 1)):
        b = box(col, "Meat_Box", -0.3, 0.3, -0.22, 0.22, 0.0, 0.35, m_card, uv_scale=1.0)
        b.location = (x, y, 0.35 if tip else 0.0)
        b.rotation_euler = (math.radians(100) if tip else 0, 0, rz)
        if tip:
            box(col, "Meat_Spilled", x - 0.25, x + 0.2, y + 0.3, y + 0.6, 0.0, 0.08, m_meat)
            plane(col, "Stain", x, y + 0.6, 0.006, 1.2, 0.8, m_stain, rot=(0, 0, rz))

    # 引きずられた肉の跡（給餌室から通路へ）
    for i in range(10):
        plane(col, "Drag", 1.2 - i * 0.12, 40.8 - i * 0.28, 0.005, 0.35, 0.3, m_stain, rot=(0, 0, rng.normal(0.4, 0.2)))

    plane(col, "Puddle", 0.0, 46.5, 0.004, 4.6, 3.6, m_puddle)
    for x, y, z, rz in ((7.845, 45.0, 1.4, -90), (-7.845, 51.5, 1.2, 90)):
        plane(col, "Claw", x, y, z, 0.9, 1.1, m_claw, rot=(math.radians(90), 0, math.radians(rz)))
    plane(col, "Claw", 3.0, 53.845, 1.6, 1.0, 1.1, m_claw, rot=(math.radians(90), 0, math.radians(180)))

    # --- 照明（ゲームの赤い光 (-4, 42) と (4, 50)）と、消えた蛍光灯 ---------------------------------------
    for x, y in ((-4.0, 42.0), (4.0, 50.0)):
        box(col, "Lamp_Housing", x - 0.25, x + 0.25, y - 0.12, y + 0.12, 3.08, 3.18, m_dark)
        box(col, "Lamp_Lens", x - 0.2, x + 0.2, y - 0.09, y + 0.09, 3.05, 3.08, m_red)
        for dx in (-0.18, 0.18):
            cylinder(col, "Lamp_Rod", (x + dx, y, 3.18), (x + dx, y, 3.5), 0.01, m_dark, 6)
    for x, y in ((-4.0, 47.5), (4.0, 44.5), (0.0, 51.5)):
        box(col, "Fixture", x - 0.6, x + 0.6, y - 0.3, y + 0.3, 3.3, 3.38, m_steel)
    for x in (-7.6, 7.6):
        cylinder(col, "Pipe", (x, 38.15, 3.2), (x, 53.85, 3.2), 0.07, m_dark)

    finish(col, "Room_" + ROOM)
    return col


def export():
    export_glb(bpy.data.collections["Room_" + ROOM], os.path.abspath(OUT))
    print("書き出し:", os.path.abspath(OUT))
