class_name LockedDoor
extends StaticBody3D
## カードキーで開く扉。開けるときの音で恐竜が寄ってくる。

const OPEN_NOISE := 10.0

var size := Vector3(2.0, 3.5, 0.2)
var reader_mat: StandardMaterial3D   # 横のカードリーダーの表示灯（レベル側で作る）
var _shape: CollisionShape3D
var _open := false


func _ready() -> void:
	add_to_group("interactable")
	var bs := BoxShape3D.new()
	bs.size = size
	_shape = CollisionShape3D.new()
	_shape.shape = bs
	add_child(_shape)
	var mi := MeshInstance3D.new()
	var bm := BoxMesh.new()
	bm.size = size
	mi.mesh = bm
	var m := StandardMaterial3D.new()
	m.albedo_color = Color(0.45, 0.42, 0.2)
	m.metallic = 0.5
	m.roughness = 0.5
	mi.material_override = m
	add_child(mi)


func get_prompt(_player) -> String:
	return "E: 扉を開ける" if Game.has_keycard else "ロックされている（カードキーが必要）"


func interact(_player) -> void:
	if _open:
		return
	if not Game.has_keycard:
		Game.show_hint("扉はロックされている。どこかにカードキーがあるはずだ")
		return
	_open = true
	remove_from_group("interactable")
	if reader_mat != null:
		reader_mat.albedo_color = Color(0.2, 1.0, 0.3)
		reader_mat.emission = Color(0.2, 1.0, 0.3)
	Game.emit_noise(global_position, OPEN_NOISE, self)
	Game.show_hint("扉が重い音を立てて開く……急げ！")
	var tw := create_tween()
	tw.tween_property(self, "position:y", position.y + size.y - 0.1, 1.5)
	tw.tween_callback(func(): _shape.disabled = true)
