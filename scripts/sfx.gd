extends Node
## 効果音を鳴らすオートロード（Sfx）。音は tools/make_sounds.py で合成したもの。
##   Sfx.play_at("growl", 位置)   … その場所から聞こえる立体音
##   Sfx.play("pickup")            … 画面全体に聞こえる音

const DIR := "res://assets/sounds/"
const NAMES := ["step", "step_wet", "locker", "can", "pickup", "door", "heartbeat", "caught", "thunder", "alarm",
		"bang", "break", "slam",
		"elevator", "dino_step", "growl", "snort", "screech", "ambience"]

var _streams := {}
var played := 0               # 鳴らした回数（自動テスト用）


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	for n in NAMES:
		var path: String = DIR + n + ".wav"
		if ResourceLoader.exists(path):
			_streams[n] = load(path)


## 3D 空間の pos から鳴らす。max_distance より遠いと聞こえない。
func play_at(sound: String, pos: Vector3, volume_db := 0.0, max_distance := 25.0, pitch_spread := 0.08) -> void:
	if not _streams.has(sound):
		return
	var scene := get_tree().current_scene
	if scene == null:
		return
	var p := AudioStreamPlayer3D.new()
	p.stream = _streams[sound]
	p.volume_db = volume_db
	p.max_distance = max_distance
	p.unit_size = 4.0
	p.pitch_scale = randf_range(1.0 - pitch_spread, 1.0 + pitch_spread)
	p.attenuation_filter_cutoff_hz = 3000.0   # 遠いほどこもって聞こえる
	scene.add_child(p)
	p.global_position = pos
	p.finished.connect(p.queue_free)
	p.play()
	played += 1


## 位置に関係なく鳴らす（UI、心拍など）。
func play(sound: String, volume_db := 0.0, pitch := 1.0) -> AudioStreamPlayer:
	if not _streams.has(sound):
		return null
	var p := AudioStreamPlayer.new()
	p.stream = _streams[sound]
	p.volume_db = volume_db
	p.pitch_scale = pitch
	add_child(p)
	p.finished.connect(p.queue_free)
	p.play()
	played += 1
	return p


## 繰り返し鳴らし続ける音（環境音）。止めるときは戻り値を queue_free する。
func loop(sound: String, volume_db := 0.0) -> AudioStreamPlayer:
	if not _streams.has(sound):
		return null
	var p := AudioStreamPlayer.new()
	p.stream = _streams[sound]
	p.volume_db = volume_db
	get_tree().current_scene.add_child(p)
	p.finished.connect(p.play)
	p.play()
	return p
