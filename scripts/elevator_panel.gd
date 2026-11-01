class_name ElevatorPanel
extends Node3D
## エレベーターの呼び出しボタン。電源が戻っていれば呼べるが、着くまで ARRIVE_TIME 秒かかる。
## 呼ぶ音で恐竜が寄ってくるので、到着までホールで隠れて耐える（企画書のクライマックス）。

const ARRIVE_TIME := 20.0
const CALL_NOISE := 18.0

var waiting := false
var time_left := 0.0
var _lamp: StandardMaterial3D


func _ready() -> void:
	add_to_group("interactable")
	_lamp = StandardMaterial3D.new()
	_lamp.albedo_color = Color(0.3, 0.3, 0.3)
	_lamp.emission_enabled = true
	_lamp.emission = Color(0, 0, 0)
	var mi := MeshInstance3D.new()
	var bm := BoxMesh.new()
	bm.size = Vector3(0.18, 0.3, 0.06)
	mi.mesh = bm
	mi.material_override = _lamp
	mi.position.y = 1.3
	add_child(mi)
	Game.power_restored.connect(func():
		_lamp.albedo_color = Color(0.2, 0.9, 0.3)
		_lamp.emission = Color(0.2, 0.9, 0.3))


func get_prompt(_player) -> String:
	if waiting:
		return "エレベーター到着まで %d 秒" % ceili(time_left)
	return "E: エレベーターを呼ぶ" if Game.power_on else "電源が来ていない（監視室で非常電源を入れる）"


func interact(_player) -> void:
	if waiting:
		return
	if not Game.power_on:
		Sfx.play("pickup", -14.0, 0.5)
		Game.show_hint("動かない……監視室で非常電源を入れないと")
		return
	waiting = true
	time_left = ARRIVE_TIME
	Sfx.play_at("elevator", global_position, -6.0, 30.0, 0.0)
	Game.emit_noise(global_position, CALL_NOISE, self)
	Game.show_hint("エレベーターが降りてくる……着くまで %d 秒、見つかるな" % int(ARRIVE_TIME))


func _process(delta: float) -> void:
	if not waiting or Game.state != Game.State.PLAY:
		return
	time_left -= delta
	if time_left <= 0.0:
		waiting = false
		var player := get_tree().get_first_node_in_group("player") as Node3D
		if player != null and player.global_position.distance_to(global_position) < 6.0:
			Game.clear_game()
		else:
			Game.show_hint("扉が開いた！ 乗り込め")
			waiting = true
			time_left = 999.0
			_open_wait()


## ホールの外にいたら、戻ってくるまで扉を開けて待つ。
func _open_wait() -> void:
	while is_inside_tree() and Game.state == Game.State.PLAY:
		var player := get_tree().get_first_node_in_group("player") as Node3D
		if player != null and player.global_position.distance_to(global_position) < 6.0:
			Game.clear_game()
			return
		await get_tree().create_timer(0.2).timeout
