class_name Stalker
extends CharacterBody3D
## ストーカー（小型の肉食恐竜）。耳が良く、目は近くしか見えない。
## 状態: 巡回 → 警戒 → 捜索 → 追跡 → 捕獲。見失えば捜索を経て巡回に戻る。

enum State { PATROL, ALERT, SEARCH, CHASE, CATCH }

const PATROL_SPEED := 1.8
const SEARCH_SPEED := 2.8
const CHASE_SPEED := 5.0          # 主人公の全力疾走（5.5）より少し遅い
const HEARING_MULT := 1.0         # 1.0 = 足音の届く距離どおりに聞こえる
const VIEW_RANGE := 7.0           # 立っている主人公が見える距離（しゃがむと6割）
const VIEW_HALF_ANGLE := 55.0     # 視野の半分の角度（度）
const CATCH_RANGE := 1.2
const ALERT_TIME := 1.5           # 物音の方を向いて固まっている時間
const SEARCH_TIME := 9.0          # 捜索を続ける時間
const LOSE_SIGHT_TIME := 3.0      # 追跡中、これだけ見えなければ捜索に切り替える
const LURE_SPEED := 4.2           # 空き缶の音には走って向かう
const LURE_ALERT_TIME := 1.3      # 空き缶の音で吠え終わってから走り出す
const LURE_SEARCH_TIME := 14.0    # 空き缶が落ちた場所を調べ続ける時間

var waypoints: Array = []
var state: int = State.PATROL
var awareness := 0.0              # 0〜100。100で「見つけた」

var _wp := 0
var _target := Vector3.ZERO
var _search_origin := Vector3.ZERO
var _timer := 0.0
var _search_left := 0.0
var _lost_timer := 0.0
var _lured := false               # 空き缶の音を調べに行っている
var _delta := 0.0
var _player: Player
var _agent: NavigationAgent3D
var _eye_mat: StandardMaterial3D
var _dino: DinoModel
var _anim: AnimationPlayer
var _growl_timer := randf_range(3.0, 8.0)
var _stride := 0.0
const STRIDE_LENGTH := 1.1        # この距離ごとに足音が鳴る（メートル）
var _gravity: float = ProjectSettings.get_setting("physics/3d/default_gravity")


func _ready() -> void:
	add_to_group("stalker")

	var cap := CapsuleShape3D.new()
	cap.radius = 0.4
	cap.height = 1.2
	var cs := CollisionShape3D.new()
	cs.shape = cap
	cs.position.y = 0.6
	add_child(cs)
	_build_model()

	_agent = NavigationAgent3D.new()
	_agent.radius = 0.45
	_agent.path_desired_distance = 0.6
	_agent.target_desired_distance = 0.8
	add_child(_agent)

	Game.noise_emitted.connect(_on_noise)
	_set_eye_color()


func _physics_process(delta: float) -> void:
	_delta = delta
	if _player == null:
		_player = get_tree().get_first_node_in_group("player") as Player

	if not is_on_floor():
		velocity.y -= _gravity * delta

	if NavigationServer3D.map_get_iteration_id(_agent.get_navigation_map()) == 0 or waypoints.is_empty():
		move_and_slide()
		return
	if Game.state != Game.State.PLAY and state != State.CATCH:
		_stop()
		move_and_slide()
		return

	var sees := _can_see_player()
	if sees:
		var d := global_position.distance_to(_player.global_position)
		awareness += delta * lerpf(140.0, 40.0, clampf(d / VIEW_RANGE, 0.0, 1.0))
		_target = _player.global_position
	else:
		awareness -= delta * 8.0
	awareness = clampf(awareness, 0.0, 100.0)

	match state:
		State.PATROL:
			_move_to(waypoints[_wp], PATROL_SPEED)
			if _agent.is_navigation_finished():
				_wp = (_wp + 1) % waypoints.size()
			if sees and awareness >= 100.0:
				_enter(State.CHASE)
			elif sees and awareness >= 30.0:
				_enter(State.ALERT)

		State.ALERT:
			_stop()
			_face(_target - global_position)
			_timer -= delta
			if sees and awareness >= 100.0:
				_enter(State.CHASE)
			elif _timer <= 0.0:
				_enter(State.SEARCH)

		State.SEARCH:
			_search_left -= delta
			if sees and awareness >= 100.0:
				_enter(State.CHASE)
			elif _search_left <= 0.0:
				awareness = 0.0
				_enter(State.PATROL)
			elif _agent.is_navigation_finished():
				# 着いたら首を振って辺りを見回し、近くの別の場所へ
				_stop()
				_timer -= delta
				if _timer <= 0.0:
					_timer = 3.0   # "look" の見回し1回ぶん
					_lured = false
					var off := Vector3(randf_range(-4.0, 4.0), 0.0, randf_range(-4.0, 4.0))
					_target = NavigationServer3D.map_get_closest_point(_agent.get_navigation_map(), _search_origin + off)
					_agent.target_position = _target
			else:
				_move_to(_target, LURE_SPEED if _lured else SEARCH_SPEED)

		State.CHASE:
			if sees:
				_lost_timer = 0.0
			else:
				_lost_timer += delta
			_move_to(_target, CHASE_SPEED)
			if _player != null and not _player.is_hidden \
					and global_position.distance_to(_player.global_position) < CATCH_RANGE:
				_enter(State.CATCH)
			elif _lost_timer > LOSE_SIGHT_TIME or (not sees and _agent.is_navigation_finished()):
				_enter(State.SEARCH)

		State.CATCH:
			_stop()
			if _player != null:
				_face(_player.global_position - global_position)

	move_and_slide()
	_animate(delta)


func _animate(delta: float) -> void:
	_play_sounds(delta)
	if _anim != null:
		_update_anim()
	if _dino == null:
		return
	var mood := DinoModel.Mood.CALM
	if state == State.ALERT:
		mood = DinoModel.Mood.ALERT
	elif state == State.SEARCH:
		mood = DinoModel.Mood.SEARCH
	elif state == State.CHASE or state == State.CATCH:
		mood = DinoModel.Mood.CHASE
	_dino.animate(delta, Vector2(velocity.x, velocity.z).length(), mood)


func _enter(new_state: int) -> void:
	var old := state
	state = new_state
	if new_state == State.ALERT and old != State.ALERT:
		Sfx.play_at("snort", global_position + Vector3.UP, -2.0, 18.0)
	elif new_state == State.CHASE and old != State.CHASE:
		Sfx.play_at("screech", global_position + Vector3.UP, 4.0, 45.0)
	match new_state:
		State.ALERT:
			_timer = LURE_ALERT_TIME if _lured else ALERT_TIME
			_play_once("roar")
		State.SEARCH:
			_search_origin = _target
			_search_left = LURE_SEARCH_TIME if _lured else SEARCH_TIME
			_timer = 3.0
			_agent.target_position = _target
		State.PATROL:
			_lured = false
		State.CHASE:
			_lured = false
			_lost_timer = 0.0
			awareness = 100.0
		State.CATCH:
			_play_once("attack")
			Game.player_caught()
	_set_eye_color()


## 足音と、ときどきのうなり声。
func _play_sounds(delta: float) -> void:
	var speed := Vector2(velocity.x, velocity.z).length()
	if is_on_floor() and speed > 0.3:
		_stride += speed * delta
		if _stride >= STRIDE_LENGTH:
			_stride = 0.0
			var vol := -2.0 if state == State.CHASE else -9.0
			Sfx.play_at("dino_step", global_position, vol, 22.0, 0.12)
	_growl_timer -= delta
	if _growl_timer <= 0.0:
		_growl_timer = randf_range(5.0, 11.0)
		if state == State.PATROL or state == State.SEARCH:
			Sfx.play_at("growl", global_position + Vector3.UP * 1.3, -3.0, 30.0, 0.12)


## 物音を聞いたとき。届く範囲内なら、その方向を警戒してから調べに行く。
func _on_noise(pos: Vector3, radius: float, source) -> void:
	if state == State.CHASE or state == State.CATCH or Game.state != Game.State.PLAY:
		return
	if _agent == null or NavigationServer3D.map_get_iteration_id(_agent.get_navigation_map()) == 0:
		return
	var hear := radius * HEARING_MULT
	var d := global_position.distance_to(pos)
	if d > hear:
		return
	var strength := 1.0 - d / hear
	awareness = maxf(awareness, 30.0 + 40.0 * strength)
	_target = NavigationServer3D.map_get_closest_point(_agent.get_navigation_map(), pos)
	# 空き缶の音には強く反応する: 吠えてすぐ走って向かい、長く調べる
	_lured = source is Throwable
	_enter(State.ALERT)


func _can_see_player() -> bool:
	if _player == null or _player.is_hidden:
		return false
	var eye := global_position + Vector3(0, 1.3, 0)
	var tgt := _player.global_position + Vector3(0, 0.6 if _player.is_crouching else 1.2, 0)
	var to := tgt - eye
	var rng := VIEW_RANGE * (0.6 if _player.is_crouching else 1.0)
	if state == State.CHASE:
		rng = VIEW_RANGE * 2.0
	if to.length() > rng:
		return false
	if state != State.CHASE:
		var fwd := -global_transform.basis.z
		var flat_to := Vector3(to.x, 0, to.z).normalized()
		if fwd.angle_to(flat_to) > deg_to_rad(VIEW_HALF_ANGLE):
			return false
	var q := PhysicsRayQueryParameters3D.create(eye, tgt)
	q.exclude = [get_rid()]
	var hit := get_world_3d().direct_space_state.intersect_ray(q)
	return not hit.is_empty() and hit.collider == _player


func _move_to(pos: Vector3, speed: float) -> void:
	if _agent.target_position.distance_to(pos) > 0.3:
		_agent.target_position = pos
	if _agent.is_navigation_finished():
		_stop()
		return
	var next := _agent.get_next_path_position()
	var dir := next - global_position
	dir.y = 0.0
	if dir.length() > 0.05:
		dir = dir.normalized()
		velocity.x = dir.x * speed
		velocity.z = dir.z * speed
		_face(dir)


func _stop() -> void:
	velocity.x = 0.0
	velocity.z = 0.0


func _face(dir: Vector3) -> void:
	dir.y = 0.0
	if dir.length() < 0.01:
		return
	rotation.y = lerp_angle(rotation.y, atan2(-dir.x, -dir.z), 8.0 * _delta)


func _set_eye_color() -> void:
	if _eye_mat == null:
		return
	var c := Color(0.9, 0.8, 0.2)
	if state == State.ALERT or state == State.SEARCH:
		c = Color(1.0, 0.5, 0.1)
	elif state == State.CHASE or state == State.CATCH:
		c = Color(1.0, 0.1, 0.05)
	_eye_mat.albedo_color = c
	_eye_mat.emission = c


## Blenderで作った恐竜のモデル。あれば箱の仮モデルの代わりに使う。
## 頭が -Z（Blenderでは +Y）向き、足元が原点、全長約2.3m・頭の高さ約1.4mが目安。
## アニメーション（tools/blender/stalker.py）: idle walk run look は繰り返し、roar attack は1回。
const MODEL_PATH := "res://assets/models/stalker.glb"
const WALK_ANIM_SPEED := 1.2   # "walk" を速さ1で再生したときに進む速さ（m/秒）
const RUN_ANIM_SPEED := 4.8    # "run" を速さ1で再生したときに進む速さ（m/秒）
const LOOPS := ["idle", "walk", "run", "look"]


## 今の状態と速さに合う動きを選ぶ。吠える・噛みつく間はそれが終わるまで待つ。
func _update_anim() -> void:
	if _anim.current_animation in ["roar", "attack"] and _anim.is_playing() and state != State.CHASE:
		return   # 吠えている途中に見つけたら、すぐ走り出す
	if state == State.CATCH:
		return
	var speed := Vector2(velocity.x, velocity.z).length()
	if speed > 3.0:
		_loop("run", speed / RUN_ANIM_SPEED)
	elif speed > 0.1:
		_loop("walk", speed / WALK_ANIM_SPEED)
	elif state == State.SEARCH or state == State.ALERT:
		_loop("look", 1.0)
	else:
		_loop("idle", 1.0)


func _loop(anim_name: String, speed_scale: float) -> void:
	if not _anim.has_animation(anim_name):
		return
	if _anim.current_animation != anim_name:
		_anim.play(anim_name, 0.25)
	_anim.speed_scale = clampf(speed_scale, 0.5, 2.0)


func _play_once(anim_name: String) -> void:
	if _anim == null or not _anim.has_animation(anim_name):
		return
	_anim.speed_scale = 1.0
	_anim.play(anim_name, 0.15)


## 仮モデル（scripts/dino_model.gd）。頭は -Z（前）向き。
func _build_model() -> void:
	if ResourceLoader.exists(MODEL_PATH):
		var scene := load(MODEL_PATH) as PackedScene
		if scene != null:
			var model := scene.instantiate()
			add_child(model)
			_anim = model.find_child("AnimationPlayer", true, false) as AnimationPlayer
			if _anim != null:
				for a in LOOPS:
					if _anim.has_animation(a):
						_anim.get_animation(a).loop_mode = Animation.LOOP_LINEAR
				_loop("idle", 1.0)
			return
	_eye_mat = StandardMaterial3D.new()
	_eye_mat.emission_enabled = true
	_eye_mat.emission_energy_multiplier = 3.0
	_dino = DinoModel.new()
	_dino.eye_mat = _eye_mat
	add_child(_dino)
