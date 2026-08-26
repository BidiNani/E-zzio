class_name GridMap2D
extends RefCounted

## GridMap2D - Manages the 2.5D Isometric Grid Topology & Vertical Connectivity

const GridCellScript = preload("res://src/core/grid_cell.gd")

var width: int = 20
var height: int = 20
var cells: Dictionary = {} # Vector2i -> GridCell

func _init(p_width: int = 20, p_height: int = 20) -> void:
	width = p_width
	height = p_height
	generate_default_grid()

func generate_default_grid() -> void:
	cells.clear()
	for x in range(width):
		for y in range(height):
			var pos = Vector2i(x, y)
			var cell = GridCellScript.new(pos, true, 0, GridCellScript.Type.FLAT)
			cells[pos] = cell

func is_valid_cell(pos: Vector2i) -> bool:
	return pos.x >= 0 and pos.x < width and pos.y >= 0 and pos.y < height

func is_cell_walkable(pos: Vector2i) -> bool:
	if not is_valid_cell(pos):
		return false
	var cell = cells.get(pos)
	return cell.is_walkable if cell else false

func get_cell(pos: Vector2i):
	return cells.get(pos)

func set_cell_walkable(pos: Vector2i, walkable: bool) -> void:
	if is_valid_cell(pos):
		cells[pos].is_walkable = walkable

func set_cell_elevation(pos: Vector2i, elev: int) -> void:
	if is_valid_cell(pos):
		cells[pos].elevation = elev

func set_cell_stair(pos: Vector2i, elev: int, direction: Vector2i) -> void:
	if is_valid_cell(pos):
		var cell = cells[pos]
		cell.elevation = elev
		cell.cell_type = GridCellScript.Type.STAIR
		cell.ramp_direction = direction
		cell.is_walkable = true

func set_cell_cliff(pos: Vector2i, elev: int) -> void:
	if is_valid_cell(pos):
		var cell = cells[pos]
		cell.elevation = elev
		cell.cell_type = GridCellScript.Type.CLIFF
		cell.is_walkable = false

## Contract: can a character traverse directly from cell A to adjacent cell B?
func can_traverse(from_pos: Vector2i, to_pos: Vector2i) -> bool:
	if not is_valid_cell(from_pos) or not is_valid_cell(to_pos):
		return false

	var cell_a = cells.get(from_pos)
	var cell_b = cells.get(to_pos)

	if not cell_a.is_walkable or not cell_b.is_walkable:
		return false

	var delta_z: int = cell_b.elevation - cell_a.elevation
	var step_vec: Vector2i = to_pos - from_pos

	# 1. Flat traversal (Delta Z == 0): always allowed if both cells are walkable
	if delta_z == 0:
		return true

	# 2. Ascending Step (Delta Z == 1): Allowed only if entering a stair/ramp ascending in step_vec, or leaving one
	if delta_z == 1:
		if cell_b.cell_type == GridCellScript.Type.STAIR or cell_b.cell_type == GridCellScript.Type.RAMP:
			if cell_b.ramp_direction == step_vec or cell_b.ramp_direction == Vector2i.ZERO:
				return true
		if cell_a.cell_type == GridCellScript.Type.STAIR or cell_a.cell_type == GridCellScript.Type.RAMP:
			if cell_a.ramp_direction == step_vec or cell_a.ramp_direction == Vector2i.ZERO:
				return true
		return false # Cliff: ascent blocked!

	# 3. Descending Step (Delta Z == -1): Allowed only if stair/ramp, or controlled step down
	if delta_z == -1:
		if cell_a.cell_type == GridCellScript.Type.STAIR or cell_a.cell_type == GridCellScript.Type.RAMP:
			if cell_a.ramp_direction == -step_vec or cell_a.ramp_direction == Vector2i.ZERO:
				return true
		if cell_b.cell_type == GridCellScript.Type.STAIR or cell_b.cell_type == GridCellScript.Type.RAMP:
			if cell_b.ramp_direction == -step_vec or cell_b.ramp_direction == Vector2i.ZERO:
				return true
		return false # Cliff: drop blocked!

	# 4. Large drop/climb (|Delta Z| > 1): Strictly forbidden
	return false

## Returns reachable neighbors respecting vertical connectivity and corner-cutting prevention
func get_neighbors(pos: Vector2i, allow_diagonals: bool = false) -> Array[Vector2i]:
	var result: Array[Vector2i] = []
	var cardinals = [
		Vector2i(pos.x + 1, pos.y),
		Vector2i(pos.x - 1, pos.y),
		Vector2i(pos.x, pos.y + 1),
		Vector2i(pos.x, pos.y - 1)
	]
	for n in cardinals:
		if can_traverse(pos, n):
			result.append(n)
			
	if allow_diagonals:
		var diagonals = [
			Vector2i(pos.x + 1, pos.y + 1),
			Vector2i(pos.x - 1, pos.y + 1),
			Vector2i(pos.x + 1, pos.y - 1),
			Vector2i(pos.x - 1, pos.y - 1)
		]
		for d in diagonals:
			if is_valid_cell(d):
				var c1 = Vector2i(d.x, pos.y)
				var c2 = Vector2i(pos.x, d.y)
				# Diagonal is traversable only if direct edge can be traversed AND both cardinal corners are traversable
				if can_traverse(pos, d) and can_traverse(pos, c1) and can_traverse(pos, c2):
					result.append(d)
					
	return result

## Creates a rectangular elevated plateau with optional cliff boundaries
func create_plateau(top_left: Vector2i, size: Vector2i, elevation: int) -> void:
	for x in range(top_left.x, top_left.x + size.x):
		for y in range(top_left.y, top_left.y + size.y):
			var p = Vector2i(x, y)
			if is_valid_cell(p):
				cells[p].elevation = elevation
				cells[p].cell_type = GridCellScript.Type.FLAT
				cells[p].is_walkable = true
				cells[p].tile_theme = "stone"

## Creates a stepped stairway connecting elevation start_z to start_z + steps
func create_stairway(start_pos: Vector2i, direction: Vector2i, steps: int, start_z: int) -> void:
	for i in range(steps):
		var p = start_pos + (direction * i)
		if is_valid_cell(p):
			set_cell_stair(p, start_z + i, direction)
			cells[p].tile_theme = "wood"
