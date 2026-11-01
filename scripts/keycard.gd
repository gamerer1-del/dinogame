class_name KeyCard
extends Node3D
## カードキー。拾うと給餌室の北の扉が開けられる。

var _mesh: MeshInstance3D


func _ready() -> void:
	add_to_group("interactable")
	_mesh = MeshInstance3D.new()
	var bm := BoxMesh.new()
	bm.size = Vector3(0.25, 0.02, 0.16)
	_mesh.mesh = bm
	var m := StandardMaterial3D.new()
	m.albedo_color = Color(0.2, 0.9, 0.4)
	m.emission_enabled = true
	m.emission = Color(0.2, 0.9, 0.4)
	m.emission_energy_multiplier = 1.5
	_mesh.material_override = m
	add_child(_mesh)
	var glow := OmniLight3D.new()
	glow.light_color = Color(0.2, 0.9, 0.4)
	glow.light_energy = 0.6
	glow.omni_range = 1.5
	glow.position.y = 0.2
	add_child(glow)


func _process(delta: float) -> void:
	_mesh.rotation.y += delta * 1.5


func get_prompt(_player) -> String:
	return "E: カードキーを取る"


func interact(_player) -> void:
	Game.has_keycard = true
	Sfx.play("pickup", -6.0, 0.8)
	Game.show_hint("カードキーを手に入れた。北の扉を開けよう")
	queue_free()
