class_name VisibilityMap
extends RefCounted

## VisibilityMap - Persistent Fog of War state manager per team (HIDDEN, EXPLORED, VISIBLE)

enum FogState { HIDDEN = 0, EXPLORED = 1, VISIBLE = 2 }

var width: int = 16
var height: int = 16
var fog_cells: Dictionary = {} # Vector2i -> FogState

func _init(p_width: int = 16, p_height: int = 16) -> void:
	width = p_width
	height = p_height
	reset_map()

func reset_map() -> void:
	fog_cells.clear()
	for x in range(width):
		for y in range(height):
			fog_cells[Vector2i(x, y)] = FogState.HIDDEN

func update_visibility(currently_visible: Array) -> void:
	# 1. Transition all previous VISIBLE cells to EXPLORED
	for pos in fog_cells.keys():
		if fog_cells[pos] == FogState.VISIBLE:
			fog_cells[pos] = FogState.EXPLORED

	# 2. Mark currently visible cells as VISIBLE
	for pos in currently_visible:
		if fog_cells.has(pos):
			fog_cells[pos] = FogState.VISIBLE

func get_state(pos: Vector2i) -> FogState:
	return fog_cells.get(pos, FogState.HIDDEN)

func is_cell_visible(pos: Vector2i) -> bool:
	return get_state(pos) == FogState.VISIBLE

func is_cell_explored(pos: Vector2i) -> bool:
	return get_state(pos) in [FogState.EXPLORED, FogState.VISIBLE]

func serialize() -> Dictionary:
	var raw: Dictionary = {}
	for pos in fog_cells.keys():
		var state_val: int = int(fog_cells[pos])
		if state_val != FogState.HIDDEN:
			raw["%d,%d" % [pos.x, pos.y]] = state_val
	return {"width": width, "height": height, "explored_data": raw}

func deserialize(data: Dictionary) -> bool:
	width = data.get("width", 16)
	height = data.get("height", 16)
	reset_map()
	var raw = data.get("explored_data", {})
	for k in raw.keys():
		var parts = k.split(",")
		if parts.size() == 2:
			var pos = Vector2i(int(parts[0]), int(parts[1]))
			fog_cells[pos] = int(raw[k])
	return true
