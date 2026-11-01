extends Node
## ゲーム全体の状態を持つオートロード（Game）。
## 入力設定、物音の通知、チェックポイント、捕まった／クリアの管理をする。

signal noise_emitted(pos: Vector3, radius: float, source)
signal hint_requested(text: String)
signal state_changed(state: int)

enum State { PLAY, CAUGHT, CLEAR }

## チェックポイント: 0 = 観察室、1 = 飼育通路の入口、2 = 給餌室の入口
const CHECKPOINTS := [Vector3(0, 0.1, -2), Vector3(-1.2, 0.1, -9.5), Vector3(0, 0.1, -39.5)]

var state: int = State.PLAY
var checkpoint := 0
var has_keycard := false
## 水たまりの範囲（XZ平面の Rect2）。踏むと足音が大きくなる。
var puddles: Array = []


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	_setup_input()


## 物音を出す。radius は「この距離まで聞こえる」メートル数。
func emit_noise(pos: Vector3, radius: float, source = null) -> void:
	noise_emitted.emit(pos, radius, source)


func show_hint(text: String) -> void:
	hint_requested.emit(text)


func is_in_puddle(pos: Vector3) -> bool:
	for r in puddles:
		if r.has_point(Vector2(pos.x, pos.z)):
			return true
	return false


func reach_checkpoint(index: int) -> void:
	if index > checkpoint:
		checkpoint = index


func player_caught() -> void:
	if state != State.PLAY:
		return
	state = State.CAUGHT
	state_changed.emit(state)
	Sfx.play("caught", -2.0)
	await get_tree().create_timer(2.5).timeout
	restart()


func clear_game() -> void:
	if state != State.PLAY:
		return
	state = State.CLEAR
	state_changed.emit(state)
	Sfx.play("elevator", -4.0)
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE


## full = true なら最初から、false なら最後のチェックポイントから。
func restart(full := false) -> void:
	if full:
		checkpoint = 0
	has_keycard = false
	puddles.clear()
	state = State.PLAY
	get_tree().reload_current_scene()


func _unhandled_input(event: InputEvent) -> void:
	if state == State.CLEAR and event.is_action_pressed("restart"):
		restart(true)


# --- 入力設定 ---------------------------------------------------------------
# project.godot に書くと読みにくいので、起動時にコードで登録する。

func _setup_input() -> void:
	_add_action("move_forward", [KEY_W, KEY_UP], [], [], [[JOY_AXIS_LEFT_Y, -1.0]])
	_add_action("move_back", [KEY_S, KEY_DOWN], [], [], [[JOY_AXIS_LEFT_Y, 1.0]])
	_add_action("move_left", [KEY_A, KEY_LEFT], [], [], [[JOY_AXIS_LEFT_X, -1.0]])
	_add_action("move_right", [KEY_D, KEY_RIGHT], [], [], [[JOY_AXIS_LEFT_X, 1.0]])
	_add_action("sprint", [KEY_SHIFT], [], [JOY_BUTTON_LEFT_STICK])
	_add_action("crouch", [KEY_CTRL, KEY_C], [], [JOY_BUTTON_B])
	_add_action("interact", [KEY_E], [], [JOY_BUTTON_A])
	_add_action("throw", [], [MOUSE_BUTTON_LEFT], [], [[JOY_AXIS_TRIGGER_RIGHT, 1.0]])
	_add_action("flashlight", [KEY_F], [], [JOY_BUTTON_Y])
	_add_action("pause", [KEY_ESCAPE], [], [JOY_BUTTON_START])
	_add_action("restart", [KEY_R], [], [JOY_BUTTON_BACK])


func _add_action(action: String, keys: Array, mouse_buttons := [], joy_buttons := [], joy_axes := []) -> void:
	if InputMap.has_action(action):
		return
	InputMap.add_action(action, 0.25)
	for k in keys:
		var e := InputEventKey.new()
		e.physical_keycode = k
		InputMap.action_add_event(action, e)
	for b in mouse_buttons:
		var e := InputEventMouseButton.new()
		e.button_index = b
		InputMap.action_add_event(action, e)
	for b in joy_buttons:
		var e := InputEventJoypadButton.new()
		e.button_index = b
		InputMap.action_add_event(action, e)
	for a in joy_axes:
		var e := InputEventJoypadMotion.new()
		e.axis = a[0]
		e.axis_value = a[1]
		InputMap.action_add_event(action, e)
