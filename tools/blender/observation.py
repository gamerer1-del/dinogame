"""観察室（スタート地点）の見た目。

寸法は docs/blender-guide.md の「観察室」どおり。当たり判定はゲーム側の箱なので、
壁・机・コンソールの外形はその箱と同じ位置に置き、細かい物は通り道の邪魔にならない所だけに置く。
"""
import math
import os

import bmesh
import bpy
import numpy as np
from mathutils import Vector

import textures as tx
from common import (H, T, assign_faces, bake_transforms, box, collection, cylinder, export_glb,
                    floor, join_all, material, plane, wall_x, wall_y, world_uv)

ROOM = "observation"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "assets", "models", "rooms",
                   ROOM + ".glb")

DOOR_X = (-1.85, 0.6)      # 出入口
WIN_X = (0.795, 1.845)     # 観察窓（ゲームの箱と同じ 1.05m 幅）
NORTH = 8.0


def build():
    rng = np.random.default_rng(1)
    col = collection("Room_" + ROOM)

    m_panel = tx.metal_panel("obs_panel", seed=11)
    m_conc = tx.concrete("obs_concrete", seed=21)
    m_floor = tx.lab_floor("obs_floor", seed=31)
    m_puddle = tx.puddle("obs_puddle", seed=41)
    m_paper = tx.paper("obs_paper", seed=51)
    m_claw = tx.claw_marks("obs_claw", seed=61)
    m_screen = tx.cracked_screen("obs_screen", seed=71)
    m_hazard = tx.hazard("obs_hazard", seed=81)
    m_steel = material("obs_steel", (0.42, 0.44, 0.45), rough=0.35, metal=0.9)
    m_dark = material("obs_dark_metal", (0.07, 0.075, 0.08), rough=0.5, metal=0.7)
    m_desk = material("obs_desk_top", (0.32, 0.33, 0.32), rough=0.55, metal=0.2)
    m_pipe = material("obs_pipe", (0.24, 0.20, 0.16), rough=0.6, metal=0.7)
    m_pipe_y = material("obs_pipe_yellow", (0.55, 0.42, 0.08), rough=0.55, metal=0.4)
    m_glass = material("obs_glass", (0.25, 0.32, 0.33), rough=0.05, metal=0.0, alpha=0.22, blend=True)
    m_red = material("obs_emergency", (0.6, 0.02, 0.01), rough=0.3,
                     emission=(1.0, 0.05, 0.02), emit_strength=6.0)
    m_amber = material("obs_amber", (0.4, 0.2, 0.02), rough=0.3,
                       emission=(1.0, 0.45, 0.05), emit_strength=2.0)
    m_diffuser = material("obs_diffuser_dead", (0.55, 0.56, 0.55), rough=0.4)
    m_plastic = material("obs_plastic", (0.12, 0.12, 0.13), rough=0.5)
    m_chair = material("obs_chair", (0.09, 0.11, 0.14), rough=0.8)
    m_cable = material("obs_cable", (0.02, 0.02, 0.02), rough=0.6)
    m_sign = material("obs_sign", (0.85, 0.85, 0.82), rough=0.5)
    m_sign_txt = material("obs_sign_text", (0.05, 0.05, 0.05), rough=0.5)

    # --- 床と壁 ---------------------------------------------------------------------
    floor(col, "Floor", -5, 5, 0, NORTH, m_floor)
    wall_x(col, "Wall_S", 0, -5, 5, m_panel)
    wall_y(col, "Wall_W", -5, 0, NORTH, m_panel)
    wall_y(col, "Wall_E", 5, 0, NORTH, m_panel)
    walls_n = [
        wall_x(col, "Wall_N_W", NORTH, -5, -2, [m_panel, m_conc]),
        wall_x(col, "Wall_N_Pillar", NORTH, 0.6, 0.8, [m_panel, m_conc], pad=0.0),
        wall_x(col, "Wall_N_E", NORTH, 2, 5, [m_panel, m_conc]),
        box(col, "Wall_N_Sill", WIN_X[0], WIN_X[1], NORTH - T / 2, NORTH + T / 2, 0, 1.0, [m_panel, m_conc]),
    ]
    # 北の壁の向こう側（通路から見える面）は旧棟のコンクリート
    for w in walls_n:
        assign_faces(w, 1, lambda n, c: n.y > 0.5)

    # --- 観察窓 ---------------------------------------------------------------------
    box(col, "Window_Glass", WIN_X[0], WIN_X[1], NORTH - 0.04, NORTH + 0.04, 1.0, H, m_glass)
    for y in (NORTH - T / 2 - 0.03, NORTH + T / 2):
        box(col, "Window_Sill", WIN_X[0] - 0.05, WIN_X[1] + 0.05, y, y + 0.03, 0.95, 1.05, m_steel)
        for x in (WIN_X[0], WIN_X[1] - 0.06):
            box(col, "Window_Jamb", x, x + 0.06, y, y + 0.03, 1.0, 3.3, m_steel)
        box(col, "Window_Head", WIN_X[0], WIN_X[1], y, y + 0.03, 3.24, 3.3, m_steel)
        box(col, "Window_Mullion", WIN_X[0], WIN_X[1], y, y + 0.03, 2.2, 2.25, m_steel)

    # --- 出入口の枠（警告ストライプ） ----------------------------------------------------------
    y_in = NORTH - T / 2
    for x0, x1 in ((DOOR_X[0] - 0.12, DOOR_X[0]), (DOOR_X[1], DOOR_X[1] + 0.12)):
        box(col, "Door_Frame", x0, x1, y_in - 0.025, y_in, 0, 3.0, m_hazard, uv_scale=1.0)
        box(col, "Door_Frame_N", x0, x1, NORTH + T / 2, NORTH + T / 2 + 0.025, 0, 3.0, m_hazard, uv_scale=1.0)
    box(col, "Door_Header", DOOR_X[0] - 0.12, DOOR_X[1] + 0.12, y_in - 0.025, y_in, 3.0, 3.15, m_hazard, uv_scale=1.0)
    # 開口の内側の面に沿った鋼の縁
    for x0, x1 in ((DOOR_X[0], DOOR_X[0] + 0.02), (DOOR_X[1] - 0.02, DOOR_X[1])):
        box(col, "Door_Jamb", x0, x1, NORTH - T / 2, NORTH + T / 2, 0, H, m_steel)
    box(col, "Door_Threshold", DOOR_X[0], DOOR_X[1], NORTH - T / 2, NORTH + T / 2, 0, 0.01, m_steel)

    # --- 幅木 --------------------------------------------------------------------------
    kick = 0.15
    box(col, "Kick_S", -4.85, 4.85, 0.15, 0.17, 0, kick, m_dark)
    box(col, "Kick_W", -4.85, -4.83, 0.15, 7.85, 0, kick, m_dark)
    box(col, "Kick_E", 4.83, 4.85, 0.15, 7.85, 0, kick, m_dark)
    box(col, "Kick_N1", -4.85, DOOR_X[0] - 0.12, 7.83, 7.85, 0, kick, m_dark)
    box(col, "Kick_N2", DOOR_X[1] + 0.12, 4.85, 7.83, 7.85, 0, kick, m_dark)

    # --- 天井まわり（配管、ケーブルトレイ、照明） ----------------------------------------------------
    for x, s in ((-4.72, 1), (4.72, -1)):
        cylinder(col, "Pipe_Big", (x, 0.15, 3.15), (x, 7.85, 3.15), 0.08, m_pipe)
        cylinder(col, "Pipe_Small", (x + 0.05 * s, 0.15, 2.93), (x + 0.05 * s, 7.85, 2.93), 0.035, m_pipe_y)
        for y in np.arange(0.8, 7.8, 1.5):
            box(col, "Pipe_Clamp", x - 0.13, x + 0.13, y - 0.03, y + 0.03, 2.88, 3.26, m_dark)
    # 南の壁沿いのケーブルトレイ
    box(col, "CableTray", -4.85, 4.85, 0.18, 0.48, 3.25, 3.28, m_steel)
    for y0 in (0.18, 0.45):
        box(col, "CableTray_Lip", -4.85, 4.85, y0, y0 + 0.03, 3.25, 3.33, m_steel)
    for i in range(5):
        cylinder(col, "Tray_Cable", (-4.85, 0.25 + i * 0.045, 3.3), (4.85, 0.25 + i * 0.045, 3.3), 0.018, m_cable, 6)

    # 非常灯（ゲームの赤い光の位置 (0, 4, 3.0) に器具を吊るす）
    for rx in (-0.18, 0.18):
        cylinder(col, "Lamp_Rod", (rx, 4.0, 3.12), (rx, 4.0, 3.42), 0.01, m_dark, 6)
    box(col, "Lamp_Housing", -0.25, 0.25, 3.88, 4.12, 3.08, 3.18, m_dark)
    box(col, "Lamp_Lens", -0.2, 0.2, 3.91, 4.09, 3.05, 3.08, m_red)
    # 壁付けの小さな非常表示灯
    for x, y, nx in ((-4.83, 2.0, 1), (4.83, 6.0, -1)):
        box(col, "Wall_Lamp", min(x, x + 0.08 * nx), max(x, x + 0.08 * nx), y - 0.12, y + 0.12, 2.6, 2.72, m_dark)
        box(col, "Wall_Lamp_Lens", min(x + 0.08 * nx, x + 0.09 * nx), max(x + 0.08 * nx, x + 0.09 * nx),
            y - 0.1, y + 0.1, 2.62, 2.7, m_red)
    # 消えた蛍光灯（1本は片方の吊り線が切れて垂れ下がっている）
    for x, y in ((-2.5, 2.2), (2.5, 2.2), (-2.5, 5.8)):
        for dy in (-0.55, 0.55):
            cylinder(col, "Fixture_Wire", (x, y + dy, 3.25), (x, y + dy, 3.42), 0.005, m_cable, 4)
        box(col, "Fixture", x - 0.3, x + 0.3, y - 0.6, y + 0.6, 3.17, 3.25, m_steel)
        box(col, "Fixture_Diffuser", x - 0.27, x + 0.27, y - 0.57, y + 0.57, 3.16, 3.17, m_diffuser)
    fx = box(col, "Fixture_Fallen", -0.3, 0.3, -0.6, 0.6, -0.04, 0.04, m_steel)
    box(col, "Fixture_Fallen_Diffuser", -0.27, 0.27, -0.57, 0.57, -0.05, -0.04, m_diffuser).parent = fx
    fx.location = (2.5, 5.5, 2.85)
    fx.rotation_euler = (math.radians(-38), math.radians(6), 0)
    cylinder(col, "Fixture_Wire", (2.5, 6.35, 3.42), (2.5, 6.0, 3.2), 0.005, m_cable, 4)
    # 天井から垂れた切れたケーブル
    for x, y, l in ((-1.2, 6.6, 1.0), (-1.05, 6.7, 0.7), (3.6, 1.5, 0.9)):
        pts = [Vector((x, y, 3.42))]
        for k in range(6):
            pts.append(pts[-1] + Vector((rng.normal(0, 0.04), rng.normal(0, 0.04), -l / 6)))
        for a, b in zip(pts, pts[1:]):
            cylinder(col, "Cable_Hang", a, b, 0.012, m_cable, 6)

    # --- 机 ---------------------------------------------------------------------------
    box(col, "Desk_Top", -4.0, -2.0, 2.5, 3.5, 0.75, 0.8, m_desk, uv_scale=1.0)
    box(col, "Desk_Pedestal", -4.0, -3.55, 2.55, 3.45, 0.0, 0.75, m_steel)
    for z0 in (0.05, 0.3, 0.52):
        box(col, "Desk_Drawer", -3.99, -3.56, 2.535, 2.55, z0, z0 + 0.2, m_dark)
    box(col, "Desk_Panel", -3.55, -2.05, 3.4, 3.45, 0.15, 0.75, m_steel)
    box(col, "Desk_Leg", -2.1, -2.05, 2.55, 3.45, 0.0, 0.75, m_steel)
    # 机の上: 倒れたモニター、キーボード、マグカップ、書類
    mon = box(col, "Desk_Monitor", -0.28, 0.28, -0.02, 0.02, 0.0, 0.34, m_plastic)
    box(col, "Desk_Monitor_Screen", -0.25, 0.25, -0.025, -0.02, 0.02, 0.32, m_screen, uv_scale=0.5).parent = mon
    mon.location = (-3.1, 3.2, 0.8)
    mon.rotation_euler = (math.radians(-72), 0, math.radians(14))
    box(col, "Desk_Keyboard", -2.9, -2.45, 2.62, 2.78, 0.8, 0.82, m_plastic)
    cylinder(col, "Desk_Mug", (-2.3, 3.25, 0.8), (-2.3, 3.25, 0.9), 0.04, m_sign, 10)

    # --- 観測コンソール（外形 X 1.6〜4.0、Y 6.5〜7.3、高さ 1.2） ------------------------------------------
    bm = bmesh.new()
    prof = [(6.5, 0.0), (7.3, 0.0), (7.3, 1.2), (6.85, 1.2), (6.5, 0.92)]
    vs = []
    for x in (1.6, 4.0):
        vs.append([bm.verts.new((x, y, z)) for y, z in prof])
    bm.faces.new(vs[0][::-1])
    bm.faces.new(vs[1])
    for i in range(len(prof)):
        j = (i + 1) % len(prof)
        bm.faces.new((vs[0][i], vs[0][j], vs[1][j], vs[1][i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new("Console")
    bm.to_mesh(me)
    bm.free()
    console = bpy.data.objects.new("Console", me)
    col.objects.link(console)
    me.materials.append(m_steel)
    world_uv(console, 1.0)
    # 斜めの操作盤の上のボタンとスイッチ（ほとんどは消え、数個だけ橙色に点いている）
    slope = math.atan2(0.28, 0.35)
    for i in range(18):
        x = 1.8 + (i % 9) * 0.25
        t = 0.25 + (i // 9) * 0.45
        y = 6.5 + 0.35 * t
        z = 0.92 + 0.28 * t + 0.015
        m = m_amber if i in (3, 11, 16) else (m_red if i == 7 else m_plastic)
        b = box(col, "Console_Button", -0.04, 0.04, -0.03, 0.03, -0.01, 0.01, m)
        b.location = (x, y, z)
        b.rotation_euler = (slope, 0, 0)
    # 奥の割れたモニター 2 台（壁に固定）
    for cx in (2.15, 3.45):
        box(col, "Console_Monitor", cx - 0.5, cx + 0.5, 7.4, 7.5, 1.3, 1.95, m_plastic)
        box(col, "Console_Monitor_Screen", cx - 0.46, cx + 0.46, 7.39, 7.4, 1.33, 1.92, m_screen, uv_scale=1.0)
        box(col, "Console_Monitor_Arm", cx - 0.05, cx + 0.05, 7.5, 7.85, 1.55, 1.65, m_dark)
    # スクリーンの UV を 0..1 に合わせ直す
    for ob in col.objects:
        if ob.name.startswith(("Console_Monitor_Screen", "Desk_Monitor_Screen")):
            _fit_uv(ob)

    # --- 倒れた椅子（西の壁際、通り道の外） ---------------------------------------------------------
    ch = box(col, "Chair_Seat", -0.25, 0.25, -0.25, 0.25, 0.42, 0.48, m_chair)
    box(col, "Chair_Back", -0.23, 0.23, 0.2, 0.25, 0.5, 0.95, m_chair).parent = ch
    cylinder(col, "Chair_Post", (0, 0, 0.1), (0, 0, 0.42), 0.025, m_dark, 8).parent = ch
    for k in range(5):
        a = k * 2 * math.pi / 5
        cylinder(col, "Chair_Leg", (0, 0, 0.08), (0.3 * math.cos(a), 0.3 * math.sin(a), 0.04), 0.018, m_dark, 6).parent = ch
    ch.location = (-4.3, 0.95, 0.25)
    ch.rotation_euler = (math.radians(90), 0, math.radians(30))

    # --- 壁の掲示物、案内板 ---------------------------------------------------------------
    box(col, "Board", -3.6, -1.4, 0.15, 0.18, 1.2, 2.2, m_dark)
    for i in range(6):
        x = -3.45 + (i % 3) * 0.7 + rng.normal(0, 0.05)
        z = 1.75 if i < 3 else 1.3
        p = plane(col, "Board_Paper", x + 0.25, 0.185, z + 0.18, 0.4, 0.3, m_paper,
                  rot=(math.radians(90), 0, math.radians(180) + rng.normal(0, 0.08)))
        _paper_uv(p, i)
    box(col, "Sign", 2.2, 3.4, 7.83, 7.85, 2.45, 2.75, m_sign)
    _text(col, "OBSERVATION  B2-01", (2.8, 7.825, 2.6), 0.11, m_sign_txt)
    # 救急箱（白い箱に赤い十字。光らせない）
    m_cross = material("obs_red_paint", (0.45, 0.04, 0.03), rough=0.6)
    box(col, "FirstAid", -4.85, -4.75, 5.2, 5.7, 1.4, 1.85, m_sign)
    box(col, "FirstAid_Cross", -4.75, -4.745, 5.41, 5.49, 1.52, 1.73, m_cross)
    box(col, "FirstAid_Cross", -4.75, -4.745, 5.345, 5.555, 1.585, 1.665, m_cross)

    # --- 床の書類、爪痕、水たまり ----------------------------------------------------------------
    for i in range(32):
        # 机のまわりと、出入口へ向かって吹き散らされたように
        if i < 18:
            x, y = rng.normal(-2.6, 1.0), rng.normal(2.6, 1.0)
        else:
            x, y = rng.normal(-0.6, 1.2), rng.normal(5.2, 1.2)
        x, y = float(np.clip(x, -4.7, 4.7)), float(np.clip(y, 0.3, 7.6))
        if -4.05 < x < -1.95 and 2.45 < y < 3.55:
            continue
        p = plane(col, "Floor_Paper", x, y, 0.008 + i * 0.0002, 0.21, 0.297, m_paper,
                  rot=(rng.normal(0, 0.01), rng.normal(0, 0.01), rng.random() * math.tau))
        _paper_uv(p, i)
    # 爪痕: 東の壁、机の側面、南の壁の掲示板の横
    plane(col, "Claw_E", 4.845, 3.1, 1.45, 0.9, 1.1, m_claw, rot=(math.radians(90), 0, math.radians(-90)))
    plane(col, "Claw_E2", 4.845, 4.4, 0.85, 0.6, 0.8, m_claw, rot=(math.radians(90), math.radians(20), math.radians(-90)))
    plane(col, "Claw_S", -0.6, 0.155, 1.3, 0.8, 1.0, m_claw, rot=(math.radians(90), math.radians(-15), 0))
    plane(col, "Claw_Floor", 0.2, 6.2, 0.006, 0.7, 0.9, m_claw, rot=(0, 0, math.radians(25)))
    # 出入口の内側の水たまり（天井の配管から漏れている）
    plane(col, "Puddle", -0.5, 6.9, 0.004, 2.2, 1.6, m_puddle, rot=(0, 0, math.radians(8)))
    plane(col, "Puddle_Small", -3.9, 6.6, 0.004, 0.9, 0.7, m_puddle, rot=(0, 0, math.radians(-30)))

    _parent_clear(col)
    join_all(col, "Room_" + ROOM)
    return col


def _fit_uv(ob):
    """前を向いた面の UV を 0..1 に広げる（モニターの画面用）。"""
    me = ob.data
    uv = me.uv_layers.active.data
    us = [uv[i].uv.x for p in me.polygons for i in p.loop_indices]
    vs = [uv[i].uv.y for p in me.polygons for i in p.loop_indices]
    u0, u1, v0, v1 = min(us), max(us), min(vs), max(vs)
    for p in me.polygons:
        for i in p.loop_indices:
            uv[i].uv = ((uv[i].uv.x - u0) / max(u1 - u0, 1e-6), (uv[i].uv.y - v0) / max(v1 - v0, 1e-6))


def _paper_uv(ob, i):
    """書類の画像（2×2）のどれか1枚を使う。"""
    qx, qy = (i % 2) * 0.5, ((i // 2) % 2) * 0.5
    uv = ob.data.uv_layers.active.data
    for l in uv:
        l.uv = (qx + l.uv.x * 0.5, qy + l.uv.y * 0.5)


def _text(col, s, loc, size, mat):
    cu = bpy.data.curves.new("SignText", "FONT")
    cu.body = s
    cu.size = size
    cu.align_x = "CENTER"
    cu.align_y = "CENTER"
    cu.extrude = 0.002
    ob = bpy.data.objects.new("SignText", cu)
    col.objects.link(ob)
    ob.location = loc
    ob.rotation_euler = (math.radians(90), 0, 0)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    mo = bpy.data.objects.new("Sign_Text", me)
    col.objects.link(mo)
    mo.matrix_world = ob.matrix_world
    me.materials.clear()
    me.materials.append(mat)
    bpy.data.objects.remove(ob, do_unlink=True)
    return mo


def _parent_clear(col):
    bpy.context.view_layer.update()
    for ob in col.objects:
        if ob.parent is not None:
            mw = ob.matrix_world.copy()
            ob.parent = None
            ob.matrix_world = mw
    bake_transforms(col)


def export():
    export_glb(bpy.data.collections["Room_" + ROOM], os.path.abspath(OUT))
    print("書き出し:", os.path.abspath(OUT))
