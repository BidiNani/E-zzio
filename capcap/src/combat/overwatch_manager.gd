class_name OverwatchManager
extends RefCounted

## OverwatchManager - Deterministic event-driven reaction coordinator for movement triggers

const VisionSystemScript = preload("res://src/vision/vision_system.gd")
const CombatResolverScript = preload("res://src/combat/combat_resolver.gd")
const LineOfSight2DScript = preload("res://src/combat/line_of_sight_2d.gd")
const AttackActionScript = preload("res://src/actions/attack_action.gd")

## Handles enemy movement step event and triggers deterministic reaction shots
static func on_unit_step_moved(moving_unit, step_pos: Vector2i, game_state, combat_renderer = null) -> Array:
	var reactions: Array = []
	if not moving_unit or not moving_unit.stats.is_alive():
		return reactions

	var moving_elev: int = game_state.grid_map.get_cell(step_pos).elevation if game_state.grid_map.is_valid_cell(step_pos) else 0

	# 1. Identify all eligible enemy reactors currently in Overwatch
	var candidate_reactors: Array = []
	for uid in game_state.units.keys():
		var u = game_state.units[uid]
		if u.team_id != moving_unit.team_id and u.is_overwatch and u.stats.is_alive() and u.state != u.State.DISABLED:
			# Check Range
			if CombatResolverScript.is_in_range(u.grid_pos, u.current_elevation, step_pos, moving_elev, u.min_range, u.max_range):
				# Check Vision / Line of Sight to the stepped cell
				if LineOfSight2DScript.has_los(u.grid_pos, u.current_elevation, step_pos, moving_elev, game_state.grid_map):
					candidate_reactors.append(u)

	if candidate_reactors.size() == 0:
		return reactions

	# 2. Sort candidate reactors deterministically by (Distance 3D ascending, ID ascending)
	candidate_reactors.sort_custom(func(a, b):
		var dist_a = CombatResolverScript.get_distance_3d(a.grid_pos, a.current_elevation, step_pos, moving_elev)
		var dist_b = CombatResolverScript.get_distance_3d(b.grid_pos, b.current_elevation, step_pos, moving_elev)
		if not is_equal_approx(dist_a, dist_b):
			return dist_a < dist_b
		return a.unit_id < b.unit_id
	)

	# 3. Execute reaction shots sequentially
	for reactor in candidate_reactors:
		if not moving_unit.stats.is_alive():
			break # Target defeated, stop further shots

		# Build and execute AttackAction
		var atk_act = AttackActionScript.new(reactor.unit_id, moving_unit.unit_id, 0) # Reaction shot cost was prepaid on entering overwatch
		var valid = atk_act.can_execute(game_state)
		if valid[0]:
			atk_act.execute(game_state)
			reactor.is_overwatch = false # Consume overwatch stance
			reactor.queue_redraw()

			if combat_renderer:
				combat_renderer.fire_tracer(reactor.grid_pos, reactor.current_elevation, step_pos, moving_elev)

			reactions.append({"reactor_id": reactor.unit_id, "target_id": moving_unit.unit_id, "success": true})

	return reactions

## Resets overwatch for team at start of their turn
static func reset_team_overwatch(team_id: String, game_state) -> void:
	for uid in game_state.units.keys():
		var u = game_state.units[uid]
		if u.team_id == team_id:
			u.is_overwatch = false
			u.queue_redraw()
