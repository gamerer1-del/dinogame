class_name Throwable
extends RigidBody3D
## 空き缶。拾って投げると、ぶつかった場所で物音が鳴り、恐竜の注意をそらせる。

const IMPACT_NOISE := 12.0

var _armed := false
var _flight_time := 0.0
var _cooldown := 0.0


func _ready() -> void:
	add_to_group("interactable")
	mass = 0.3
	continuous_cd = true
	contact_monitor = true
	max_contacts_reported = 4
	var cyl := CylinderShape3D.new()
	cyl.radius = 0.06
	cyl.height = 0.2
	var cs := CollisionShape3D.new()
	cs.shape = cyl
	add_child(cs)
	var mi := MeshInstance3D.new()
	var cm := CylinderMesh.new()
	cm.top_radius = 0.06
	cm.bottom_radius = 0.06
	cm.height = 0.2
	mi.mesh = cm
	var m := StandardMaterial3D.new()
	m.albedo_color = Color(0.7, 0.15, 0.12)
	m.metallic = 0.7
	m.roughness = 0.35
	mi.material_override = m
	add_child(mi)
	body_entered.connect(_on_body_entered)


func launch(v: Vector3) -> void:
	_armed = true
	_flight_time = 0.0
	linear_velocity = v
	angular_velocity = Vector3(randf(), randf(), randf()) * 8.0


func _physics_process(delta: float) -> void:
	_cooldown -= delta
	if _armed:
		_flight_time += delta
		if _flight_time > 0.5 and linear_velocity.length() < 0.2:
			_armed = false


func _on_body_entered(_body: Node) -> void:
	if _armed and _cooldown <= 0.0:
		_cooldown = 0.25
		Game.emit_noise(global_position, IMPACT_NOISE, self)
		Sfx.play_at("can", global_position, 0.0, 30.0, 0.15)


func get_prompt(_player) -> String:
	return "E: 空き缶を拾う"


func interact(player) -> void:
	player.ammo += 1
	Sfx.play("pickup", -10.0)
	Game.show_hint("空き缶を拾った。左クリックで投げると、落ちた場所で音が鳴る")
	queue_free()
