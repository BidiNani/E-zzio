class_name AIController
extends RefCounted

## AIController - Orchestrates turn execution for all AI units

const DecisionEngineScript = preload("res://src/ai/decision_engine.gd")

static func execute_ai_turn(game_state, action_queue, pathfinder, combat_renderer = null) -> void:
	for uid in game_state.units.keys():
		var u = game_state.units[uid]
		if u.team_id == "Enemy" and u.stats.is_alive():
			# Loop decisions until AP exhausted or HOLD
			var safety_counter: int = 0
			while u.stats.current_ap > 0 and safety_counter < 6:
				safety_counter += 1
				var action = DecisionEngineScript.decide_action(u, game_state, pathfinder)
				if not action:
					break

				if combat_renderer and action.get_script().get_global_name() == "AttackAction":
					var target = game_state.get_unit(action.target_id)
					if target:
						combat_renderer.fire_tracer(u.grid_pos, u.current_elevation, target.grid_pos, target.current_elevation)

				action_queue.push_action(action)
				action_queue.execute_all(game_state)
