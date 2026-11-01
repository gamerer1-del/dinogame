"""エレベーターホールの見た目（整備区画のいちばん奥）。

場所は scripts/level.gd の MAZE の 19〜21行目・1〜3列目（Blender 座標で X -13.75〜-6.25、Y 101.5〜109）。
南の壁の真ん中（X -11.25〜-8.75）が整備通路からの入口、北の壁の真ん中にエレベーターの扉。
"""
import os

import bpy

import textures as tx
from common import H, T, box, collection, cylinder, export_glb, finish, floor, material, plane, text, wall_x, wall_y

ROOM = "exit"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "assets", "models", "rooms",
                   ROOM + ".glb")

X0, X1, Y0, Y1 = -13.75, -6.25, 101.5, 109.0
CX = (X0 + X1) / 2
DOOR = (-11.25, -8.75)        # 南の入口


def build():
    col = collection("Room_" + ROOM)
    m_panel = tx.metal_panel("exit_panel", seed=13, tint=(0.40, 0.42, 0.43), dirt=0.4)
    m_floor = tx.lab_floor("exit_floor", seed=33, wet=0.3)
    m_hazard = tx.hazard("exit_hazard", seed=83)
    m_claw = tx.claw_marks("exit_claw", seed=64)
    m_steel = material("exit_steel", (0.6, 0.61, 0.62), rough=0.22, metal=1.0)
    m_dark = material("exit_dark_metal", (0.07, 0.07, 0.075), rough=0.5, metal=0.7)
    m_white = material("exit_light", (0.8, 0.82, 0.85), rough=0.3, emission=(0.9, 0.95, 1.0), emit_strength=1.5)
    m_green = material("exit_green", (0.05, 0.5, 0.15), rough=0.3, emission=(0.1, 1.0, 0.3), emit_strength=4.0)
    m_amber = material("exit_amber", (0.5, 0.3, 0.02), rough=0.3, emission=(1.0, 0.55, 0.1), emit_strength=3.0)
    m_txt = material("exit_text_dark", (0.02, 0.03, 0.02), rough=0.5)

    floor(col, "Floor", X0, X1, Y0, Y1, m_floor)
    wall_y(col, "Wall_W", X0, Y0, Y1, m_panel)
    wall_y(col, "Wall_E", X1, Y0, Y1, m_panel)
    wall_x(col, "Wall_N", Y1, X0, X1, m_panel)
    wall_x(col, "Wall_S", Y0, X0, DOOR[0], m_panel)
    wall_x(col, "Wall_S", Y0, DOOR[1], X1, m_panel)
    i0, i1 = Y0 + T / 2, Y1 - T / 2
    for x0, x1, y0, y1 in ((X0 + 0.15, X0 + 0.17, i0, i1), (X1 - 0.17, X1 - 0.15, i0, i1),
                           (X0 + 0.15, X1 - 0.15, i1 - 0.02, i1)):
        box(col, "Kick", x0, x1, y0, y1, 0, 0.15, m_dark)
    for x0, x1 in ((DOOR[0] - 0.12, DOOR[0]), (DOOR[1], DOOR[1] + 0.12)):
        box(col, "Door_Frame", x0, x1, i0, i0 + 0.025, 0, 3.0, m_hazard, uv_scale=1.0)

    # エレベーターの扉（左右2枚）と枠、床の乗り場
    yd = i1
    box(col, "Elevator_Door_L", CX - 1.0, CX - 0.005, yd - 0.1, yd, 0.0, 3.0, m_steel, uv_scale=1.0)
    box(col, "Elevator_Door_R", CX + 0.005, CX + 1.0, yd - 0.1, yd, 0.0, 3.0, m_steel, uv_scale=1.0)
    for x0, x1 in ((CX - 1.2, CX - 1.0), (CX + 1.0, CX + 1.2)):
        box(col, "Elevator_Jamb", x0, x1, yd - 0.15, yd, 0.0, 3.2, m_dark)
    box(col, "Elevator_Head", CX - 1.2, CX + 1.2, yd - 0.15, yd, 3.0, 3.2, m_dark)
    box(col, "Elevator_Sill", CX - 1.0, CX + 1.0, yd - 0.3, yd, 0.0, 0.01, m_steel)
    plane(col, "Floor_Hazard", CX, yd - 0.65, 0.004, 2.4, 0.6, m_hazard)
    # 階数表示と呼びボタン（ゲーム側の呼び出しボタンは CX + 1.4 の位置）
    box(col, "Indicator", CX - 0.35, CX + 0.35, yd - 0.17, yd - 0.15, 3.25, 3.4, m_dark)
    text(col, "B5", (CX, yd - 0.175, 3.325), 0.1, m_amber)
    box(col, "Call_Panel", CX + 1.3, CX + 1.5, yd - 0.03, yd, 1.1, 1.5, m_steel)
    # 非常口のサイン（入口の上、ホールの内側を向く）
    box(col, "Exit_Sign", CX - 0.5 - 1.25, CX + 0.5 - 1.25, i0, i0 + 0.05, 2.9, 3.15, m_green)
    text(col, "EXIT", (CX - 1.25, i0 + 0.055, 3.025), 0.14, m_txt, rot=(1.5708, 0, 3.14159))

    # 天井の照明パネル（電源が戻るとゲーム側の白い光が点く）
    for y in (Y0 + 2.0, (Y0 + Y1) / 2, Y1 - 2.0):
        box(col, "Light_Panel", CX - 0.8, CX + 0.8, y - 0.25, y + 0.25, 3.4, 3.45, m_steel)
        box(col, "Light_Diffuser", CX - 0.75, CX + 0.75, y - 0.2, y + 0.2, 3.39, 3.4, m_white)
    # ここまで追ってきた爪痕
    plane(col, "Claw", X0 + 0.155, Y0 + 2.0, 1.2, 0.8, 1.0, m_claw, rot=(1.5708, 0, 1.5708))
    plane(col, "Claw", X1 - 0.155, Y1 - 2.5, 1.5, 0.8, 1.0, m_claw, rot=(1.5708, 0, -1.5708))

    finish(col, "Room_" + ROOM)
    return col


def export():
    export_glb(bpy.data.collections["Room_" + ROOM], os.path.abspath(OUT))
    print("書き出し:", os.path.abspath(OUT))
