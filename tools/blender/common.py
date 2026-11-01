"""Blender で部屋の見た目を作るための共通部品。

Blender の Python から読み込んで使う（tools/blender/README.md 参照）。
テクスチャは numpy で作るので、外部の素材をダウンロードしなくても再現できる。
座標は docs/blender-guide.md の Blender 座標（1単位 = 1m、Z が上、床の上面が 0）。
"""
import math
import os

import bmesh
import bpy
import numpy as np

H = 3.5      # 天井の高さ
T = 0.3      # 壁の厚さ
TEX = 1024   # テクスチャの一辺

TEX_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "textures")


# --- ノイズ ------------------------------------------------------------------------

def noise(n, beta=2.0, seed=0, ny=None):
    """FFT でつくるタイル状に繋がるノイズ（0..1）。beta が大きいほど大きな模様になる。"""
    ny = ny or n
    rng = np.random.default_rng(seed)
    w = rng.standard_normal((ny, n))
    fy = np.fft.fftfreq(ny)[:, None]
    fx = np.fft.fftfreq(n)[None, :]
    f = np.sqrt(fx * fx + fy * fy)
    f[0, 0] = 1.0
    spec = np.fft.fft2(w) / f ** (beta / 2.0)
    spec[0, 0] = 0
    r = np.real(np.fft.ifft2(spec))
    r -= r.min()
    return r / max(r.max(), 1e-9)


def streaks(n, seed=0, density=0.5, ny=None):
    """縦に流れる筋（結露や錆の垂れ）。上から下へ伸びる値 0..1。"""
    ny = ny or n
    rng = np.random.default_rng(seed)
    base = noise(n, 1.2, seed, 8)            # 横方向だけ変化
    cols = np.repeat(base[:1], ny, axis=0)   # 縦に伸ばす
    fine = noise(n, 0.6, seed + 1, ny)
    s = np.clip((cols - (1.0 - density)) / density, 0, 1)
    s = s * (0.6 + 0.4 * fine)
    return s


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def lines_mask(n, positions, width, axis, ny=None):
    """positions（0..1）の位置に線を引いたマスク。axis=0 は縦線、1 は横線。"""
    ny = ny or n
    m = np.zeros((ny, n))
    if axis == 0:
        x = (np.arange(n) + 0.5) / n
        for p in positions:
            d = np.abs(((x - p + 0.5) % 1.0) - 0.5)
            m = np.maximum(m, (1 - smoothstep(width * 0.5, width, d))[None, :])
    else:
        y = (np.arange(ny) + 0.5) / ny
        for p in positions:
            d = np.abs(y - p)
            m = np.maximum(m, (1 - smoothstep(width * 0.5, width, d))[:, None])
    return m


def dots_mask(n, xs, ys, radius, ny=None):
    """リベットなどの丸い点。中心が 1 のなだらかな山。"""
    ny = ny or n
    yy, xx = np.mgrid[0:ny, 0:n]
    xx = (xx + 0.5) / n
    yy = (yy + 0.5) / ny
    m = np.zeros((ny, n))
    for py in ys:
        for px in xs:
            dx = np.abs(((xx - px + 0.5) % 1.0) - 0.5) * n
            dy = np.abs(yy - py) * ny
            d = np.sqrt(dx * dx + dy * dy) / (radius * n)
            m = np.maximum(m, np.clip(1 - d * d, 0, 1))
    return m


def normal_from_height(h, strength=4.0):
    gy, gx = np.gradient(h)
    nx = -gx * strength
    ny = gy * strength
    nz = np.ones_like(h)
    l = np.sqrt(nx * nx + ny * ny + nz * nz)
    return np.dstack([nx / l * 0.5 + 0.5, ny / l * 0.5 + 0.5, nz / l * 0.5 + 0.5])


def lerp(a, b, t):
    t = t[..., None] if np.ndim(t) == 2 and np.ndim(a) == 1 else t
    return np.asarray(a) * (1 - t) + np.asarray(b) * t


def mix(base, color, t):
    """base（H×W×3）に color を t（H×W）の割合で重ねる。"""
    return base * (1 - t[..., None]) + np.asarray(color)[None, None, :] * t[..., None]


# --- 画像とマテリアル ------------------------------------------------------------------

def save_image(name, arr, non_color=False):
    """arr は H×W×3 か H×W×4（0..1、上が v=1）。PNG に保存して Blender に読み込む。"""
    os.makedirs(TEX_DIR, exist_ok=True)
    arr = np.clip(arr, 0, 1)
    if arr.ndim == 2:
        arr = np.dstack([arr, arr, arr])
    if arr.shape[2] == 3:
        arr = np.dstack([arr, np.ones(arr.shape[:2])])
    hgt, wid = arr.shape[:2]
    path = os.path.join(TEX_DIR, name + ".png")
    img = bpy.data.images.get(name)
    if img is not None:
        bpy.data.images.remove(img)
    img = bpy.data.images.new(name, wid, hgt, alpha=True)
    # numpy は上の行から、Blender は下の行から並ぶ
    img.pixels.foreach_set(np.flipud(arr).astype(np.float32).ravel())
    img.filepath_raw = path
    img.file_format = "PNG"
    img.save()
    if non_color:
        img.colorspace_settings.is_data = True
    return img


def material(name, color=None, rough=0.6, metal=0.0, emission=None, emit_strength=0.0,
             alpha=None, blend=False):
    """画像を使わない単色のマテリアル。"""
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    if color is not None:
        bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    if emission is not None:
        bsdf.inputs["Emission Color"].default_value = (*emission, 1)
        bsdf.inputs["Emission Strength"].default_value = emit_strength
    if alpha is not None:
        bsdf.inputs["Alpha"].default_value = alpha
        _set_blend(m, blend)
    return m


def textured_material(name, base, orm=None, normal=None, normal_strength=1.0, emission=None,
                      emit_strength=1.0, alpha_from_base=False, blend=False):
    """glTF に書き出せる形でつなぐ。orm は R=AO, G=粗さ, B=金属。"""
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        if n.type not in ("BSDF_PRINCIPLED", "OUTPUT_MATERIAL"):
            nt.nodes.remove(n)
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    tb = nt.nodes.new("ShaderNodeTexImage")
    tb.image = base
    tb.location = (-600, 300)
    nt.links.new(tb.outputs["Color"], bsdf.inputs["Base Color"])
    if alpha_from_base:
        nt.links.new(tb.outputs["Alpha"], bsdf.inputs["Alpha"])
        _set_blend(m, blend)
    if orm is not None:
        to = nt.nodes.new("ShaderNodeTexImage")
        to.image = orm
        to.location = (-600, 0)
        sep = nt.nodes.new("ShaderNodeSeparateColor")
        sep.location = (-300, 0)
        nt.links.new(to.outputs["Color"], sep.inputs["Color"])
        nt.links.new(sep.outputs["Green"], bsdf.inputs["Roughness"])
        nt.links.new(sep.outputs["Blue"], bsdf.inputs["Metallic"])
    if normal is not None:
        tn = nt.nodes.new("ShaderNodeTexImage")
        tn.image = normal
        tn.location = (-600, -300)
        nm = nt.nodes.new("ShaderNodeNormalMap")
        nm.location = (-300, -300)
        nm.inputs["Strength"].default_value = normal_strength
        nt.links.new(tn.outputs["Color"], nm.inputs["Color"])
        nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    if emission is not None:
        te = nt.nodes.new("ShaderNodeTexImage")
        te.image = emission
        te.location = (-600, -600)
        nt.links.new(te.outputs["Color"], bsdf.inputs["Emission Color"])
        bsdf.inputs["Emission Strength"].default_value = emit_strength
    return m


def _set_blend(m, blend):
    # Blender 4.2 以降は blend_method が無くなり surface_render_method になった
    if hasattr(m, "surface_render_method"):
        try:
            m.surface_render_method = "BLENDED" if blend else "DITHERED"
        except TypeError:
            pass
    if hasattr(m, "blend_method"):
        try:
            m.blend_method = "BLEND" if blend else "CLIP"
        except TypeError:
            pass


# --- メッシュ ----------------------------------------------------------------------

def collection(name):
    """部屋ごとのコレクション。作り直すときは中身を消す。"""
    col = bpy.data.collections.get(name)
    if col is None:
        col = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(col)
    for o in list(col.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    return col


def box(col, name, x0, x1, y0, y1, z0, z1, mat, uv_scale=2.0):
    """軸に沿った箱。uv はワールド座標から付ける（壁の v は 高さ/3.5）。"""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x = x0 if v.co.x < 0 else x1
        v.co.y = y0 if v.co.y < 0 else y1
        v.co.z = z0 if v.co.z < 0 else z1
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    col.objects.link(ob)
    if isinstance(mat, (list, tuple)):
        for m in mat:
            me.materials.append(m)
    else:
        me.materials.append(mat)
    world_uv(ob, uv_scale)
    return ob


def mesh_object(col, name, bm, mats, uv_scale=None):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    col.objects.link(ob)
    for m in mats:
        me.materials.append(m)
    if uv_scale:
        world_uv(ob, uv_scale)
    return ob


def world_uv(ob, scale=2.0, wall_height=H):
    """面の向きで投影する UV。横は scale m で1周、壁の縦は床から天井までで 0..1。"""
    me = ob.data
    if not me.uv_layers:
        me.uv_layers.new(name="UVMap")
    uv = me.uv_layers.active.data
    mw = ob.matrix_world
    for poly in me.polygons:
        n = (mw.to_3x3() @ poly.normal)
        ax, ay, az = abs(n.x), abs(n.y), abs(n.z)
        for li in poly.loop_indices:
            co = mw @ me.vertices[me.loops[li].vertex_index].co
            if az >= ax and az >= ay:
                u, v = co.x / scale, co.y / scale
            elif ax >= ay:
                u = (co.y if n.x > 0 else -co.y) / scale
                v = co.z / wall_height
            else:
                u = (-co.x if n.y > 0 else co.x) / scale
                v = co.z / wall_height
            uv[li].uv = (u, v)


def fit_uv(ob):
    """UV を 0..1 に広げる（モニターの画面など、1枚の絵を貼る物用）。"""
    me = ob.data
    uv = me.uv_layers.active.data
    us = [uv[i].uv.x for p in me.polygons for i in p.loop_indices]
    vs = [uv[i].uv.y for p in me.polygons for i in p.loop_indices]
    u0, u1, v0, v1 = min(us), max(us), min(vs), max(vs)
    for p in me.polygons:
        for i in p.loop_indices:
            uv[i].uv = ((uv[i].uv.x - u0) / max(u1 - u0, 1e-6), (uv[i].uv.y - v0) / max(v1 - v0, 1e-6))


def quad_uv(ob, i):
    """2×2 に並べた画像のうち i 番目の1枚を使う（書類など）。"""
    qx, qy = (i % 2) * 0.5, ((i // 2) % 2) * 0.5
    uv = ob.data.uv_layers.active.data
    for l in uv:
        l.uv = (qx + l.uv.x * 0.5, qy + l.uv.y * 0.5)


def assign_faces(ob, mat_index, pred):
    """pred(ワールド法線, ワールド中心) が真の面に mat_index のマテリアルを割り当てる。"""
    mw = ob.matrix_world
    for poly in ob.data.polygons:
        if pred(mw.to_3x3() @ poly.normal, mw @ poly.center):
            poly.material_index = mat_index


def wall_x(col, name, y, x0, x1, mat, pad=T, z0=0.0, z1=H):
    """y の位置に x0..x1 の東西方向の壁（ゲームの _wall_x と同じ寸法）。"""
    return box(col, name, min(x0, x1) - pad / 2, max(x0, x1) + pad / 2, y - T / 2, y + T / 2, z0, z1, mat)


def wall_y(col, name, x, y0, y1, mat, pad=T, z0=0.0, z1=H):
    """x の位置に y0..y1 の南北方向の壁。"""
    return box(col, name, x - T / 2, x + T / 2, min(y0, y1) - pad / 2, max(y0, y1) + pad / 2, z0, z1, mat)


def floor(col, name, x0, x1, y0, y1, mat, depth=0.5):
    return box(col, name, x0, x1, y0, y1, -depth, 0.0, mat)


def cylinder(col, name, p0, p1, radius, mat, verts=12):
    """p0 から p1 へ伸びる円柱（配管など）。"""
    from mathutils import Vector
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=verts, radius1=radius, radius2=radius, depth=d.length)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    col.objects.link(ob)
    me.materials.append(mat)
    ob.location = (p0 + p1) / 2
    ob.rotation_mode = "QUATERNION"
    ob.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(d.normalized())
    for p in me.polygons:
        p.use_smooth = True
    return ob


def plane(col, name, cx, cy, cz, sx, sy, mat, rot=(0, 0, 0)):
    """中心 (cx,cy,cz)、大きさ sx×sy の板（UV は 0..1）。"""
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=0.5)
    uvl = bm.loops.layers.uv.new("UVMap")
    for f in bm.faces:
        for l in f.loops:
            l[uvl].uv = (l.vert.co.x + 0.5, l.vert.co.y + 0.5)
    for v in bm.verts:
        v.co.x *= sx
        v.co.y *= sy
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    col.objects.link(ob)
    me.materials.append(mat)
    ob.location = (cx, cy, cz)
    ob.rotation_euler = rot
    return ob


def bake_transforms(col):
    """書き出し前に、位置・回転をメッシュに焼き込む（原点は 0,0,0 のまま）。"""
    bpy.context.view_layer.update()   # 作ったばかりの物は matrix_world がまだ古い
    for ob in col.objects:
        if ob.type != "MESH":
            continue
        ob.data.transform(ob.matrix_world)
        ob.matrix_world.identity()


def text(col, s, loc, size, mat, rot=(math.radians(90), 0, 0)):
    """文字をメッシュにして置く（既定は -Y 側から読める向き）。"""
    cu = bpy.data.curves.new("Text", "FONT")
    cu.body = s
    cu.size = size
    cu.align_x = "CENTER"
    cu.align_y = "CENTER"
    cu.extrude = 0.002
    ob = bpy.data.objects.new("Text", cu)
    col.objects.link(ob)
    ob.location = loc
    ob.rotation_euler = rot
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    mo = bpy.data.objects.new("Text_Mesh", me)
    col.objects.link(mo)
    mo.matrix_world = ob.matrix_world
    me.materials.clear()
    me.materials.append(mat)
    bpy.data.objects.remove(ob, do_unlink=True)
    return mo


def finish(col, name):
    """親子を外して位置を焼き込み、1つのメッシュにまとめる。"""
    bpy.context.view_layer.update()
    for ob in col.objects:
        if ob.parent is not None:
            mw = ob.matrix_world.copy()
            ob.parent = None
            ob.matrix_world = mw
    bake_transforms(col)
    return join_all(col, name)


def join_all(col, name):
    """コレクションのメッシュを1つにまとめる（ゲームでの描画回数をマテリアルの数まで減らす）。"""
    obs = [o for o in col.objects if o.type == "MESH"]
    if len(obs) < 2:
        return obs[0] if obs else None
    with bpy.context.temp_override(active_object=obs[0], selected_editable_objects=obs,
                                   selected_objects=obs):
        bpy.ops.object.join()
    obs[0].name = name
    obs[0].data.name = name
    return obs[0]


def export_glb(col, path):
    """コレクションの物だけを glTF バイナリで書き出す（+Y が上）。"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in col.objects:
        o.select_set(True)
    bpy.ops.export_scene.gltf(
        filepath=path,
        export_format="GLB",
        use_selection=True,
        export_yup=True,
        export_apply=True,
        export_materials="EXPORT",
        export_lights=False,
        export_cameras=False,
        export_image_format="WEBP",   # PNG のままだと 20MB を超える。Godot 4 は WebP を読める
    )
