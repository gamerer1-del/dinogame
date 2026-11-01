"""恐竜（ストーカー）に骨と歩きのアニメーションを付けて assets/models/stalker.glb に書き出す。

体の形は Meshy で作った src/dino_meshy.glb（コミットしない）。足元が原点、頭が +Y 向きに直してから、
骨の位置は体の形に合わせて手で決め、重みは「骨までの距離」で計算する（自動の重みは生成メッシュだと失敗しやすい）。
歩きは名前 "walk" の1秒のループ。ゲームが自動で再生する。
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
CYCLE = 24        # 1歩きサイクル = 1秒

# 骨: 名前, 親, 根元, 先端（足元原点、+Y が前、単位 m）。L/R は x の符号で左右に作る
CENTER = [
    ("pelvis", None, (0, -0.15, 0.95), (0, 0.0, 0.97)),
    ("chest", "pelvis", (0, 0.0, 0.97), (0, 0.15, 1.0)),
    ("neck1", "chest", (0, 0.15, 1.0), (0, 0.24, 1.22)),
    ("neck2", "neck1", (0, 0.24, 1.22), (0, 0.34, 1.37)),
    ("head", "neck2", (0, 0.34, 1.37), (0, 0.73, 1.33)),
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
    _walk(arm)
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


def _walk(arm):
    """1秒の歩き。脚を交互に振り、体を上下させ、尾と頭でバランスを取る。"""
    act = bpy.data.actions.get("walk")
    if act:
        bpy.data.actions.remove(act)
    act = bpy.data.actions.new("walk")
    act.use_fake_user = True
    arm.animation_data_create()
    arm.animation_data.action = act
    pb = arm.pose.bones
    for b in pb:
        b.rotation_mode = "XYZ"
    for f in range(0, CYCLE + 1, 2):
        ph = f / CYCLE * math.tau
        for tag, off in (("L", 0.0), ("R", math.pi)):
            p = ph + off
            swing = math.sin(p)            # +: 前へ
            lift = max(0.0, math.cos(p))   # 前へ振る間だけ足を上げる
            pb["thigh." + tag].rotation_euler = (-0.42 * swing - 0.15 * lift, 0, 0)
            pb["shin." + tag].rotation_euler = (0.55 * lift, 0, 0)
            pb["meta." + tag].rotation_euler = (-0.45 * lift + 0.2 * swing, 0, 0)
            pb["toe." + tag].rotation_euler = (0.25 * lift - 0.15 * max(0.0, -swing), 0, 0)
            pb["arm." + tag].rotation_euler = (0.12 * swing, 0, 0)
        pb["pelvis"].location = (0, 0, -0.03 * abs(math.cos(ph)))  # 一歩ごとに少し沈む（ローカル Z ≒ 上）
        pb["pelvis"].rotation_euler = (0, 0.05 * math.sin(ph), 0)
        pb["chest"].rotation_euler = (0.03 * math.cos(2 * ph), -0.06 * math.sin(ph), 0)
        pb["neck1"].rotation_euler = (-0.04 * math.cos(2 * ph), 0.04 * math.sin(ph), 0)
        pb["head"].rotation_euler = (0.05 * math.cos(2 * ph), 0.05 * math.sin(ph), 0)
        for i, t in enumerate(("tail1", "tail2", "tail3", "tail4")):
            pb[t].rotation_euler = (0.03 * math.cos(2 * ph - i * 0.6), 0.08 * math.sin(ph - i * 0.7), 0)
        for b in pb:
            b.keyframe_insert("rotation_euler", frame=f)
            b.keyframe_insert("location", frame=f)
    bpy.context.scene.render.fps = FPS


def export():
    arm = bpy.data.objects["DinoRig"]
    body = bpy.data.objects["DinoBody"]
    arm.animation_data.action = bpy.data.actions["walk"]
    for o in bpy.context.view_layer.objects:
        o.select_set(o in (arm, body))
    bpy.context.view_layer.objects.active = arm
    bpy.ops.export_scene.gltf(filepath=os.path.abspath(OUT), export_format="GLB", use_selection=True,
                              export_yup=True, export_animations=True, export_animation_mode="ACTIONS",
                              export_image_format="WEBP", export_lights=False, export_cameras=False)
    print("書き出し:", os.path.abspath(OUT))
