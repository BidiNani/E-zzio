class_name CombatResolver
extends RefCounted

## CombatResolver - Computes 2.5D range, elevation bonus, cover mitigation and deterministic damage

const CoverSystemScript = preload("res://src/combat/cover_system.gd")

static func get_distance_3d(pos_a: Vector2i, z_a: int, pos_b: Vector2i, z_b: int) -> float:
	var dx: float = float(pos_b.x - pos_a.x)
	var dy: float = float(pos_b.y - pos_a.y)
	var dz: float = float(z_b - z_a)
	return sqrt(dx * dx + dy * dy + dz * dz)

static func is_in_range(pos_a: Vector2i, z_a: int, pos_b: Vector2i, z_b: int, min_range: float, max_range: float) -> bool:
	var dist: float = get_distance_3d(pos_a, z_a, pos_b, z_b)
	return dist >= min_range and dist <= max_range

static func calculate_damage(attacker, target, grid_map = null) -> int:
	var base_dmg: int = attacker.base_damage

	# High ground elevation bonus (+2 if attacker is strictly higher than target)
	if attacker.current_elevation > target.current_elevation:
		base_dmg += 2

	# Directional cover mitigation
	var mitigation: int = 0
	if grid_map:
		var cover = CoverSystemScript.get_cover_type(attacker.grid_pos, attacker.current_elevation, target.grid_pos, target.current_elevation, grid_map)
		mitigation = CoverSystemScript.get_mitigation(cover)

	return max(1, base_dmg - mitigation)
