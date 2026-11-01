extends Node3D
## エリア1（B5 飼育ケージ区画）を箱だけで組み立てる。
## 見た目は後で Blender MCP で作ったモデルに差し替える前提で、
## いまは「遊んで怖いか・楽しいか」を確かめるための配置だけを作る。
##
## 部屋（上から見て、-Z が北＝奥）:
##   観察室     x -5..5,  z 0..-8     スタート。ガラス越しに通路が見える
##   飼育通路   x -2..2,  z -8..-38   左右にケージ。ストーカー1匹
##   給餌室     x -8..8,  z -38..-54  カードキー。ストーカー2匹目
##   出口       x -3..3,  z -54..-60  ここまで来たらクリア

const H := 3.5          # 天井の高さ
const T := 0.3          # 壁の厚さ
const CAGES := [-14.0, -22.0, -30.0]   # ケージの中心 z
const CAGE_HALF := 2.5
const GOAL_Z := -57.0

# 明るさの調整用。暗い・明るいと感じたらここを変える。
const AMBIENT_ENERGY := 0.6                  # 部屋全体のうっすらした明るさ
const EMERGENCY_COLOR := Color(1.0, 0.38, 0.3)   # 非常灯の色（真っ赤より少し白っぽく）
const LIGHT_BOOST := 2.2                     # 照明の明るさの倍率
const LIGHT_RANGE_ADD := 3.0                 # 照明の届く距離に足すメートル数

var nav: NavigationRegion3D   # この下に置いた物から恐竜の通れる道（ナビメッシュ）を作る
var outside: Node3D           # ナビメッシュに含めない物（天井、扉、出口）
var player: Player
var hud: Hud
var _hint_stage := 0
var _room := ""               # いま組み立て中の部屋（Blenderモデルとの差し替え用の目印）

## Blenderで作った部屋のモデル（.glb）を置く場所。
## ここに observation.glb などがあれば、その部屋の箱の見た目を隠してモデルを表示する。
## 当たり判定と恐竜の通れる道は箱のまま使う。作り方は docs/blender-guide.md を参照。
const ROOM_MODEL_DIR := "res://assets/models/rooms/"
const ROOMS := ["observation", "corridor", "feeding", "exit"]

var m_concrete: StandardMaterial3D
var m_panel: StandardMaterial3D
var m_floor: StandardMaterial3D
var m_floor_new: StandardMaterial3D
var m_glass: StandardMaterial3D
var m_bars: StandardMaterial3D
var m_furniture: StandardMaterial3D
var m_puddle: StandardMaterial3D
var m_ceiling: StandardMaterial3D


func _ready() -> void:
	_make_materials()
	_make_environment()

	nav = NavigationRegion3D.new()
	var nm := NavigationMesh.new()
	nm.agent_radius = 0.5
	nm.agent_height = 1.5
	nm.agent_max_climb = 0.25
	nm.geometry_parsed_geometry_type = NavigationMesh.PARSED_GEOMETRY_STATIC_COLLIDERS
	nav.navigation_mesh = nm
	add_child(nav)
	outside = Node3D.new()
	add_child(outside)

	_room = "observation"
	_build_observation_room()
	_room = "corridor"
	_build_corridor()
	_room = "feeding"
	_build_feeding_room()
	_room = "exit"
	_build_exit()
	_room = ""
	_box(outside, Vector3(0, H + 0.15, -30), Vector3(20, 0.3, 64), m_ceiling)
	nav.bake_navigation_mesh(false)
	_apply_room_models()

	_spawn_player()
	_spawn_stalkers()
	_spawn_items()

	hud = Hud.new()
	hud.player = player
	add_child(hud)

	if not _is_selftest():
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
	Game.show_hint("停電だ……。WASDで移動、マウスで視点、Ctrlでしゃがむ（足音が小さくなる）")

	if _is_selftest():
		_selftest()


func _process(_delta: float) -> void:
	if player == null:
		return
	var z := player.global_position.z
	if z < -8.5:
		Game.reach_checkpoint(1)
		_hint_once(1, "水たまりを踏むと足音が大きくなる。空き缶を投げれば恐竜の注意をそらせる")
	if z < -38.5:
		Game.reach_checkpoint(2)
		_hint_once(2, "北の扉はカードキーでロックされている。冷蔵庫やロッカーには E で隠れられる")
	if z < GOAL_Z and Game.state == Game.State.PLAY:
		Game.clear_game()


func _hint_once(stage: int, text: String) -> void:
	if stage > _hint_stage:
		_hint_stage = stage
		Game.show_hint(text)


# --- 部屋 ---------------------------------------------------------------------

func _build_observation_room() -> void:
	_floor(nav, -5, 5, 0, -8, m_floor_new)
	_wall_x(nav, 0, -5, 5, m_panel)
	_wall_z(nav, -5, 0, -8, m_panel)
	_wall_z(nav, 5, 0, -8, m_panel)
	# 北の壁: 西側は壁、x -1.85..0.6 が扉の穴（恐竜も通れる幅）、x 0.8..1.85 が通路を見下ろす窓
	_wall_x(nav, -8, -5, -2, m_panel)
	_wall_x(nav, -8, 0.6, 0.8, m_panel, 0.0)
	_wall_x(nav, -8, 2, 5, m_panel)
	_box(nav, Vector3(1.32, 0.5, -8), Vector3(1.05, 1.0, T), m_panel)                # 窓の下の腰壁
	_box(nav, Vector3(1.32, 1.0 + (H - 1.0) / 2.0, -8), Vector3(1.05, H - 1.0, 0.08), m_glass)
	# 机と観測用コンソール
	_box(nav, Vector3(-3, 0.4, -3), Vector3(2, 0.8, 1), m_furniture)
	_box(nav, Vector3(2.8, 0.6, -6.9), Vector3(2.4, 1.2, 0.8), m_furniture)
	_light(Vector3(0, 3.0, -4), EMERGENCY_COLOR, 1.2, 8.0, false)


func _build_corridor() -> void:
	_floor(nav, -2, 2, -8, -38, m_floor)
	for s in [-1.0, 1.0]:
		var x: float = 2.0 * s
		var z_prev := -8.0
		for c in CAGES:
			_wall_z(nav, x, z_prev, c + CAGE_HALF, m_concrete, 0.0)
			z_prev = c - CAGE_HALF
			_build_cage(x, s, c)
		_wall_z(nav, x, z_prev, -38, m_concrete, 0.0)

	# 通路のロッカー（ケージとケージの間の壁際）
	_hiding_spot(Vector3(-1.65, 1.0, -18), Vector3(0.6, 2.0, 0.9), "ロッカー", Color(0.3, 0.36, 0.4))
	_hiding_spot(Vector3(1.65, 1.0, -26), Vector3(0.6, 2.0, 0.9), "ロッカー", Color(0.3, 0.36, 0.4))
	# 西側の奥のケージに積まれた木箱
	_box(nav, Vector3(-4.2, 0.5, -31), Vector3(1, 1, 1), m_furniture)
	# 漏水の水たまり（端を0.5mずつ残して、しゃがんで避けられるようにしている）
	_puddle(Rect2(-1.5, -24, 3, 3))

	for z in [-12.0, -28.0]:
		_light(Vector3(0, 3.0, z), EMERGENCY_COLOR, 1.2, 7.0, false)
	for z in [-20.0, -36.0]:
		_light(Vector3(0, 3.0, z), EMERGENCY_COLOR, 1.2, 7.0, true)


## 片側のケージ。通路側は鉄格子で、真ん中の格子が壊れて出入りできる。
func _build_cage(x: float, s: float, c: float) -> void:
	var back := 5.0 * s
	_floor(nav, minf(x, back), maxf(x, back), c + CAGE_HALF, c - CAGE_HALF, m_floor)
	_wall_z(nav, back, c + CAGE_HALF, c - CAGE_HALF, m_concrete)
	_wall_x(nav, c + CAGE_HALF, x, back, m_concrete)
	_wall_x(nav, c - CAGE_HALF, x, back, m_concrete)
	var z := c - CAGE_HALF + 0.2
	while z < c + CAGE_HALF - 0.1:
		if absf(z - c) > 0.8:
			_box(nav, Vector3(x, H / 2.0, z), Vector3(0.08, H, 0.08), m_bars)
		z += 0.35


func _build_feeding_room() -> void:
	_floor(nav, -8, 8, -38, -54, m_floor_new)
	_wall_x(nav, -38, -8, -2, m_panel, 0.0)
	_wall_x(nav, -38, 2, 8, m_panel, 0.0)
	_wall_z(nav, -8, -38, -54, m_panel)
	_wall_z(nav, 8, -38, -54, m_panel)
	_wall_x(nav, -54, -8, -1, m_panel)
	_wall_x(nav, -54, 1, 8, m_panel)

	# 机、棚
	_box(nav, Vector3(-4, 0.45, -44), Vector3(3, 0.9, 1.2), m_furniture)
	_box(nav, Vector3(4, 0.45, -44), Vector3(3, 0.9, 1.2), m_furniture)
	_box(nav, Vector3(-4, 0.45, -51), Vector3(3, 0.9, 1.2), m_furniture)
	_box(nav, Vector3(-7.45, 1.2, -47), Vector3(0.8, 2.4, 4), m_furniture)
	# 隠れ場所
	_hiding_spot(Vector3(7.25, 1.1, -50), Vector3(1.2, 2.2, 1.4), "冷蔵庫", Color(0.75, 0.78, 0.8))
	_hiding_spot(Vector3(-7.55, 1.0, -41), Vector3(0.6, 2.0, 0.9), "ロッカー", Color(0.3, 0.36, 0.4))
	_puddle(Rect2(-2, -48, 4, 3))

	# 北の扉（カードキー）。扉は動くので、ナビメッシュの外に置く
	var door := LockedDoor.new()
	door.size = Vector3(2.0, H, 0.2)
	door.position = Vector3(0, H / 2.0, -54)
	var reader := StandardMaterial3D.new()
	reader.albedo_color = Color(1.0, 0.15, 0.1)
	reader.emission_enabled = true
	reader.emission = Color(1.0, 0.15, 0.1)
	reader.emission_energy_multiplier = 2.0
	door.reader_mat = reader
	outside.add_child(door)
	_box(outside, Vector3(1.4, 1.3, -53.75), Vector3(0.2, 0.3, 0.06), reader, false)

	_light(Vector3(-4, 3.0, -42), EMERGENCY_COLOR, 1.3, 8.0, false)
	_light(Vector3(4, 3.0, -50), EMERGENCY_COLOR, 1.3, 8.0, true)


func _build_exit() -> void:
	_floor(outside, -3, 3, -54, -60, m_floor_new)
	_wall_z(outside, -3, -54, -60, m_panel)
	_wall_z(outside, 3, -54, -60, m_panel)
	_wall_x(outside, -60, -3, 3, m_panel)
	_box(outside, Vector3(0, 1.5, -59.8), Vector3(2, 3, 0.1), m_bars)   # エレベーターの扉（仮）
	_light(Vector3(0, 3.0, -57), Color(0.9, 0.95, 1.0), 2.0, 6.0, false)


# --- 登場物 ---------------------------------------------------------------------

func _spawn_player() -> void:
	player = Player.new()
	player.position = Game.CHECKPOINTS[Game.checkpoint]
	add_child(player)


func _spawn_stalkers() -> void:
	# 1匹目: 通路の東側、いちばん手前のケージから出てくる。
	# 通路とケージだけでなく、観察室の中や給餌室の入口まで見回りに来る。
	_stalker(Vector3(3.5, 0.1, -14), [
		Vector3(0, 0, -11), Vector3(-1, 0, -5.5), Vector3(3, 0, -3.5), Vector3(-3.5, 0, -5.5),
		Vector3(0, 0, -16), Vector3(-3.5, 0, -22), Vector3(0, 0, -36), Vector3(0, 0, -42),
		Vector3(-3.5, 0, -30), Vector3(0, 0, -26), Vector3(3.5, 0, -22),
	])
	# 2匹目: 給餌室をぐるりと回り、ときどき通路の奥やケージにも出てくる
	_stalker(Vector3(6, 0.1, -52), [
		Vector3(6, 0, -40), Vector3(0, 0, -33), Vector3(3.5, 0, -30), Vector3(-5.5, 0, -40),
		Vector3(-6, 0, -48.5), Vector3(0, 0, -49), Vector3(6, 0, -47),
	])


func _stalker(pos: Vector3, points: Array) -> void:
	var s := Stalker.new()
	s.position = pos
	s.waypoints = points
	add_child(s)


func _spawn_items() -> void:
	for p in [Vector3(3, 0.3, -5), Vector3(1.2, 0.3, -29), Vector3(-4.2, 0.3, -22), Vector3(4.5, 1.0, -44)]:
		var can := Throwable.new()
		can.position = p
		add_child(can)
	var card := KeyCard.new()
	card.position = Vector3(-4, 0.95, -51)
	add_child(card)


## Blenderの部屋モデルがあれば読み込み、その部屋の箱の見た目を隠す。
## Blenderの原点とゲームの原点は同じ位置（座標の対応は docs/blender-guide.md）。
func _apply_room_models() -> void:
	for room in ROOMS:
		var path: String = ROOM_MODEL_DIR + room + ".glb"
		if not ResourceLoader.exists(path):
			continue
		var scene := load(path) as PackedScene
		if scene == null:
			push_warning("部屋モデルを読み込めませんでした: " + path)
			continue
		var model := scene.instantiate()
		model.name = "Model_" + room
		add_child(model)
		for n in get_tree().get_nodes_in_group("box_visual_" + room):
			n.visible = false
		print("部屋モデルを使用: ", path)


# --- 部品づくり -------------------------------------------------------------------

func _box(parent: Node, center: Vector3, size: Vector3, mat: Material, collide := true) -> Node3D:
	var mi := MeshInstance3D.new()
	var bm := BoxMesh.new()
	bm.size = size
	mi.mesh = bm
	mi.material_override = mat
	if _room != "":
		mi.add_to_group("box_visual_" + _room)
	if not collide:
		mi.position = center
		parent.add_child(mi)
		return mi
	var body := StaticBody3D.new()
	body.position = center
	var cs := CollisionShape3D.new()
	var sh := BoxShape3D.new()
	sh.size = size
	cs.shape = sh
	body.add_child(cs)
	body.add_child(mi)
	parent.add_child(body)
	return body


## z の位置に、x0..x1 の東西方向の壁。pad は角を埋めるための延長。
func _wall_x(parent: Node, z: float, x0: float, x1: float, mat: Material, pad := T) -> void:
	_box(parent, Vector3((x0 + x1) / 2.0, H / 2.0, z), Vector3(absf(x1 - x0) + pad, H, T), mat)


## x の位置に、z0..z1 の南北方向の壁。
func _wall_z(parent: Node, x: float, z0: float, z1: float, mat: Material, pad := T) -> void:
	_box(parent, Vector3(x, H / 2.0, (z0 + z1) / 2.0), Vector3(T, H, absf(z1 - z0) + pad), mat)


func _floor(parent: Node, x0: float, x1: float, z0: float, z1: float, mat: Material) -> void:
	_box(parent, Vector3((x0 + x1) / 2.0, -0.25, (z0 + z1) / 2.0), Vector3(absf(x1 - x0), 0.5, absf(z1 - z0)), mat)


func _hiding_spot(pos: Vector3, size: Vector3, label: String, color: Color) -> void:
	var h := HidingSpot.new()
	h.size = size
	h.label = label
	h.color = color
	h.position = pos
	nav.add_child(h)


func _puddle(r: Rect2) -> void:
	Game.puddles.append(r)
	var mi := MeshInstance3D.new()
	var pm := PlaneMesh.new()
	pm.size = r.size
	mi.mesh = pm
	mi.material_override = m_puddle
	mi.position = Vector3(r.position.x + r.size.x / 2.0, 0.01, r.position.y + r.size.y / 2.0)
	outside.add_child(mi)


func _light(pos: Vector3, color: Color, energy: float, light_range: float, flicker: bool) -> void:
	var l: OmniLight3D
	if flicker:
		var f := FlickerLight.new()
		f.base_energy = energy * LIGHT_BOOST
		l = f
	else:
		l = OmniLight3D.new()
	l.position = pos
	l.light_color = color
	l.light_energy = energy * LIGHT_BOOST
	l.omni_range = light_range + LIGHT_RANGE_ADD
	l.shadow_enabled = true
	add_child(l)


func _make_materials() -> void:
	m_concrete = _mat(Color(0.42, 0.41, 0.38), 0.95)                   # 古い棟: 汚れたコンクリート
	m_panel = _mat(Color(0.32, 0.38, 0.42), 0.4, 0.6)                  # 増築部: 新しい金属パネル
	m_floor = _mat(Color(0.18, 0.18, 0.19), 0.35)                      # 湿った床
	m_floor_new = _mat(Color(0.25, 0.27, 0.28), 0.6)
	m_bars = _mat(Color(0.3, 0.22, 0.18), 0.6, 0.8)                    # 錆びた鉄格子
	m_furniture = _mat(Color(0.35, 0.33, 0.3), 0.8)
	m_ceiling = _mat(Color(0.12, 0.12, 0.13), 0.9)
	m_puddle = _mat(Color(0.04, 0.05, 0.07), 0.02, 0.9)
	m_glass = _mat(Color(0.6, 0.8, 0.9, 0.15), 0.05)
	m_glass.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA


func _mat(c: Color, rough := 0.9, metal := 0.0) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.albedo_color = c
	m.roughness = rough
	m.metallic = metal
	return m


func _make_environment() -> void:
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color(0.01, 0.01, 0.015)
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.5, 0.52, 0.6)
	env.ambient_light_energy = AMBIENT_ENERGY
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	env.glow_enabled = true
	env.fog_enabled = true
	env.fog_light_color = Color(0.12, 0.12, 0.15)
	env.fog_density = 0.015
	var we := WorldEnvironment.new()
	we.environment = env
	add_child(we)


# --- 自動テスト（godot --headless -- --selftest） -------------------------------------

func _is_selftest() -> bool:
	return "--selftest" in OS.get_cmdline_user_args()


func _selftest() -> void:
	var ok := true
	await get_tree().create_timer(0.5).timeout
	var polys := nav.navigation_mesh.get_polygon_count()
	print("SELFTEST navmesh polygons: ", polys)
	ok = ok and polys > 0

	# 恐竜が通路から観察室・給餌室の中まで歩いて行けるか
	var map := get_world_3d().navigation_map
	for goal in [Vector3(0, 0, -4), Vector3(4, 0, -48), Vector3(3.5, 0, -14)]:
		var path := NavigationServer3D.map_get_path(map, Vector3(0, 0, -25), goal, true)
		var reach: float = path[path.size() - 1].distance_to(goal) if path.size() > 0 else 999.0
		print("SELFTEST path to %s: end %.2f m away" % [goal, reach])
		ok = ok and reach < 0.8

	var s: Stalker = get_tree().get_nodes_in_group("stalker")[0]
	var p0 := s.global_position
	await get_tree().create_timer(3.0).timeout
	var moved := s.global_position.distance_to(p0)
	print("SELFTEST stalker patrol moved: %.2f m, state: %s" % [moved, Stalker.State.keys()[s.state]])
	ok = ok and moved > 1.0

	# 物音への反応
	Game.emit_noise(s.global_position + Vector3(0, 0, -3), 10.0, null)
	print("SELFTEST after noise: ", Stalker.State.keys()[s.state])
	ok = ok and s.state == Stalker.State.ALERT
	await get_tree().create_timer(2.0).timeout
	print("SELFTEST 2s later: ", Stalker.State.keys()[s.state])
	ok = ok and s.state == Stalker.State.SEARCH

	# 正面に立つと見つかって追われる
	var fwd := -s.global_transform.basis.z
	fwd.y = 0
	player.global_position = s.global_position + fwd.normalized() * 3.0
	await get_tree().create_timer(1.5).timeout
	print("SELFTEST player in front: ", Stalker.State.keys()[s.state], " / game: ", Game.State.keys()[Game.state])
	ok = ok and (s.state == Stalker.State.CHASE or s.state == Stalker.State.CATCH)

	print("SELFTEST RESULT: ", "PASS" if ok else "FAIL")
	get_tree().quit(0 if ok else 1)
