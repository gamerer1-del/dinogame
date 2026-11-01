class_name DinoModel
extends Node3D
## ストーカー（小型の肉食恐竜）の仮モデル。基本図形を組み合わせて作り、
## 歩くと脚が動き、尾が揺れ、状態に合わせて首を振ったり口を開けたりする。
## 足元が原点、頭は -Z（前）向き。全長約2.3m、頭の高さ約1.4m。
## Blenderでモデルを作ったら assets/models/stalker.glb に置けば、こちらは使われなくなる。

enum Mood { CALM, ALERT, SEARCH, CHASE }

const THIGH_REST := 0.35     # 太ももは前へ
const KNEE_REST := -0.75     # すねは後ろへ（鳥のような逆関節に見える）
const ANKLE_REST := 0.4

var eye_mat: StandardMaterial3D

var _body: Node3D
var _torso: Node3D
var _neck: Node3D
var _jaw: Node3D
var _tail: Array = []
var _legs: Array = []        # [太もも, ひざ] の組
var _phase := 0.0
var _t := 0.0

var _skin: StandardMaterial3D
var _belly: StandardMaterial3D
var _dark: StandardMaterial3D
var _teeth: StandardMaterial3D
var _claw: StandardMaterial3D
var _mouth: StandardMaterial3D


func _ready() -> void:
	_skin = _mat(Color(0.3, 0.33, 0.2), 0.45)
	_belly = _mat(Color(0.52, 0.49, 0.38), 0.7)
	_dark = _mat(Color(0.09, 0.1, 0.07), 0.6)
	_teeth = _mat(Color(0.92, 0.88, 0.76), 0.4)
	_claw = _mat(Color(0.14, 0.12, 0.1), 0.3)
	_mouth = _mat(Color(0.4, 0.06, 0.06), 0.4)
	_build()


## 毎フレーム呼ぶ。speed は水平の移動速度（m/秒）。
func animate(delta: float, speed: float, mood: int) -> void:
	_t += delta
	var move := clampf(speed / 2.5, 0.0, 1.5)
	_phase += delta * (2.0 + speed * 2.2)

	# 脚: 左右を半周期ずらして振る
	for i in _legs.size():
		var leg: Array = _legs[i]
		var p := _phase + PI * i
		(leg[0] as Node3D).rotation.x = THIGH_REST + sin(p) * 0.55 * move
		(leg[1] as Node3D).rotation.x = KNEE_REST - (0.5 + 0.5 * sin(p + PI / 2.0)) * 0.6 * move

	# 胴: 歩くと上下に弾み、止まっていると呼吸する
	_body.position.y = 1.0 + absf(sin(_phase)) * 0.05 * move
	_body.rotation.z = sin(_phase) * 0.05 * move
	var breath := 1.0 + 0.025 * sin(_t * 2.0)
	_torso.scale = Vector3(breath, 1.0, breath)

	# 尾: 根元から先へ波が伝わるように揺らす
	for i in _tail.size():
		var seg: Node3D = _tail[i]
		seg.rotation.y = sin(_t * 1.6 - i * 0.7) * (0.1 + 0.12 * move)

	# 首と口: 状態で変える
	var look := sin(_t * 0.5) * 0.15
	var jaw := 0.04 + 0.03 * sin(_t * 1.3)
	match mood:
		Mood.ALERT:
			look = sin(_t * 6.0) * 0.05
			jaw = 0.18
		Mood.SEARCH:
			look = sin(_t * 1.2) * 0.6
			jaw = 0.08
		Mood.CHASE:
			look = 0.0
			jaw = 0.6 + sin(_t * 9.0) * 0.08
	_neck.rotation.y = lerp_angle(_neck.rotation.y, look, 6.0 * delta)
	_jaw.rotation.x = lerpf(_jaw.rotation.x, -jaw, 10.0 * delta)   # マイナスで下あごが下がる


func _build() -> void:
	_body = _pivot(self, Vector3(0, 1.0, 0.05))

	# 胴体（Z方向に寝かせたカプセル）と腹、胸
	_torso = _pivot(_body, Vector3.ZERO, Vector3(deg_to_rad(82), 0, 0))
	_capsule(_torso, Vector3.ZERO, 0.3, 1.3, Vector3.ZERO, _skin)
	_capsule(_body, Vector3(0, -0.1, -0.05), 0.24, 1.0, Vector3(deg_to_rad(90), 0, 0), _belly)
	_ball(_body, Vector3(0, 0.03, -0.45), 0.29, _skin)
	# 背中のとげ（オリジナルの特徴: 首から尾の付け根まで並ぶ暗い突起）
	for i in 8:
		var z := -0.7 + i * 0.18
		var h := 0.1 + 0.08 * sin(PI * (i + 1) / 9.0)
		_cone(_body, Vector3(0, 0.29 - absf(z) * 0.05, z), 0.04, 0.0, h, Vector3.ZERO, _dark)

	# 首と頭
	_neck = _pivot(_body, Vector3(0, 0.12, -0.62), Vector3(deg_to_rad(35), 0, 0))
	_capsule(_neck, Vector3(0, 0, -0.22), 0.14, 0.6, Vector3(deg_to_rad(90), 0, 0), _skin)
	var head := _pivot(_neck, Vector3(0, 0, -0.5), Vector3(deg_to_rad(-35), 0, 0))
	var skull := _cone(head, Vector3(0, 0.03, -0.27), 0.2, 0.09, 0.66, Vector3(deg_to_rad(-90), 0, 0), _skin)
	skull.scale = Vector3(0.85, 1.0, 1.0)
	_box(head, Vector3(0, 0.15, -0.12), Vector3(0.3, 0.05, 0.14), _dark)          # 眉の張り出し
	for x in [-0.115, 0.115]:
		var eye := _ball(head, Vector3(x, 0.1, -0.2), 0.035, eye_mat if eye_mat != null else _teeth)
		eye.name = "Eye"
	for i in 4:                                                                  # 上の歯
		for x in [-0.07, 0.07]:
			_cone(head, Vector3(x, -0.06, -0.18 - i * 0.1), 0.018, 0.0, 0.07, Vector3(PI, 0, 0), _teeth)
	_jaw = _pivot(head, Vector3(0, -0.06, -0.04))
	var jaw_mesh := _cone(_jaw, Vector3(0, -0.04, -0.24), 0.12, 0.05, 0.48, Vector3(deg_to_rad(-90), 0, 0), _skin)
	jaw_mesh.scale = Vector3(0.8, 1.0, 0.7)
	_box(_jaw, Vector3(0, 0.0, -0.22), Vector3(0.13, 0.02, 0.36), _mouth)          # 口の中
	for i in 3:                                                                  # 下の歯
		for x in [-0.055, 0.055]:
			_cone(_jaw, Vector3(x, 0.01, -0.16 - i * 0.1), 0.015, 0.0, 0.06, Vector3.ZERO, _teeth)

	# 小さな前脚と爪
	for s in [-1.0, 1.0]:
		var arm := _pivot(_body, Vector3(0.2 * s, -0.12, -0.52), Vector3(deg_to_rad(40), 0, 0.2 * s))
		_capsule(arm, Vector3(0, -0.14, 0), 0.05, 0.3, Vector3.ZERO, _skin)
		for c in 3:
			_cone(arm, Vector3((c - 1) * 0.03, -0.3, -0.02), 0.012, 0.0, 0.07, Vector3(deg_to_rad(160), 0, 0), _claw)

	# 尾（4節。根元から先へ細くなる）
	var parent: Node3D = _pivot(_body, Vector3(0, 0.05, 0.6), Vector3(deg_to_rad(-6), 0, 0))
	var radii := [0.22, 0.15, 0.1, 0.06]
	var lengths := [0.45, 0.42, 0.38, 0.34]
	for i in 4:
		var r0: float = radii[i]
		var r1: float = radii[i + 1] if i < 3 else 0.02
		var l: float = lengths[i]
		_cone(parent, Vector3(0, 0, l / 2.0), r0, r1, l, Vector3(deg_to_rad(90), 0, 0), _skin)
		_cone(parent, Vector3(0, r0 * 0.9, l / 2.0), 0.03, 0.0, 0.08, Vector3.ZERO, _dark)
		_tail.append(parent)
		parent = _pivot(parent, Vector3(0, 0, l))

	# 後ろ脚（太もも → ひざ → 足首 → 3本指）
	for s in [-1.0, 1.0]:
		var thigh := _pivot(_body, Vector3(0.24 * s, -0.05, 0.15), Vector3(THIGH_REST, 0, 0))
		_capsule(thigh, Vector3(0, -0.2, 0), 0.13, 0.5, Vector3.ZERO, _skin)
		var knee := _pivot(thigh, Vector3(0, -0.42, 0), Vector3(KNEE_REST, 0, 0))
		_capsule(knee, Vector3(0, -0.2, 0), 0.07, 0.48, Vector3.ZERO, _skin)
		var ankle := _pivot(knee, Vector3(0, -0.42, 0), Vector3(ANKLE_REST, 0, 0))
		_capsule(ankle, Vector3(0, -0.07, 0), 0.05, 0.2, Vector3.ZERO, _skin)
		for t in 3:
			var toe_x := (t - 1) * 0.045
			_box(ankle, Vector3(toe_x, -0.15, -0.09), Vector3(0.035, 0.035, 0.2), _skin)
			_cone(ankle, Vector3(toe_x, -0.15, -0.2), 0.014, 0.0, 0.05, Vector3(deg_to_rad(-100), 0, 0), _claw)
		_legs.append([thigh, knee])


# --- 部品 -----------------------------------------------------------------------

func _pivot(parent: Node3D, pos: Vector3, rot := Vector3.ZERO) -> Node3D:
	var n := Node3D.new()
	n.position = pos
	n.rotation = rot
	parent.add_child(n)
	return n


func _capsule(parent: Node3D, pos: Vector3, radius: float, length: float, rot: Vector3, mat: Material) -> MeshInstance3D:
	var m := CapsuleMesh.new()
	m.radius = radius
	m.height = maxf(length, radius * 2.0)
	return _mesh(parent, m, pos, rot, mat)


func _cone(parent: Node3D, pos: Vector3, bottom: float, top: float, height: float, rot: Vector3, mat: Material) -> MeshInstance3D:
	var m := CylinderMesh.new()
	m.bottom_radius = bottom
	m.top_radius = top
	m.height = height
	m.radial_segments = 12
	m.rings = 1
	return _mesh(parent, m, pos, rot, mat)


func _ball(parent: Node3D, pos: Vector3, radius: float, mat: Material) -> MeshInstance3D:
	var m := SphereMesh.new()
	m.radius = radius
	m.height = radius * 2.0
	return _mesh(parent, m, pos, Vector3.ZERO, mat)


func _box(parent: Node3D, pos: Vector3, size: Vector3, mat: Material) -> MeshInstance3D:
	var m := BoxMesh.new()
	m.size = size
	return _mesh(parent, m, pos, Vector3.ZERO, mat)


func _mesh(parent: Node3D, mesh: Mesh, pos: Vector3, rot: Vector3, mat: Material) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	mi.mesh = mesh
	mi.material_override = mat
	mi.position = pos
	mi.rotation = rot
	parent.add_child(mi)
	return mi


func _mat(c: Color, rough: float) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.albedo_color = c
	m.roughness = rough
	return m
