class_name VictoryEvaluator
extends RefCounted

## VictoryEvaluator - Single authority and deterministic arbiter for Match Victory and Defeat

enum MatchState { ONGOING = 0, VICTORY_PLAYER = 1, DEFEAT_PLAYER = 2 }

## Evaluates the current game state and produces a deterministic verdict
static func evaluate_match(game_state, objectives: Array, max_turns: int = 20) -> MatchState:
	# 1. Defeat Condition: All Player units wiped out
	var player_units_alive: int = 0
	for uid in game_state.units.keys():
		var u = game_state.units[uid]
		if u.team_id == "Player" and u.stats.is_alive():
			player_units_alive += 1

	if player_units_alive == 0:
		return MatchState.DEFEAT_PLAYER

	# 2. Check and update objectives progress
	for obj in objectives:
		obj.check_progress(game_state)

	# 3. Check for any critical failed objective
	for obj in objectives:
		if obj.team_id == "Player" and obj.is_mandatory and obj.is_failed:
			return MatchState.DEFEAT_PLAYER

	# 4. Victory Condition: All mandatory Player objectives completed
	var mandatory_count: int = 0
	var completed_mandatory_count: int = 0

	for obj in objectives:
		if obj.team_id == "Player" and obj.is_mandatory:
			mandatory_count += 1
			if obj.is_completed:
				completed_mandatory_count += 1

	if mandatory_count > 0 and completed_mandatory_count == mandatory_count:
		return MatchState.VICTORY_PLAYER

	# 5. Defeat Condition: Turn limit exceeded without victory
	if game_state.turn_number > max_turns:
		return MatchState.DEFEAT_PLAYER

	return MatchState.ONGOING
