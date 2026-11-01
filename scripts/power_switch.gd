class_name PowerSwitch
extends Node3D
## 監視室の非常電源のレバー。入れるとエレベーターが動くようになるが、警報が鳴って恐竜が集まってくる。

const ALARM_NOISE := 60.0        # 警報が聞こえる距離（研究所のほぼ全体）

var _lamp: StandardMaterial3D
var _lever: Node3D


func _ready() -> void:
	add_to_group("interactable")
	var body := StandardMaterial3D.new()
	body.albedo_color = Color(0.3, 0.32, 0.3)
	body.metallic = 0.6
	body.roughness = 0.5
	_box(self, Vector3(0, 1.2, 0), Vector3(0.7, 1.0, 0.3), body)
	_lamp = StandardMaterial3D.new()
	_lamp.albedo_color = Color(1.0, 0.2, 0.1)
	_lamp.emission_enabled = true
	_lamp.emission = Color(1.0, 0.2, 0.1)
	_lamp.emission_energy_multiplier = 3.0
	_box(self, Vector3(0, 1.6, 0.16), Vector3(0.14, 0.08, 0.04), _lamp)
	_lever = Node3D.new()
	_lever.position = Vector3(0, 1.15, 0.17)
	_lever.rotation.x = 0.7
	add_child(_lever)
	var grip := StandardMaterial3D.new()
	grip.albedo_color = Color(0.7, 0.1, 0.08)
	_box(_lever, Vector3(0, 0.18, 0), Vector3(0.06, 0.36, 0.06), grip)


func get_prompt(_player) -> String:
	return "" if Game.power_on else "E: 非常電源を入れる（警報が鳴る）"


func interact(_player) -> void:
	if Game.power_on:
		return
	remove_from_group("interactable")
	create_tween().tween_property(_lever, "rotation:x", -0.7, 0.4)
	_lamp.albedo_color = Color(0.2, 1.0, 0.3)
	_lamp.emission = Color(0.2, 1.0, 0.3)
	Game.restore_power()
	Sfx.play("alarm", -2.0)
	Game.emit_noise(global_position, ALARM_NOISE, self)
	Game.show_hint("電源が戻った！ だが警報が……奴が来る。隠れるか、エレベーターへ急げ")


func _box(parent: Node3D, pos: Vector3, s: Vector3, m: Material) -> void:
	var mi := MeshInstance3D.new()
	var bm := BoxMesh.new()
	bm.size = s
	mi.mesh = bm
	mi.material_override = m
	mi.position = pos
	parent.add_child(mi)
