class_name ThreatEvaluator
extends RefCounted

## ThreatEvaluator - Deterministic threat scoring with cover awareness & flanking incentives

const CombatResolverScript = preload("res://src/combat/combat_resolver.gd")
const CoverSystemScript = preload("res://src/combat/cover_system.gd")

static func evaluate_threat(ai_unit, target_unit, grid_map = null) -> float:
	var dist: float = CombatResolverScript.get_distance_3d(ai_unit.grid_pos, ai_unit.current_elevation, target_unit.grid_pos, target_unit.current_elevation)
	var hp_fraction: float = float(target_unit.stats.current_hp) / float(target_unit.stats.max_hp)
	var elev_diff: float = float(target_unit.current_elevation - ai_unit.current_elevation)

	var score: float = 100.0 - (dist * 4.0) + ((1.0 - hp_fraction) * 25.0) + (elev_diff * 3.0)

	# Cover modifier: exposed / flanked targets receive bonus priority (+15), covered targets penalized
	if grid_map:
		var cover = CoverSystemScript.get_cover_type(ai_unit.grid_pos, ai_unit.current_elevation, target_unit.grid_pos, target_unit.current_elevation, grid_map)
		match cover:
			CoverSystemScript.CoverType.FULL:
				score -= 20.0
			CoverSystemScript.CoverType.HALF:
				score -= 10.0
			CoverSystemScript.CoverType.NONE:
				score += 15.0

	return score

static func select_highest_threat(ai_unit, targets: Array, grid_map = null):
	if targets.size() == 0:
		return null
	var best_target = targets[0]
	var best_score = evaluate_threat(ai_unit, best_target, grid_map)

	for i in range(1, targets.size()):
		var cand = targets[i]
		var score = evaluate_threat(ai_unit, cand, grid_map)
		if score > best_score:
			best_score = score
			best_target = cand

	return best_target
