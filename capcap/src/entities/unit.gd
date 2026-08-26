class_name Unit
extends Node2D

const IsoMathScript = preload("res://src/core/iso_math.gd")
const UnitStatsScript = preload("res://src/state/unit_stats.gd")

enum State { IDLE, MOVING, ATTACKING, DISABLED }

var unit_id: String = ""
var unit_name: String = ""
var grid_pos: Vector2i = Vector2i.ZERO
var current_elevation: int = 0
var team_id: String = "Player"
var unit_color: Color = Color(0.2, 0.6, 1.0)

var min_range: float = 1.0
var max_range: float = 5.0
var vision_radius: float = 8.0
var base_damage: int = 8

var is_selected: bool = false
var is_overwatch: bool = false
var is_flashing_hit: bool = false
var flash_timer: float = 0.0
var state: State = State.IDLE

var stats
var current_path: Array[Vector2i] = []
var path_index: int = 0
var move_speed: float = 4.0
var move_progress: float = 0.0

signal move_completed(unit)
signal step_completed(unit, current_pos)

func setup(p_id: String, p_name: String, p_pos: Vector2i, p_color: Color, p_elevation: int = 0, p_max_ap: int = 6, p_team: String = "Player", p_max_range: float = 5.0, p_base_damage: int = 8) -> void:
	unit_id = p_id
	unit_name = p_name
	grid_pos = p_pos
	unit_color = p_color
	current_elevation = p_elevation
	team_id = p_team
	max_range = p_max_range
	base_damage = p_base_damage
	stats = UnitStatsScript.new(p_max_ap, 20)
	position = IsoMathScript.grid_to_world(grid_pos, current_elevation)
	queue_redraw()

func follow_path(p_path: Array[Vector2i], grid_map) -> void:
	if p_path.size() <= 1:
		return
	current_path = p_path
	path_index = 0
	move_progress = 0.0
	state = State.MOVING

func trigger_hit_feedback() -> void:
	is_flashing_hit = true
	flash_timer = 0.2
	queue_redraw()

func _process(delta: float) -> void:
	if is_flashing_hit:
		flash_timer -= delta
		if flash_timer <= 0.0:
			is_flashing_hit = false
			queue_redraw()

	if state == State.MOVING and current_path.size() > 1:
		move_progress += delta * move_speed
		if move_progress >= 1.0:
			move_progress = 0.0
			path_index += 1
			grid_pos = current_path[path_index]
			emit_signal("step_completed", self, grid_pos)

			if path_index >= current_path.size() - 1 or not stats.is_alive():
				state = State.IDLE
				current_path.clear()
				emit_signal("move_completed", self)
				queue_redraw()
				return

		var from_pos = current_path[path_index]
		var to_pos = current_path[path_index + 1]
		var world_from = IsoMathScript.grid_to_world(from_pos, current_elevation)
		var world_to = IsoMathScript.grid_to_world(to_pos, current_elevation)
		position = world_from.lerp(world_to, move_progress)
		queue_redraw()

func set_selected(p_selected: bool) -> void:
	is_selected = p_selected
	queue_redraw()

func _draw() -> void:
	if not stats or not stats.is_alive():
		draw_circle(Vector2.ZERO, 6.0, Color(0.2, 0.2, 0.2, 0.4))
		return

	# 1. Selection Pulsing Halo
	if is_selected:
		draw_arc(Vector2.ZERO, 15.0, 0, TAU, 24, Color(1.0, 1.0, 1.0, 0.9), 2.5)
		draw_arc(Vector2.ZERO, 18.0, 0, TAU, 24, Color(0.2, 0.8, 1.0, 0.4), 1.5)

	# 2. Base Faction & Body
	var body_col = Color.WHITE if is_flashing_hit else unit_color
	if state == State.DISABLED:
		body_col = body_col.darkened(0.6)

	draw_circle(Vector2.ZERO, 11.0, body_col)
	draw_arc(Vector2.ZERO, 11.0, 0, TAU, 20, Color.BLACK, 1.5)

	# 3. Role Silhouette Glyphs
	if "Sniper" in unit_name:
		# Triangle / Reticle glyph
		var pts = PackedVector2Array([Vector2(0, -6), Vector2(5, 4), Vector2(-5, 4)])
		draw_colored_polygon(pts, Color.WHITE)
	elif "Vanguard" in unit_name:
		# Shield shape glyph
		var pts = PackedVector2Array([Vector2(-4, -4), Vector2(4, -4), Vector2(4, 1), Vector2(0, 5), Vector2(-4, 1)])
		draw_colored_polygon(pts, Color.WHITE)
	elif "Orc" in unit_name or "Guard" in unit_name:
		# Horns / heavy square glyph
		draw_rect(Rect2(Vector2(-4, -4), Vector2(8, 8)), Color.BLACK)
	elif "Scout" in unit_name:
		# Diamond glyph
		var pts = PackedVector2Array([Vector2(0, -5), Vector2(5, 0), Vector2(0, 5), Vector2(-5, 0)])
		draw_colored_polygon(pts, Color.BLACK)

	# 4. Overwatch Indicator
	if is_overwatch:
		draw_arc(Vector2.ZERO, 15.0, 0, TAU, 16, Color(1.0, 0.85, 0.1, 0.95), 2.0)
		draw_line(Vector2(-7, 0), Vector2(7, 0), Color.YELLOW, 1.5)
		draw_line(Vector2(0, -7), Vector2(0, 7), Color.YELLOW, 1.5)

	# 5. Health Bar
	var bar_width = 24.0
	var bar_height = 4.0
	var bar_pos = Vector2(-bar_width / 2.0, -18.0)

	draw_rect(Rect2(bar_pos, Vector2(bar_width, bar_height)), Color(0.1, 0.1, 0.1, 0.8))
	var hp_pct = float(stats.current_hp) / float(stats.max_hp)
	var hp_col = Color(0.2, 0.9, 0.2) if hp_pct > 0.5 else (Color(0.95, 0.8, 0.1) if hp_pct > 0.25 else Color(0.95, 0.2, 0.2))
	draw_rect(Rect2(bar_pos, Vector2(bar_width * hp_pct, bar_height)), hp_col)
