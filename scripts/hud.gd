class_name Hud
extends CanvasLayer
## 画面表示: 足音メーター、持ち物、恐竜の気配、ヒント、捕まった／クリア画面。

var player: Player

var _pulse: ColorRect
var _fade: ColorRect
var _status: Label
var _threat: Label
var _prompt: Label
var _hint: Label
var _center: Label
var _hint_time := 0.0
var _t := 0.0

const THREAT_TEXT := ["", "……何かの気配がする", "何かを探している……動くな", "見つかった！ 隠れろ！"]
const THREAT_ALPHA := [0.0, 0.04, 0.10, 0.22]


func _ready() -> void:
	_pulse = _rect(Color(0.6, 0.0, 0.0, 0.0))
	_status = _label(20, HORIZONTAL_ALIGNMENT_LEFT, VERTICAL_ALIGNMENT_TOP)
	_status.offset_left = 24
	_status.offset_top = 20
	_threat = _label(30, HORIZONTAL_ALIGNMENT_CENTER, VERTICAL_ALIGNMENT_TOP)
	_threat.offset_top = 30
	_prompt = _label(24, HORIZONTAL_ALIGNMENT_CENTER, VERTICAL_ALIGNMENT_BOTTOM)
	_prompt.offset_bottom = -120
	_hint = _label(22, HORIZONTAL_ALIGNMENT_CENTER, VERTICAL_ALIGNMENT_BOTTOM)
	_hint.offset_bottom = -50
	var cross := _label(18, HORIZONTAL_ALIGNMENT_CENTER, VERTICAL_ALIGNMENT_CENTER)
	cross.text = "・"
	_fade = _rect(Color(0, 0, 0, 0))
	_center = _label(40, HORIZONTAL_ALIGNMENT_CENTER, VERTICAL_ALIGNMENT_CENTER)
	Game.hint_requested.connect(_on_hint)


func _process(delta: float) -> void:
	if player == null:
		return

	var bars := int(round(clampf(player.noise_level / Player.NOISE_SPRINT, 0.0, 1.0) * 10.0))
	_status.text = "足音　%s\n空き缶　%d\nカードキー　%s\n懐中電灯（F）　%s" % [
		"■".repeat(bars) + "□".repeat(10 - bars),
		player.ammo,
		"あり" if Game.has_keycard else "なし",
		"ON" if player.flashlight_on() else "OFF",
	]

	var level := 0
	for s in get_tree().get_nodes_in_group("stalker"):
		var d: float = s.global_position.distance_to(player.global_position)
		if s.state == Stalker.State.CHASE or s.state == Stalker.State.CATCH:
			level = 3
		elif s.state == Stalker.State.ALERT or s.state == Stalker.State.SEARCH:
			level = maxi(level, 2)
		elif d < 9.0:
			level = maxi(level, 1)
	_threat.text = THREAT_TEXT[level]
	_threat.modulate = Color(1, 0.3, 0.25) if level == 3 else Color(1, 1, 1, 0.85)
	_t += delta * (2.0 + level * 2.5)
	_pulse.color.a = THREAT_ALPHA[level] * (0.6 + 0.4 * sin(_t))

	_prompt.text = ""
	if Game.state == Game.State.PLAY and player.focus != null and is_instance_valid(player.focus) \
			and player.focus.has_method("get_prompt"):
		_prompt.text = player.focus.get_prompt(player)

	_hint_time -= delta
	_hint.modulate.a = clampf(_hint_time, 0.0, 1.0)

	var fade_to := 0.0
	match Game.state:
		Game.State.CAUGHT:
			fade_to = 1.0
			_center.text = "捕まった……"
		Game.State.CLEAR:
			fade_to = 0.75
			_center.text = "脱出成功！\n体験版プロトタイプはここまで\n\nRキーで最初から"
		_:
			_center.text = ""
	_fade.color.a = move_toward(_fade.color.a, fade_to, delta * 1.5)


func _on_hint(text: String) -> void:
	_hint.text = text
	_hint_time = 6.0


func _rect(c: Color) -> ColorRect:
	var r := ColorRect.new()
	r.color = c
	r.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(r)
	r.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	return r


func _label(font_size: int, h: HorizontalAlignment, v: VerticalAlignment) -> Label:
	var l := Label.new()
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	l.horizontal_alignment = h
	l.vertical_alignment = v
	l.add_theme_font_size_override("font_size", font_size)
	l.add_theme_constant_override("outline_size", 6)
	l.add_theme_color_override("font_outline_color", Color.BLACK)
	add_child(l)
	l.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	return l
