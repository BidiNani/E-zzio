class_name FormationSolver
extends RefCounted

## FormationSolver - Computes unique, valid destination cells for groups of units

enum FormationType { LINE, GRID }

## Returns a Dictionary mapping unit -> target_cell
static func solve_formation(units: Array, target_center: Vector2i, grid_map, form_type: FormationType = FormationType.GRID) -> Dictionary:
	var result: Dictionary = {}
	var assigned_cells: Array[Vector2i] = []
	var count: int = units.size()

	if count == 0:
		return result
	if count == 1:
		var valid_target = find_closest_valid_cell(target_center, grid_map, assigned_cells)
		result[units[0]] = valid_target
		return result

	var raw_offsets: Array[Vector2i] = []

	if form_type == FormationType.LINE:
		# Line formation: along Y axis perpendicular to typical movement
		var half: int = count / 2
		for i in range(count):
			raw_offsets.append(Vector2i(0, i - half))
	else:
		# Grid formation: compact square matrix
		var cols: int = int(ceil(sqrt(float(count))))
		for i in range(count):
			var r: int = i / cols
			var c: int = i % cols
			raw_offsets.append(Vector2i(c - cols/2, r - cols/2))

	# Assign cells with collision & obstacle resolution
	for i in range(count):
		var unit = units[i]
		var ideal_pos: Vector2i = target_center + raw_offsets[i]
		var final_cell: Vector2i = find_closest_valid_cell(ideal_pos, grid_map, assigned_cells)
		result[unit] = final_cell
		assigned_cells.append(final_cell)

	return result

## Spiral search around pos to find the closest valid, walkable, and unassigned cell
static func find_closest_valid_cell(center: Vector2i, grid_map, assigned_cells: Array[Vector2i], max_radius: int = 8) -> Vector2i:
	if grid_map.is_cell_walkable(center) and not assigned_cells.has(center):
		return center

	for r in range(1, max_radius + 1):
		for dx in range(-r, r + 1):
			for dy in range(-r, r + 1):
				if abs(dx) == r or abs(dy) == r:
					var cand = Vector2i(center.x + dx, center.y + dy)
					if grid_map.is_cell_walkable(cand) and not assigned_cells.has(cand):
						return cand

	return center # Fallback
