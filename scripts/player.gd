class_name Player
extends CharacterBody3D
## 主人公（三人称）。歩く・しゃがむ・走る・隠れる・物を投げる・懐中電灯。
## 足音の大きさは Game.emit_noise で恐竜に伝わる。

const WALK_SPEED := 3.0
const CROUCH_SPEED := 1.4
const SPRINT_SPEED := 5.5
const MOUSE_SENS := 0.0025
const PAD_SENS := 2.5
const STEP_LENGTH := 0.8          # この距離ごとに足音が1回鳴る（メートル）
const NOISE_CROUCH := 2.0         # 足音が聞こえる距離（メートル）
const NOISE_WALK := 6.0
const NOISE_SPRINT := 14.0
const PUDDLE_MULT := 2.0          # 水たまりでは足音が何倍になるか
const HIDE_NOISE := 3.0           # ロッカーの扉がきしむ音
const STAND_HEIGHT := 1.7
const CROUCH_HEIGHT := 1.0
const INTERACT_RANGE := 2.0
const THROW_SPEED := 9.0
const MODEL_PATH := "res://assets/models/player.glb"

var ammo := 0
var is_hidden := false
var is_crouching := false
var noise_level := 0.0            # HUD 表示用（直近の足音の大きさ）
var focus: Node = null            # いま E で調べられる物

var _hide_spot: Node = null
var _light_before_hiding := true
var _step_accum := 0.0
var _gravity: float = ProjectSettings.get_setting("physics/3d/default_gravity")

var _shape: CollisionShape3D
var _capsule: CapsuleShape3D
var _body_mesh: MeshInstance3D
var _model: Node3D
var _yaw: Node3D
var _pitch: Node3D
var _arm: SpringArm3D
var camera: Camera3D
var _flashlight: SpotLight3D


func _ready() -> void:
	add_to_group("player")

	_capsule = CapsuleShape3D.new()
	_capsule.radius = 0.35
	_capsule.height = STAND_HEIGHT
	_shape = CollisionShape3D.new()
	_shape.shape = _capsule
	_shape.position.y = STAND_HEIGHT / 2.0
	add_child(_shape)

	# 見た目（白衣の研究員のつもりの仮モデル）
	_model = Node3D.new()
	add_child(_model)
	_body_mesh = MeshInstance3D.new()
	var cm := CapsuleMesh.new()
	cm.radius = 0.33
	cm.height = STAND_HEIGHT
	_body_mesh.mesh = cm
	_body_mesh.position.y = STAND_HEIGHT / 2.0
	_body_mesh.material_override = _mat(Color(0.85, 0.86, 0.82))
	_model.add_child(_body_mesh)
	var visor := MeshInstance3D.new()
	var vm := BoxMesh.new()
	vm.size = Vector3(0.3, 0.1, 0.12)
	visor.mesh = vm
	visor.position = Vector3(0, 1.5, -0.3)
	visor.material_override = _mat(Color(0.1, 0.12, 0.15))
	_model.add_child(visor)
	# Blenderで作った主人公のモデルがあれば差し替える（足元が原点、-Z＝Blenderの+Y が正面）
	if ResourceLoader.exists(MODEL_PATH):
		var scene := load(MODEL_PATH) as PackedScene
		if scene != null:
			_model.add_child(scene.instantiate())
			_body_mesh.visible = false
			visor.visible = false

	# 三人称カメラ: yaw（左右）→ pitch（上下）→ SpringArm（壁にめり込まない）→ Camera
	_yaw = Node3D.new()
	_yaw.position.y = STAND_HEIGHT - 0.2
	add_child(_yaw)
	_pitch = Node3D.new()
	_pitch.rotation.x = -0.2
	_yaw.add_child(_pitch)
	_arm = SpringArm3D.new()
	_arm.spring_length = 3.2
	_arm.margin = 0.2
	_arm.position = Vector3(0.45, 0, 0)
	var arm_shape := SphereShape3D.new()
	arm_shape.radius = 0.2
	_arm.shape = arm_shape
	_arm.add_excluded_object(get_rid())
	_pitch.add_child(_arm)
	camera = Camera3D.new()
	camera.fov = 70
	camera.current = true
	_arm.add_child(camera)

	_flashlight = SpotLight3D.new()
	_flashlight.position = Vector3(0.3, -0.1, -0.4)
	_flashlight.spot_range = 24.0
	_flashlight.spot_angle = 32.0
	_flashlight.light_energy = 4.0
	_flashlight.light_color = Color(1.0, 0.95, 0.85)
	_flashlight.shadow_enabled = true
	_pitch.add_child(_flashlight)


func flashlight_on() -> bool:
	return _flashlight.visible


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		_rotate_camera(-event.relative.x * MOUSE_SENS, -event.relative.y * MOUSE_SENS)
		return
	if event is InputEventMouseButton and event.pressed and Input.mouse_mode != Input.MOUSE_MODE_CAPTURED \
			and Game.state == Game.State.PLAY:
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
		get_viewport().set_input_as_handled()
		return
	if event.is_action_pressed("pause"):
		Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
		return
	if Game.state != Game.State.PLAY:
		return
	if event.is_action_pressed("interact"):
		_interact()
	elif event.is_action_pressed("throw") and not is_hidden:
		_throw()
	elif event.is_action_pressed("flashlight") and not is_hidden:
		_flashlight.visible = not _flashlight.visible


func _rotate_camera(dx: float, dy: float) -> void:
	_yaw.rotate_y(dx)
	_pitch.rotation.x = clamp(_pitch.rotation.x + dy, -1.2, 0.5)


func _physics_process(delta: float) -> void:
	var pad := Vector2(Input.get_joy_axis(0, JOY_AXIS_RIGHT_X), Input.get_joy_axis(0, JOY_AXIS_RIGHT_Y))
	if pad.length() > 0.2:
		_rotate_camera(-pad.x * PAD_SENS * delta, -pad.y * PAD_SENS * delta)

	noise_level = move_toward(noise_level, 0.0, 8.0 * delta)
	_update_focus()

	if is_hidden or Game.state != Game.State.PLAY:
		velocity = Vector3.ZERO
		return

	if not is_on_floor():
		velocity.y -= _gravity * delta

	_set_crouch(Input.is_action_pressed("crouch"))
	var sprinting := Input.is_action_pressed("sprint") and not is_crouching

	var input := Input.get_vector("move_left", "move_right", "move_forward", "move_back")
	var cam_basis := _yaw.global_transform.basis
	var dir := cam_basis.x * input.x + cam_basis.z * input.y
	dir.y = 0.0
	dir = dir.normalized() * minf(input.length(), 1.0)
	var speed := CROUCH_SPEED if is_crouching else (SPRINT_SPEED if sprinting else WALK_SPEED)
	velocity.x = dir.x * speed
	velocity.z = dir.z * speed
	move_and_slide()

	var flat := Vector2(velocity.x, velocity.z)
	if flat.length() > 0.1:
		_model.rotation.y = lerp_angle(_model.rotation.y, atan2(-flat.x, -flat.y), 12.0 * delta)

	# 足音
	if is_on_floor() and flat.length() > 0.1:
		_step_accum += flat.length() * delta
		if _step_accum >= STEP_LENGTH:
			_step_accum = 0.0
			var r := NOISE_CROUCH if is_crouching else (NOISE_SPRINT if sprinting else NOISE_WALK)
			if Game.is_in_puddle(global_position):
				r *= PUDDLE_MULT
			Game.emit_noise(global_position, r, self)
			var vol := -16.0 if is_crouching else (-1.0 if sprinting else -8.0)
			if Game.is_in_puddle(global_position):
				Sfx.play_at("step_wet", global_position, vol + 3.0)
			else:
				Sfx.play_at("step", global_position, vol)
			noise_level = maxf(noise_level, r)


func _set_crouch(on: bool) -> void:
	if on == is_crouching:
		return
	is_crouching = on
	var h := CROUCH_HEIGHT if on else STAND_HEIGHT
	_capsule.height = h
	_shape.position.y = h / 2.0
	(_body_mesh.mesh as CapsuleMesh).height = h
	_body_mesh.position.y = h / 2.0
	create_tween().tween_property(_yaw, "position:y", h - 0.2, 0.15)


func _update_focus() -> void:
	if is_hidden:
		focus = _hide_spot
		return
	var best: Node = null
	var best_d := INTERACT_RANGE
	var here := Vector2(global_position.x, global_position.z)
	for n in get_tree().get_nodes_in_group("interactable"):
		var p: Vector3 = n.global_position
		var d := here.distance_to(Vector2(p.x, p.z))
		if d < best_d:
			best = n
			best_d = d
	focus = best


func _interact() -> void:
	if focus != null and is_instance_valid(focus) and focus.has_method("interact"):
		focus.interact(self)


func _throw() -> void:
	if ammo <= 0:
		Game.show_hint("投げられる物を持っていない")
		return
	Sfx.play_at("step", global_position + Vector3.UP, -14.0, 10.0, 0.3)   # 投げる時の衣ずれ
	ammo -= 1
	var can := Throwable.new()
	get_tree().current_scene.add_child(can)
	var fwd := -camera.global_transform.basis.z
	can.global_position = global_position + Vector3(0, 1.4, 0) + fwd * 0.6
	can.launch(fwd * THROW_SPEED + Vector3.UP * 3.0)


func enter_hiding(spot: Node) -> void:
	is_hidden = true
	_hide_spot = spot
	velocity = Vector3.ZERO
	_model.visible = false
	_shape.set_deferred("disabled", true)
	_light_before_hiding = _flashlight.visible
	_flashlight.visible = false
	Game.emit_noise(global_position, HIDE_NOISE, self)
	Sfx.play_at("locker", global_position, -6.0)
	Game.show_hint("息をひそめている……（Eで出る）")


func exit_hiding() -> void:
	is_hidden = false
	_hide_spot = null
	_model.visible = true
	_shape.set_deferred("disabled", false)
	_flashlight.visible = _light_before_hiding
	Game.emit_noise(global_position, HIDE_NOISE, self)
	Sfx.play_at("locker", global_position, -6.0)


func _mat(c: Color) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.albedo_color = c
	m.roughness = 0.8
	return m
