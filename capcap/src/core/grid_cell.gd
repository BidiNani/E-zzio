class_name GridCell
extends RefCounted

## GridCell - Data container for an individual 2.5D cell

enum Type { FLAT, STAIR, RAMP, CLIFF, PIT, WATER }

var grid_pos: Vector2i = Vector2i.ZERO
var elevation: int = 0
var cell_type: Type = Type.FLAT
var is_walkable: bool = true
var movement_cost: float = 1.0
var ramp_direction: Vector2i = Vector2i.ZERO # Direction of ascent
var tile_theme: String = "grass" # "grass", "stone", "dirt", "wood"
var occupant_id: String = ""

func _init(p_pos: Vector2i = Vector2i.ZERO, p_walkable: bool = true, p_elevation: int = 0, p_type: Type = Type.FLAT) -> void:
	grid_pos = p_pos
	is_walkable = p_walkable
	elevation = p_elevation
	cell_type = p_type
