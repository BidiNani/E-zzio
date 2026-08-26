class_name VisionSystem
extends RefCounted

## VisionSystem - Central 2.5D visibility calculator shared equally by Player, AI and Renderer

const LOSScript = preload("res://src/combat/line_of_sight_2d.gd")
const CombatResolverScript = preload("res://src/combat/combat_resolver.gd")

const DEFAULT_VISION_RADIUS: float = 8.0

## Computes the array of grid cells visible to a single unit
static func compute_unit_vision(unit, grid_map, radius: float = DEFAULT_VISION_RADIUS) -> Array[Vector2i]:
	var visible: Array[Vector2i] = []
	if not unit or not unit.stats.is_alive() or unit.state == unit.State.DISABLED:
		return visible

	var origin: Vector2i = unit.grid_pos
	var origin_z: int = unit.current_elevation
	var r_int: int = int(ceil(radius))

	for dx in range(-r_int, r_int + 1):
		for dy in range(-r_int, r_int + 1):
			var target_pos = Vector2i(origin.x + dx, origin.y + dy)
			if grid_map.is_valid_cell(target_pos):
				var target_z: int = grid_map.get_cell(target_pos).elevation
				var dist: float = CombatResolverScript.get_distance_3d(origin, origin_z, target_pos, target_z)
				if dist <= radius:
					if LOSScript.has_los(origin, origin_z, target_pos, target_z, grid_map):
						visible.append(target_pos)

	return visible

## Computes the set union of all visible cells for an entire team
static func compute_team_vision(team_id: String, game_state) -> Array[Vector2i]:
	var visible_set: Dictionary = {}
	for uid in game_state.units.keys():
		var u = game_state.units[uid]
		if u.team_id == team_id and u.stats.is_alive():
			var unit_vision = compute_unit_vision(u, game_state.grid_map, DEFAULT_VISION_RADIUS)
			for pos in unit_vision:
				visible_set[pos] = true

	var res: Array[Vector2i] = []
	for p in visible_set.keys():
		res.append(p)
	return res

## Checks if an observer unit has line of sight and range to see a target unit
static func is_unit_visible(observer, target, grid_map, radius: float = DEFAULT_VISION_RADIUS) -> bool:
	if not observer or not target or not observer.stats.is_alive() or not target.stats.is_alive():
		return false

	var dist: float = CombatResolverScript.get_distance_3d(observer.grid_pos, observer.current_elevation, target.grid_pos, target.current_elevation)
	if dist > radius:
		return false

	return LOSScript.has_los(observer.grid_pos, observer.current_elevation, target.grid_pos, target.current_elevation, grid_map)
