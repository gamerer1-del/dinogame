class_name HidingSpot
extends StaticBody3D
## ロッカーや冷蔵庫。E で中に隠れると、恐竜から見えなくなる。

var size := Vector3(0.6, 2.0, 0.9)
var label := "ロッカー"
var color := Color(0.3, 0.36, 0.4)


func _ready() -> void:
	add_to_group("interactable")
	var bs := BoxShape3D.new()
	bs.size = size
	var cs := CollisionShape3D.new()
	cs.shape = bs
	add_child(cs)
	var mi := MeshInstance3D.new()
	var bm := BoxMesh.new()
	bm.size = size
	mi.mesh = bm
	var m := StandardMaterial3D.new()
	m.albedo_color = color
	m.metallic = 0.6
	m.roughness = 0.45
	mi.material_override = m
	add_child(mi)


func get_prompt(player) -> String:
	return "E: 出る" if player.is_hidden else "E: %sに隠れる" % label


func interact(player) -> void:
	if player.is_hidden:
		player.exit_hiding()
	else:
		player.enter_hiding(self)
