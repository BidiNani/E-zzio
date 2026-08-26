class_name IsoCursor
extends Node2D

const IsoMathScript = preload("res://src/core/iso_math.gd")

var current_grid_pos: Vector2i = Vector2i.ZERO
var current_elevation: int = 0
var is_valid: bool = true

func update_cursor(grid_pos: Vector2i, elevation: int = 0, valid: bool = true) -> void:
	current_grid_pos = grid_pos
	current_elevation = elevation
	is_valid = valid
	position = IsoMathScript.grid_to_world(grid_pos, elevation)
	queue_redraw()

func _draw() -> void:
	var poly: PackedVector2Array = IsoMathScript.get_cell_polygon(Vector2i.ZERO, 0)
	var color: Color = Color(0.2, 0.8, 1.0, 0.8) if is_valid else Color(1.0, 0.2, 0.2, 0.8)
	draw_polyline(poly + PackedVector2Array([poly[0]]), color, 2.5)
