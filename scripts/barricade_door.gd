class_name BarricadeDoor
extends StaticBody3D
## 部屋の出入口の扉。E で開け閉めできる。
## 閉めておくと恐竜は通れず、追いかけてきた恐竜は扉に体当たりする。HITS 回で壊れて開きっぱなしになる。

const HITS := 4                  # 壊れるまでに耐える体当たりの回数（1回およそ1.2秒）
const CLOSE_NOISE := 6.0         # 開け閉めの音が届く距離
const HIT_NOISE := 16.0

var size := Vector3(2.4, 3.4, 0.12)
var is_closed := false
var is_broken := false
var hp := HITS

var _shape: CollisionShape3D
var _panel: Node3D
var _mat: StandardMaterial3D
var slide := Vector3.RIGHT       # 開くときに滑る向き（扉の面に沿って横）


func _ready() -> void:
	add_to_group("interactable")
	add_to_group("barricade")
	var bs := BoxShape3D.new()
	bs.size = size
	_shape = CollisionShape3D.new()
	_shape.shape = bs
	_shape.position.y = size.y / 2.0
	add_child(_shape)

	# 見た目: 金属の扉、黄色と黒の警告帯、のぞき窓
	_panel = Node3D.new()
	add_child(_panel)
	_mat = StandardMaterial3D.new()
	_mat.albedo_color = Color(0.36, 0.38, 0.38)
	_mat.metallic = 0.7
	_mat.roughness = 0.45
	_box(_panel, Vector3(0, size.y / 2.0, 0), size, _mat)
	var stripe := StandardMaterial3D.new()
	stripe.albedo_color = Color(0.75, 0.55, 0.05)
	stripe.roughness = 0.6
	for y in [0.35, 1.1]:
		_box(_panel, Vector3(0, y, 0), Vector3(size.x - 0.1, 0.12, size.z + 0.02), stripe)
	var win := StandardMaterial3D.new()
	win.albedo_color = Color(0.05, 0.06, 0.07)
	win.roughness = 0.1
	_box(_panel, Vector3(0, 1.75, 0), Vector3(0.35, 0.25, size.z + 0.02), win)
	_apply(false)


func get_prompt(_player) -> String:
	if is_broken:
		return ""
	return "E: 扉を開ける" if is_closed else "E: 扉を閉める（恐竜を少し止められる）"


func interact(_player) -> void:
	if is_broken:
		return
	is_closed = not is_closed
	_apply(true)
	Sfx.play_at("slam" if is_closed else "door", global_position + Vector3.UP, -4.0, 25.0)
	Game.emit_noise(global_position, CLOSE_NOISE, self)


## 恐竜の体当たり。壊れたら true を返す。
func hit() -> bool:
	if not is_closed or is_broken:
		return is_broken
	hp -= 1
	Sfx.play_at("bang", global_position + Vector3.UP, 2.0, 40.0)
	Game.emit_noise(global_position, HIT_NOISE, self)
	_mat.albedo_color = Color(0.36, 0.38, 0.38).lerp(Color(0.2, 0.15, 0.12), 1.0 - float(hp) / HITS)
	var tw := create_tween()
	tw.tween_property(_panel, "rotation:x", 0.06, 0.06)
	tw.tween_property(_panel, "rotation:x", 0.0, 0.2)
	if hp <= 0:
		is_broken = true
		is_closed = false
		remove_from_group("interactable")
		Sfx.play_at("break", global_position + Vector3.UP, 4.0, 45.0)
		var fall := create_tween()
		fall.tween_property(_panel, "rotation:x", -1.45, 0.35).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN)
		_shape.disabled = true
	return is_broken


func _apply(animate: bool) -> void:
	_shape.disabled = not is_closed
	var to := Vector3.ZERO if is_closed else slide * (size.x - 0.2)
	if animate:
		create_tween().tween_property(_panel, "position", to, 0.45).set_trans(Tween.TRANS_QUAD)
	else:
		_panel.position = to


func _box(parent: Node3D, pos: Vector3, s: Vector3, m: Material) -> void:
	var mi := MeshInstance3D.new()
	var bm := BoxMesh.new()
	bm.size = s
	mi.mesh = bm
	mi.material_override = m
	mi.position = pos
	parent.add_child(mi)
