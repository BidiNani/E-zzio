class_name CoverSystem
extends RefCounted

## CoverSystem - Evaluates directional 2.5D cover and damage mitigation (NONE, HALF, FULL)

enum CoverType { NONE, HALF, FULL }

const MITIGATION_HALF: int = 4
const MITIGATION_FULL: int = 8

## Evaluates the cover status of a target against an attacker
static func get_cover_type(attacker_pos: Vector2i, attacker_z: int, target_pos: Vector2i, target_z: int, grid_map) -> CoverType:
	if attacker_pos == target_pos:
		return CoverType.NONE

	var dir_x: int = int(sign(attacker_pos.x - target_pos.x))
	var dir_y: int = int(sign(attacker_pos.y - target_pos.y))

	var best_cover: CoverType = CoverType.NONE

	# Check adjacent directional blocker cells around target
	var check_cells: Array[Vector2i] = []
	if dir_x != 0:
		check_cells.append(Vector2i(target_pos.x + dir_x, target_pos.y))
	if dir_y != 0:
		check_cells.append(Vector2i(target_pos.x, target_pos.y + dir_y))

	for c in check_cells:
		if grid_map.is_valid_cell(c):
			var cell = grid_map.get_cell(c)
			if cell:
				# Full Cover: High obstacle or elevated cliff blocking direct body line
				if cell.elevation > target_z or cell.tile_theme == "cover_full":
					return CoverType.FULL

				# Half Cover: Low barricade, sandbag, or obstacle at same level
				if not cell.is_walkable or cell.tile_theme == "cover_half":
					if best_cover == CoverType.NONE:
						best_cover = CoverType.HALF

	return best_cover

static func get_mitigation(cover: CoverType) -> int:
	match cover:
		CoverType.HALF:
			return MITIGATION_HALF
		CoverType.FULL:
			return MITIGATION_FULL
		_:
			return 0
