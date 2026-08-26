class_name LineOfSight2D
extends RefCounted

## LineOfSight2D - Geometric 2.5D discrete raycaster for sightline and ballistic trajectory

## Returns true if unobstructed line of sight exists between source and target
static func has_los(from_pos: Vector2i, from_z: int, to_pos: Vector2i, to_z: int, grid_map) -> bool:
	if from_pos == to_pos:
		return true

	var dist_steps: int = int(ceil(max(abs(to_pos.x - from_pos.x), abs(to_pos.y - from_pos.y)))) * 2
	if dist_steps < 2:
		dist_steps = 2

	for step in range(1, dist_steps):
		var t: float = float(step) / float(dist_steps)
		var rx: float = lerp(float(from_pos.x), float(to_pos.x), t)
		var ry: float = lerp(float(from_pos.y), float(to_pos.y), t)
		var rz: float = lerp(float(from_z), float(to_z), t)

		var test_cell = Vector2i(int(round(rx)), int(round(ry)))

		# Ignore start and destination cells
		if test_cell == from_pos or test_cell == to_pos:
			continue

		if not grid_map.is_valid_cell(test_cell):
			return false

		var cell = grid_map.get_cell(test_cell)
		if cell:
			# Low cover allows line of sight (damage is mitigated via CoverSystem)
			if cell.tile_theme == "cover_half":
				continue

			# 1. Solid opaque obstacle or full cover wall blocks sight
			if not cell.is_walkable or cell.tile_theme == "cover_full":
				if float(cell.elevation) + 1.0 > rz:
					return false

			# 2. Intermediate cliff or plateau higher than the line of sight ray
			if float(cell.elevation) > rz:
				return false

	return true
