class_name PerceptionSystem
extends RefCounted

## PerceptionSystem - Discovers hostile targets strictly through the central VisionSystem

const VisionSystemScript = preload("res://src/vision/vision_system.gd")

static func get_visible_enemies(ai_unit, game_state, max_radius: float = 8.0) -> Array:
	var visible: Array = []
	if not ai_unit or not ai_unit.stats.is_alive():
		return visible

	for uid in game_state.units.keys():
		var u = game_state.units[uid]
		if u.team_id != ai_unit.team_id and u.stats.is_alive():
			if VisionSystemScript.is_unit_visible(ai_unit, u, game_state.grid_map, max_radius):
				visible.append(u)

	return visible
