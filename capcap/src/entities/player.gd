class_name PlayerEntity
extends Node2D

const IsoMathScript = preload("res://src/core/iso_math.gd")

signal movement_started
signal movement_completed(target_pos: Vector2i)
signal step_taken(current_pos: Vector2i)

enum State { IDLE, MOVING, BLOCKED }

@export var move_speed: float = 180.0

var grid_pos: Vector2i = Vector2i(0, 0)
var current_elevation: int = 0
var state: State = State.IDLE
var path_waypoints: Array[Vector2i] = []
var target_world_pos: Vector2 = Vector2.ZERO

func _ready() -> void:
	sync_world_position()

func set_grid_position(p_pos: Vector2i, p_elevation: int = 0) -> void:
	grid_pos = p_pos
	current_elevation = p_elevation
	path_waypoints.clear()
	state = State.IDLE
	sync_world_position()

func sync_world_position() -> void:
	position = IsoMathScript.grid_to_world(grid_pos, current_elevation)

func follow_path(waypoints: Array[Vector2i], grid_map = null) -> void:
	if waypoints.size() <= 1:
		return
	path_waypoints = waypoints.duplicate()
	path_waypoints.pop_front()
	state = State.MOVING
	movement_started.emit()
	advance_to_next_waypoint(grid_map)

func advance_to_next_waypoint(grid_map = null) -> void:
	if path_waypoints.size() == 0:
		state = State.IDLE
		movement_completed.emit(grid_pos)
		return

	var next_grid: Vector2i = path_waypoints[0]
	if grid_map and not grid_map.is_cell_walkable(next_grid):
		state = State.BLOCKED
		path_waypoints.clear()
		return

	var cell = grid_map.get_cell(next_grid) if grid_map else null
	current_elevation = cell.elevation if cell else 0
	target_world_pos = IsoMathScript.grid_to_world(next_grid, current_elevation)

func _process(delta: float) -> void:
	if state == State.MOVING:
		position = position.move_toward(target_world_pos, move_speed * delta)
		if position.distance_to(target_world_pos) < 1.0:
			position = target_world_pos
			grid_pos = path_waypoints.pop_front()
			step_taken.emit(grid_pos)
			advance_to_next_waypoint()

func _draw() -> void:
	draw_circle(Vector2(0, 4), 10.0, Color(0.1, 0.1, 0.1, 0.4))
	draw_circle(Vector2(0, -12), 12.0, Color(0.2, 0.6, 1.0))
	draw_circle(Vector2(0, -28), 7.0, Color(1.0, 0.85, 0.6))
