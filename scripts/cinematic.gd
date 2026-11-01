class_name Cinematic
extends Node
## ゲーム内のカメラで撮る映像（プロローグと、ステージ開始時の恐竜の紹介）。
## 上下に黒い帯を出し、字幕を流す。Space / E / Esc / Aボタンで飛ばせる。
## 台本は docs/story.md と同じ内容。

signal finished

const LETTERBOX := 90.0          # 上下の黒帯の高さ（ピクセル）

var level: Node                  # level.gd（照明の切り替えや恐竜を使う）
var _cam: Camera3D
var _layer: CanvasLayer
var _top: ColorRect
var _bottom: ColorRect
var _flash: ColorRect
var _black: ColorRect
var _sub: Label
var _title: Label
var _skip_hint: Label
var _skipped := false
var _tween: Tween


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	_cam = Camera3D.new()
	_cam.fov = 55
	add_child(_cam)
	_layer = CanvasLayer.new()
	_layer.layer = 10
	add_child(_layer)
	_black = _rect(Color(0, 0, 0, 1))
	_top = _rect(Color.BLACK)
	_bottom = _rect(Color.BLACK)
	_top.set_anchors_and_offsets_preset(Control.PRESET_TOP_WIDE)
	_top.offset_bottom = LETTERBOX
	_bottom.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_WIDE)
	_bottom.offset_top = -LETTERBOX
	_flash = _rect(Color(1, 1, 1, 0))
	_sub = _label(26)
	_sub.vertical_alignment = VERTICAL_ALIGNMENT_BOTTOM
	_sub.offset_bottom = -LETTERBOX - 24
	_title = _label(34)
	_skip_hint = _label(16)
	_skip_hint.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	_skip_hint.vertical_alignment = VERTICAL_ALIGNMENT_BOTTOM
	_skip_hint.offset_right = -24
	_skip_hint.offset_bottom = -24
	_skip_hint.text = "Space：スキップ"
	_skip_hint.modulate.a = 0.6


func _unhandled_input(event: InputEvent) -> void:
	if _skipped:
		return
	if event.is_action_pressed("interact") or event.is_action_pressed("pause") \
			or (event is InputEventKey and event.pressed and event.physical_keycode == KEY_SPACE):
		_skipped = true
		get_viewport().set_input_as_handled()


## プロローグ（初回だけ）と恐竜の紹介を流してから、操作できる状態に戻す。
func play(prologue: bool) -> void:
	Game.state = Game.State.INTRO
	_cam.make_current()
	if prologue:
		await _prologue()
	_skipped = false
	await _intro()
	await _fade_black(1.0, 0.4)
	_cam.clear_current(false)
	level.player.camera.make_current()
	level.set_power_look(false)
	Game.state = Game.State.PLAY
	Game.prologue_seen = true
	await _fade_black(0.0, 0.6)
	_layer.visible = false
	finished.emit()


# --- プロローグ -----------------------------------------------------------------

func _prologue() -> void:
	level.set_power_look(true)        # 停電前: 白い照明
	_black.color.a = 1.0
	await _card("20XX年11月　嵐の夜\n\n北アルプスの山奥　ヘリオス製薬 第三研究所", 4.5)
	if _skipped: return
	await _card("表向きは新薬の研究施設。\nだが地下5階では、ある“生き物”が飼われていた。", 4.5)
	if _skipped: return

	# 明るい飼育通路を奥へ進むカメラ
	_shot(Vector3(0, 2.6, -9), Vector3(0, 1.4, -20), Vector3(0, 2.2, -12.5), Vector3(0, 1.2, -24), 6.0)
	await _fade_black(0.0, 1.0)
	await _say("研究コード S-07。\n6500万年前に絶滅したはずの、小型の捕食者。", 5.0)
	if _skipped: return

	# ケージの中で眠る恐竜
	var s := level.stalker as Node3D
	_shot(s.global_position + Vector3(-2.4, 1.0, 1.6), s.global_position + Vector3(0, 0.8, 0),
		s.global_position + Vector3(-2.0, 0.9, 0.9), s.global_position + Vector3(0, 0.9, 0), 5.0)
	await _say("名前は付けられていない。\n職員たちは、ただ「ストーカー」と呼んでいた。", 5.0)
	if _skipped: return

	# 落雷と停電
	Sfx.play("thunder", 2.0)
	await _lightning()
	level.set_power_look(false)
	_shot(Vector3(0, 2.8, -10), Vector3(2.0, 1.2, -14), Vector3(0.2, 2.6, -10.4), Vector3(2.0, 1.0, -14), 5.0)
	await _say("落雷。主電源が落ち、非常電源に切り替わった、その瞬間——", 3.5)
	if _skipped: return
	Sfx.play("alarm", -10.0)
	await _say("すべてのケージの電子ロックが、外れた。", 3.5)
	if _skipped: return

	# 観察室で目を覚ます主人公
	var p := level.player as Node3D
	_shot(p.global_position + Vector3(1.6, 1.2, -2.2), p.global_position + Vector3(0, 1.3, 0),
		p.global_position + Vector3(1.0, 1.5, -1.6), p.global_position + Vector3(0, 1.4, 0), 6.5)
	await _say("新人研究員・朝霧ハル。配属三日目の夜勤だった。", 3.0)
	if _skipped: return
	Sfx.play("pickup", -12.0, 0.6)
	await _say("無線『……ハル、聞こえるか。九条だ。\n監視室で非常電源を入れろ。エレベーターはそれで動く』", 4.5)
	if _skipped: return
	await _say("無線『いいか、音を立てるな。あいつは目が悪いが……耳がいい』", 4.0)


# --- ステージ開始時の恐竜の紹介 -----------------------------------------------------------

func _intro() -> void:
	var s := level.stalker as Node3D
	var head := s.global_position + Vector3(0, 1.35, 0)
	var fwd := -s.global_transform.basis.z
	var side := s.global_transform.basis.x
	_black.color.a = 0.0
	_flash.color.a = 0.0
	_shot(head + fwd * 1.6 + side * 0.5, head, head + fwd * 1.1 + side * 0.2 + Vector3(0, -0.1, 0), head, 3.5)
	_title.text = ""
	_sub.text = ""
	level.stalker.call("_play_once", "roar")
	Sfx.play_at("screech", head, 0.0, 30.0)
	await _wait(1.2)
	_title.text = "S-07「ストーカー」"
	await _say("目はほとんど見えない。そのかわり、耳が鋭い。\n足音や物音のした方へ、すぐにやって来る。", 4.0)
	_title.text = ""
	if _skipped: return
	_shot(head + fwd * 2.4 + side * 1.6 + Vector3(0, 0.3, 0), head, head + fwd * 2.8 + side * 1.0 + Vector3(0, 0.5, 0), head, 9.0)
	await _say("しゃがめば（Ctrl）足音は小さくなる。水たまりや走る音は遠くまで届く。", 3.5)
	if _skipped: return
	await _say("空き缶を投げれば（左クリック）、その音の方へ走っていく。", 3.0)
	if _skipped: return
	await _say("ロッカーに隠れ、扉を閉めれば（E）しばらくは持ちこたえられる。", 3.0)
	if _skipped: return
	await _say("目指すのは監視室の非常電源、そしてエレベーター。", 3.0)


# --- 部品 ----------------------------------------------------------------------

## from の位置・視点から to へ duration 秒かけて動くカメラ。
func _shot(from: Vector3, look_from: Vector3, to: Vector3, look_to: Vector3, duration: float) -> void:
	if _tween != null:
		_tween.kill()
	_cam.global_position = from
	_cam.look_at(look_from)
	_tween = create_tween()
	_tween.tween_method(func(t: float):
		_cam.global_position = from.lerp(to, t)
		_cam.look_at(look_from.lerp(look_to, t)), 0.0, 1.0, duration).set_trans(Tween.TRANS_SINE)


## 黒い画面に文字だけを出す。
func _card(text: String, sec: float) -> void:
	_black.color.a = 1.0
	_title.text = text
	_title.modulate.a = 0.0
	var tw := create_tween()
	tw.tween_property(_title, "modulate:a", 1.0, 0.8)
	await _wait(sec)
	var tw2 := create_tween()
	tw2.tween_property(_title, "modulate:a", 0.0, 0.6)
	await _wait(0.6)
	_title.text = ""
	_title.modulate.a = 1.0


func _say(text: String, sec: float) -> void:
	_sub.text = text
	await _wait(sec)
	_sub.text = ""


func _lightning() -> void:
	for a in [1.0, 0.0, 0.8, 0.0]:
		_flash.color.a = a
		await _wait(0.08)
	await _fade_black(1.0, 0.15)
	await _wait(0.8)
	await _fade_black(0.0, 0.6)


func _fade_black(to: float, sec: float) -> void:
	var tw := create_tween()
	tw.tween_property(_black, "color:a", to, sec)
	await tw.finished


## スキップされたらすぐ戻る待ち時間。
func _wait(sec: float) -> void:
	var t := 0.0
	while t < sec and not _skipped:
		await get_tree().process_frame
		t += get_process_delta_time()


func _rect(c: Color) -> ColorRect:
	var r := ColorRect.new()
	r.color = c
	r.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_layer.add_child(r)
	r.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	return r


func _label(font_size: int) -> Label:
	var l := Label.new()
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	l.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	l.add_theme_font_size_override("font_size", font_size)
	l.add_theme_constant_override("outline_size", 8)
	l.add_theme_color_override("font_outline_color", Color.BLACK)
	_layer.add_child(l)
	l.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	return l
