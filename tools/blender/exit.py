"""出口（エレベーターホール）の見た目。

寸法は docs/blender-guide.md の「出口」どおり。ここだけ電源が生きていて白い照明が明るい。
エレベーターの扉は中心 (0, 59.8)、幅2×高さ3。
"""
import os

import bpy

import textures as tx
from common import H, box, collection, cylinder, export_glb, finish, floor, material, plane, text, wall_x, wall_y

ROOM = "exit"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "assets", "models", "rooms",
                   ROOM + ".glb")


def build():
    col = collection("Room_" + ROOM)
    m_panel = tx.metal_panel("exit_panel", seed=13, tint=(0.40, 0.42, 0.43), dirt=0.4)
    m_floor = tx.lab_floor("exit_floor", seed=33, wet=0.3)
    m_hazard = tx.hazard("exit_hazard", seed=83)
    m_claw = tx.claw_marks("exit_claw", seed=64)
    m_steel = material("exit_steel", (0.6, 0.61, 0.62), rough=0.22, metal=1.0)
    m_dark = material("exit_dark_metal", (0.07, 0.07, 0.075), rough=0.5, metal=0.7)
    m_white = material("exit_light", (0.9, 0.95, 1.0), rough=0.3, emission=(0.9, 0.95, 1.0), emit_strength=8.0)
    m_green = material("exit_green", (0.05, 0.5, 0.15), rough=0.3, emission=(0.1, 1.0, 0.3), emit_strength=4.0)
    m_amber = material("exit_amber", (0.5, 0.3, 0.02), rough=0.3, emission=(1.0, 0.55, 0.1), emit_strength=3.0)
    m_txt = material("exit_text_dark", (0.02, 0.03, 0.02), rough=0.5)

    floor(col, "Floor", -3, 3, 54, 60, m_floor)
    wall_y(col, "Wall_W", -3, 54, 60, m_panel)
    wall_y(col, "Wall_E", 3, 54, 60, m_panel)
    wall_x(col, "Wall_N", 60, -3, 3, m_panel)
    for x0, x1, y0, y1 in ((-2.85, -2.83, 54.15, 59.85), (2.83, 2.85, 54.15, 59.85)):
        box(col, "Kick", x0, x1, y0, y1, 0, 0.15, m_dark)

    # エレベーターの扉（左右2枚）と枠、床の乗り場
    box(col, "Elevator_Door_L", -1.0, -0.005, 59.75, 59.85, 0.0, 3.0, m_steel, uv_scale=1.0)
    box(col, "Elevator_Door_R", 0.005, 1.0, 59.75, 59.85, 0.0, 3.0, m_steel, uv_scale=1.0)
    for x0, x1 in ((-1.2, -1.0), (1.0, 1.2)):
        box(col, "Elevator_Jamb", x0, x1, 59.7, 59.85, 0.0, 3.2, m_dark)
    box(col, "Elevator_Head", -1.2, 1.2, 59.7, 59.85, 3.0, 3.2, m_dark)
    box(col, "Elevator_Sill", -1.0, 1.0, 59.55, 59.85, 0.0, 0.01, m_steel)
    plane(col, "Floor_Hazard", 0.0, 59.2, 0.004, 2.4, 0.6, m_hazard)
    # 階数表示と呼びボタン（点いている）
    box(col, "Indicator", -0.35, 0.35, 59.68, 59.7, 3.25, 3.4, m_dark)
    text(col, "B2", (0.0, 59.675, 3.325), 0.1, m_amber)
    box(col, "Call_Panel", 1.4, 1.6, 59.82, 59.85, 1.1, 1.5, m_steel)
    cylinder(col, "Call_Button", (1.5, 59.82, 1.35), (1.5, 59.8, 1.35), 0.035, m_green, 12)
    cylinder(col, "Call_Button", (1.5, 59.82, 1.22), (1.5, 59.8, 1.22), 0.035, m_dark, 12)
    # 非常口のサイン
    box(col, "Exit_Sign", -0.5, 0.5, 54.15, 54.2, 2.9, 3.15, m_green)
    text(col, "EXIT", (0.0, 54.205, 3.025), 0.14, m_txt, rot=(1.5708, 0, 3.14159))

    # 明るい白い照明（ゲームの白い光 (0, 57)）
    for y in (55.5, 57.0, 58.5):
        box(col, "Light_Panel", -0.8, 0.8, y - 0.25, y + 0.25, 3.4, 3.45, m_steel)
        box(col, "Light_Diffuser", -0.75, 0.75, y - 0.2, y + 0.2, 3.39, 3.4, m_white)
    # ここまで追ってきた爪痕
    plane(col, "Claw", -2.845, 55.0, 1.2, 0.8, 1.0, m_claw, rot=(1.5708, 0, 1.5708))

    finish(col, "Room_" + ROOM)
    return col


def export():
    export_glb(bpy.data.collections["Room_" + ROOM], os.path.abspath(OUT))
    print("書き出し:", os.path.abspath(OUT))
