"""恐竜（ストーカー）に骨とアニメーションを付けて assets/models/stalker.glb に書き出す。

体の形は Meshy で作った src/dino_meshy.glb（コミットしない）。足元が原点、頭が +Y 向きに直してから、
骨の位置は体の形に合わせて手で決め、重みは「骨までの距離」で計算する（自動の重みは生成メッシュだと失敗しやすい）。
アニメーション（stalker.gd が状態に合わせて切り替える）:
  idle 待機 / walk 歩き（1秒で約1.2m）/ run 走り（0.5秒で約2.4m）/ look 見回し / roar 威嚇 / attack 噛みつき
"""
import math
import os

import bpy
import numpy as np
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "src", "dino_meshy.glb")
OUT = os.path.join(HERE, "..", "..", "assets", "models", "stalker.glb")
SCALE = 1.1       # 生成された体（全長 1.9m）を全長 2.1m、頭の高さ 1.5m に
FPS = 24
JAW_Y = 0.46      # 口の付け根。これより前で JAW_Z より下の頂点が下あご
JAW_Z = 1.315

# 骨: 名前, 親, 根元, 先端（足元原点、+Y が前、単位 m）。L/R は x の符号で左右に作る
CENTER = [
    ("pelvis", None, (0, -0.15, 0.95), (0, 0.0, 0.97)),
    ("chest", "pelvis", (0, 0.0, 0.97), (0, 0.15, 1.0)),
    ("neck1", "chest", (0, 0.15, 1.0), (0, 0.24, 1.22)),
    ("neck2", "neck1", (0, 0.24, 1.22), (0, 0.34, 1.37)),
    ("head", "neck2", (0, 0.34, 1.37), (0, 0.73, 1.33)),
    ("jaw", "head", (0, JAW_Y, 1.31), (0, 0.74, 1.29)),
    ("tail1", "pelvis", (0, -0.15, 0.95), (0, -0.45, 0.86)),
    ("tail2", "tail1", (0, -0.45, 0.86), (0, -0.78, 0.62)),
    ("tail3", "tail2", (0, -0.78, 0.62), (0, -1.08, 0.34)),
    ("tail4", "tail3", (0, -1.08, 0.34), (0, -1.36, 0.06)),
]
SIDE = [
    ("thigh", "pelvis", (0.12, -0.12, 0.88), (0.16, 0.0, 0.52)),
    ("shin", "thigh", (0.16, 0.0, 0.52), (0.09, -0.24, 0.28)),
    ("meta", "shin", (0.09, -0.24, 0.28), (0.12, -0.02, 0.05)),
    ("toe", "meta", (0.12, -0.02, 0.05), (0.18, 0.2, 0.02)),
    ("arm", "chest", (0.1, 0.18, 0.95), (0.15, 0.26, 0.8)),
    ("forearm", "arm", (0.15, 0.26, 0.8), (0.15, 0.4, 0.86)),
]


def build():
    col = bpy.data.collections.get("Dino") or bpy.data.collections.new("Dino")
    if col.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(col)
    for o in list(col.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=SRC)
    body = next(o for o in bpy.data.objects if o not in before and o.type == "MESH")
    for o in [o for o in bpy.data.objects if o not in before]:
        for c in list(o.users_collection):
            c.objects.unlink(o)
        col.objects.link(o)
    body.name = "DinoBody"
    _normalize(body)

    arm = _armature(col)
    _weights(body, arm)
    body.parent = arm
    mod = body.modifiers.new("Armature", "ARMATURE")
    mod.object = arm
    for m in body.data.materials:
        m.use_backface_culling = False   # 口を開けたときに頭の内側が抜けて見えないように
    _animations(arm)
    return arm, body


def _normalize(body):
    """頭を +Y、全長を合わせ、足の真下を原点、足の裏を高さ 0 にする。"""
    me = body.data
    me.transform(Matrix.Rotation(math.pi, 4, "Z") @ Matrix.Scale(SCALE, 4))
    co = np.array([v.co[:] for v in me.vertices])
    zmin = co[:, 2].min()
    feet = co[co[:, 2] < zmin + 0.05]
    me.transform(Matrix.Translation((0.0, -feet[:, 1].mean(), -zmin)))
    body.matrix_world = Matrix.Identity(4)


def _bones():
    out = list(CENTER)
    for name, parent, a, b in SIDE:
        for s, tag in ((1, "L"), (-1, "R")):
            p = parent if parent in ("pelvis", "chest") else parent + "." + tag
            out.append((name + "." + tag, p, (a[0] * s, a[1], a[2]), (b[0] * s, b[1], b[2])))
    return out


def _armature(col):
    ad = bpy.data.armatures.new("DinoRig")
    arm = bpy.data.objects.new("DinoRig", ad)
    col.objects.link(arm)
    bpy.context.view_layer.objects.active = arm
    for o in bpy.context.view_layer.objects:
        o.select_set(o == arm)
    bpy.ops.object.mode_set(mode="EDIT")
    for name, parent, a, b in _bones():
        eb = ad.edit_bones.new(name)
        eb.head, eb.tail = Vector(a), Vector(b)
        # ロールを揃えて、どの骨もローカル X 軸 ≒ ワールド X 軸（前後に振る回転が X 回りになる）
        d = (eb.tail - eb.head).normalized()
        z = Vector((1, 0, 0)).cross(d)
        if z.length > 1e-4:
            eb.align_roll(z.normalized())
        if parent:
            eb.parent = ad.edit_bones[parent]
            eb.use_connect = (eb.parent.tail - eb.head).length < 1e-4
    bpy.ops.object.mode_set(mode="OBJECT")
    return arm


def _seg_dist(p, a, b):
    ab = b - a
    t = np.clip(((p - a) @ ab) / (ab @ ab), 0, 1)
    return np.linalg.norm(p - (a + t[:, None] * ab), axis=1)


def _weights(body, arm):
    """各頂点を近い骨（上位2本）に、距離の4乗に反比例して割り当てる。手足は同じ側の頂点だけ。"""
    co = np.array([v.co[:] for v in body.data.vertices])
    names, dists = [], []
    for name, _p, a, b in _bones():
        d = _seg_dist(co, np.array(a, float), np.array(b, float))
        if name.endswith(".L"):
            d = np.where(co[:, 0] > -0.02, d, 1e3)
        elif name.endswith(".R"):
            d = np.where(co[:, 0] < 0.02, d, 1e3)
        if name.startswith(("arm", "forearm")):
            d = np.where(co[:, 1] > 0.08, d, 1e3)   # 腕は胸より前の頂点だけ
        if name == "jaw":
            # 下あごは位置で決める。口の付け根の 6cm はあごと頭で混ぜる
            lower = (co[:, 1] > JAW_Y) & (co[:, 2] < JAW_Z) & (co[:, 2] > 1.2)
            ramp = np.clip((co[:, 1] - JAW_Y) / 0.06, 0, 1)
            d = np.where(lower, 0.004 + 0.03 * (1 - ramp), 1e3)
        names.append(name)
        dists.append(d)
    D = np.stack(dists, axis=1)
    order = np.argsort(D, axis=1)[:, :2]
    groups = {n: body.vertex_groups.new(name=n) for n in names}
    for i in range(len(co)):
        ids = order[i]
        w = 1.0 / (D[i, ids] ** 4 + 1e-8)
        w /= w.sum()
        for j, wj in zip(ids, w):
            if wj > 0.02:
                groups[names[j]].add([i], float(wj), "REPLACE")


# --- アニメーション ------------------------------------------------------------------
# 骨のローカル X 回り = 前後（＋で先端が上・前へ）、ローカル Z 回り = 左右。ローカル Y 回りはねじれなので使わない。

LEGS = ("thigh", "shin", "meta", "toe")


def _new_action(arm, name):
    act = bpy.data.actions.get(name)
    if act:
        bpy.data.actions.remove(act)
    act = bpy.data.actions.new(name)
    act.use_fake_user = True
    arm.animation_data.action = act
    for b in arm.pose.bones:
        b.rotation_mode = "XYZ"
        b.rotation_euler = (0, 0, 0)
        b.location = (0, 0, 0)
    return act


def _key(arm, f):
    for b in arm.pose.bones:
        b.keyframe_insert("rotation_euler", frame=f)
        b.keyframe_insert("location", frame=f)


def _r(pb, name, x=0.0, z=0.0):
    pb[name].rotation_euler = (x, 0.0, z)


def _gait(arm, name, frames, thigh, lift_k, bob, lean, neck, tail_up, sway):
    """歩き・走りの共通部分。thigh: 脚の振り幅、lift_k: 足の上げ方、lean: 体の前傾。"""
    _new_action(arm, name)
    pb = arm.pose.bones
    for f in range(0, frames + 1):
        ph = f / frames * math.tau
        for tag, off in (("L", 0.0), ("R", math.pi)):
            p = ph + off
            swing = math.sin(p)              # +: 脚が前にある
            lift = max(0.0, math.cos(p))     # 脚が前へ動いている間だけ足を上げる
            _r(pb, "thigh." + tag, thigh * swing + 0.25 * lift_k * lift)
            _r(pb, "shin." + tag, -0.9 * lift_k * lift)
            _r(pb, "meta." + tag, 0.7 * lift_k * lift - 0.25 * thigh * swing)
            _r(pb, "toe." + tag, -0.6 * lift_k * lift + 0.3 * max(0.0, -swing))
            _r(pb, "arm." + tag, -0.25 * lean + 0.1 * swing)
            _r(pb, "forearm." + tag, 0.35 * lean)
        pb["pelvis"].location = (0, 0, -bob * (1 - abs(math.sin(ph))))
        _r(pb, "pelvis", -lean, 0.06 * math.sin(ph))
        _r(pb, "chest", 0.02 * math.cos(2 * ph), -0.08 * math.sin(ph))
        _r(pb, "neck1", -neck + 0.03 * math.cos(2 * ph), 0.04 * math.sin(ph))
        _r(pb, "neck2", -0.5 * neck, 0.0)
        _r(pb, "head", 1.2 * neck + lean - 0.04 * math.cos(2 * ph), 0.06 * math.sin(ph))
        for i, t in enumerate(("tail1", "tail2", "tail3", "tail4")):
            _r(pb, t, tail_up + 0.04 * math.cos(2 * ph - i * 0.7), sway * math.sin(ph - i * 0.8))
        _key(arm, f)


def _idle(arm):
    """2秒の待機。呼吸で胸がふくらみ、頭が小さく動き、尾がゆっくり揺れる。"""
    _new_action(arm, "idle")
    pb = arm.pose.bones
    n = 48
    for f in range(0, n + 1, 2):
        ph = f / n * math.tau
        _r(pb, "pelvis", 0.02 * math.sin(ph))
        _r(pb, "chest", 0.03 * math.sin(ph))
        _r(pb, "neck1", -0.03 * math.sin(ph))
        _r(pb, "head", 0.04 * math.sin(ph + 0.6), 0.12 * math.sin(ph) * (1.0 if f < 30 else 0.4))
        for tag in ("L", "R"):
            _r(pb, "thigh." + tag, 0.05)
            _r(pb, "shin." + tag, -0.08)
            _r(pb, "meta." + tag, 0.05)
            _r(pb, "arm." + tag, -0.05 + 0.05 * math.sin(ph))
            _r(pb, "forearm." + tag, 0.15 + 0.08 * math.sin(ph + 1))
        for i, t in enumerate(("tail1", "tail2", "tail3", "tail4")):
            _r(pb, t, 0.03 * math.sin(ph - i), 0.07 * math.sin(ph * 0.5 * 2 - i * 0.6))
        _r(pb, "jaw", -0.03 * max(0.0, math.sin(ph * 2)))
        _key(arm, f)


def _look(arm):
    """3秒の見回し。首を左右に振り、鼻先を下げてにおいを嗅ぐ。"""
    _new_action(arm, "look")
    pb = arm.pose.bones
    n = 72
    turns = [(0, 0.0), (12, 0.7), (26, 0.7), (40, -0.7), (54, -0.7), (66, 0.0), (72, 0.0)]
    for f in range(0, n + 1, 2):
        yaw = float(np.interp(f, [a for a, _ in turns], [b for _, b in turns]))
        sniff = 0.08 * math.sin(f / n * math.tau * 6) * (1.0 if 26 <= f <= 40 or 54 <= f <= 66 else 0.0)
        _r(pb, "pelvis", -0.08, -0.1 * yaw)
        _r(pb, "chest", -0.05, 0.3 * yaw)
        _r(pb, "neck1", -0.25, 0.4 * yaw)
        _r(pb, "neck2", -0.1, 0.4 * yaw)
        _r(pb, "head", 0.2 + sniff, 0.5 * yaw)
        for tag in ("L", "R"):
            _r(pb, "thigh." + tag, 0.1)
            _r(pb, "shin." + tag, -0.2)
            _r(pb, "meta." + tag, 0.12)
            _r(pb, "forearm." + tag, 0.3)
        for i, t in enumerate(("tail1", "tail2", "tail3", "tail4")):
            _r(pb, t, 0.05, -0.25 * yaw * (i + 1) / 4)
        _r(pb, "jaw", -0.04 * abs(sniff) / 0.08)
        _key(arm, f)


def _roar(arm):
    """1.5秒の威嚇（1回だけ）。首を反らして口を大きく開け、頭を震わせる。"""
    _new_action(arm, "roar")
    pb = arm.pose.bones
    n = 36
    up = [(0, 0.0), (8, 1.0), (28, 1.0), (36, 0.0)]
    for f in range(0, n + 1):
        u = float(np.interp(f, [a for a, _ in up], [b for _, b in up]))
        shake = 0.06 * math.sin(f * 2.2) * (1.0 if 8 <= f <= 28 else 0.0)
        _r(pb, "pelvis", 0.06 * u)
        _r(pb, "chest", 0.12 * u)
        _r(pb, "neck1", 0.25 * u)
        _r(pb, "neck2", 0.15 * u)
        _r(pb, "head", 0.3 * u + shake, shake)
        _r(pb, "jaw", -0.45 * u)
        for tag, s in (("L", 1), ("R", -1)):
            _r(pb, "thigh." + tag, 0.12 * u)
            _r(pb, "shin." + tag, -0.25 * u)
            _r(pb, "meta." + tag, 0.15 * u)
            _r(pb, "arm." + tag, 0.35 * u, 0.2 * s * u)
            _r(pb, "forearm." + tag, 0.4 * u)
        for i, t in enumerate(("tail1", "tail2", "tail3", "tail4")):
            _r(pb, t, 0.12 * u, 0.05 * math.sin(f * 0.8 - i))
        _key(arm, f)


def _attack(arm):
    """0.75秒の噛みつき（1回だけ）。身を引いてから首を突き出し、口を閉じる。"""
    _new_action(arm, "attack")
    pb = arm.pose.bones
    keys = [  # フレーム, 引き(-)/突き(+), 口
        (0, 0.0, 0.0), (5, -1.0, 0.6), (9, 1.0, 1.0), (11, 1.0, 0.0), (18, 0.0, 0.0)]
    for f in range(0, 19):
        k = float(np.interp(f, [a for a, _, _ in keys], [b for _, b, _ in keys]))
        j = float(np.interp(f, [a for a, _, _ in keys], [c for _, _, c in keys]))
        pb["pelvis"].location = (0, 0.12 * k, -0.04 * abs(k))
        _r(pb, "pelvis", -0.15 * max(0.0, k))
        _r(pb, "chest", -0.1 * k)
        _r(pb, "neck1", -0.45 * k)
        _r(pb, "neck2", -0.2 * k)
        _r(pb, "head", 0.35 * k)
        _r(pb, "jaw", -0.55 * j)
        for tag in ("L", "R"):
            _r(pb, "thigh." + tag, 0.15 + 0.1 * k)
            _r(pb, "shin." + tag, -0.3)
            _r(pb, "meta." + tag, 0.2)
            _r(pb, "arm." + tag, 0.5 * max(0.0, k))
            _r(pb, "forearm." + tag, 0.5)
        for i, t in enumerate(("tail1", "tail2", "tail3", "tail4")):
            _r(pb, t, 0.1 * k)
        _key(arm, f)


def _animations(arm):
    arm.animation_data_create()
    _gait(arm, "walk", 24, thigh=0.38, lift_k=0.6, bob=0.025, lean=0.0, neck=0.0, tail_up=0.0, sway=0.1)
    _gait(arm, "run", 12, thigh=0.7, lift_k=1.0, bob=0.06, lean=0.25, neck=0.3, tail_up=0.15, sway=0.05)
    _idle(arm)
    _look(arm)
    _roar(arm)
    _attack(arm)
    arm.animation_data.action = bpy.data.actions["idle"]
    bpy.context.scene.render.fps = FPS


def export():
    arm = bpy.data.objects["DinoRig"]
    body = bpy.data.objects["DinoBody"]
    for o in (arm, body):
        o.hide_set(False)
        o.hide_viewport = False
    arm.animation_data.action = bpy.data.actions["idle"]
    for o in bpy.context.view_layer.objects:
        o.select_set(o in (arm, body))
    bpy.context.view_layer.objects.active = arm
    bpy.ops.export_scene.gltf(filepath=os.path.abspath(OUT), export_format="GLB", use_selection=True,
                              export_yup=True, export_animations=True, export_animation_mode="ACTIONS",
                              export_image_format="WEBP", export_lights=False, export_cameras=False)
    print("書き出し:", os.path.abspath(OUT))
