class_name DecisionEngine
extends RefCounted

## DecisionEngine - Evaluates situation and generates concrete tactical actions (ATTACK, MOVE, HOLD)

const PerceptionScript = preload("res://src/ai/perception_system.gd")
const ThreatScript = preload("res://src/ai/threat_evaluator.gd")
const CombatResolverScript = preload("res://src/combat/combat_resolver.gd")
const LOSScript = preload("res://src/combat/line_of_sight_2d.gd")
const AttackActionScript = preload("res://src/actions/attack_action.gd")
const MoveActionScript = preload("res://src/actions/move_action.gd")

enum Intent { ATTACK, MOVE_TO_ATTACK, HOLD }

static func decide_action(ai_unit, game_state, pathfinder):
	if not ai_unit or not ai_unit.stats.is_alive() or ai_unit.stats.current_ap == 0 or ai_unit.state == ai_unit.State.DISABLED:
		return null

	# 1. Perceive visible hostile targets
	var enemies = PerceptionScript.get_visible_enemies(ai_unit, game_state, 12.0)
	if enemies.size() == 0:
		return null # HOLD

	# 2. Select priority target
	var primary_target = ThreatScript.select_highest_threat(ai_unit, enemies)
	if not primary_target:
		return null

	# 3. Check if immediate attack is possible
	var in_range = CombatResolverScript.is_in_range(ai_unit.grid_pos, ai_unit.current_elevation, primary_target.grid_pos, primary_target.current_elevation, ai_unit.min_range, ai_unit.max_range)
	var has_los = LOSScript.has_los(ai_unit.grid_pos, ai_unit.current_elevation, primary_target.grid_pos, primary_target.current_elevation, game_state.grid_map)

	if in_range and has_los and ai_unit.stats.current_ap >= 2:
		var atk_act = AttackActionScript.new(ai_unit.unit_id, primary_target.unit_id)
		var val = atk_act.can_execute(game_state)
		if val[0]:
			return atk_act

	# 4. If out of range or blocked, find best firing position to move toward
	var best_path: Array[Vector2i] = find_approach_path(ai_unit, primary_target, game_state, pathfinder)
	if best_path.size() > 1:
		# Truncate path to maximum available AP
		var max_steps: int = min(ai_unit.stats.current_ap, best_path.size() - 1)
		var truncated_path: Array[Vector2i] = []
		for i in range(max_steps + 1):
			truncated_path.append(best_path[i])

		if truncated_path.size() > 1:
			var move_act = MoveActionScript.new(ai_unit.unit_id, truncated_path)
			var val = move_act.can_execute(game_state)
			if val[0]:
				return move_act

	return null # HOLD

static func find_approach_path(ai_unit, target, game_state, pathfinder) -> Array[Vector2i]:
	# Search candidate firing positions around target within max_range
	var target_pos = target.grid_pos
	var target_z = target.current_elevation
	var best_pos = Vector2i.ZERO
	var min_dist_to_ai: float = 9999.0

	var search_radius: int = int(floor(ai_unit.max_range))
	for dx in range(-search_radius, search_radius + 1):
		for dy in range(-search_radius, search_radius + 1):
			var cand = Vector2i(target_pos.x + dx, target_pos.y + dy)
			if game_state.grid_map.is_cell_walkable(cand):
				var cand_z = game_state.grid_map.get_cell(cand).elevation
				if CombatResolverScript.is_in_range(cand, cand_z, target_pos, target_z, ai_unit.min_range, ai_unit.max_range):
					if LOSScript.has_los(cand, cand_z, target_pos, target_z, game_state.grid_map):
						var d = float(abs(cand.x - ai_unit.grid_pos.x) + abs(cand.y - ai_unit.grid_pos.y))
						if d < min_dist_to_ai:
							min_dist_to_ai = d
							best_pos = cand

	if best_pos != Vector2i.ZERO:
		return pathfinder.find_path(ai_unit.grid_pos, best_pos)

	return []
