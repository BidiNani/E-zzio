class_name GameState
extends RefCounted

## GameState - Central Match State, Serialization & Game Over Authority

const VictoryEvaluatorScript = preload("res://src/objectives/victory_evaluator.gd")
const MissionObjectiveScript = preload("res://src/objectives/mission_objective.gd")

var turn_number: int = 1
var max_turns: int = 20
var active_team: String = "Player"
var match_state: int = 0 # 0: ONGOING, 1: VICTORY_PLAYER, 2: DEFEAT_PLAYER
var units: Dictionary = {}
var objectives: Array = []
var grid_map

signal turn_changed(new_turn, team)
signal match_state_changed(new_state)

func _init(p_grid_map = null) -> void:
	grid_map = p_grid_map

func register_unit(unit) -> void:
	units[unit.unit_id] = unit

func get_unit(unit_id: String):
	return units.get(unit_id, null)

func add_objective(obj) -> void:
	objectives.append(obj)

func evaluate_victory() -> int:
	var old_state = match_state
	match_state = VictoryEvaluatorScript.evaluate_match(self, objectives, max_turns)
	if match_state != old_state:
		emit_signal("match_state_changed", match_state)
	return match_state

func next_turn() -> void:
	if match_state != 0:
		return # Game Over, no turn advancement

	turn_number += 1
	evaluate_victory()
	emit_signal("turn_changed", turn_number, active_team)

func serialize() -> Dictionary:
	var units_data: Dictionary = {}
	for uid in units.keys():
		var u = units[uid]
		units_data[uid] = {
			"name": u.unit_name,
			"team": u.team_id,
			"grid_pos": [u.grid_pos.x, u.grid_pos.y],
			"elevation": u.current_elevation,
			"is_overwatch": u.is_overwatch,
			"state": u.state,
			"stats": u.stats.serialize()
		}

	var objs_data: Array = []
	for obj in objectives:
		objs_data.append(obj.serialize())

	return {
		"turn_number": turn_number,
		"max_turns": max_turns,
		"active_team": active_team,
		"match_state": match_state,
		"units": units_data,
		"objectives": objs_data
	}

func deserialize(data: Dictionary) -> bool:
	turn_number = data.get("turn_number", 1)
	max_turns = data.get("max_turns", 20)
	active_team = data.get("active_team", "Player")
	match_state = data.get("match_state", 0)

	var units_dict = data.get("units", {})
	for uid in units_dict.keys():
		if units.has(uid):
			var u = units[uid]
			var u_data = units_dict[uid]
			var pos_arr = u_data.get("grid_pos", [0, 0])
			u.grid_pos = Vector2i(pos_arr[0], pos_arr[1])
			u.current_elevation = u_data.get("elevation", 0)
			u.is_overwatch = u_data.get("is_overwatch", false)
			u.state = u_data.get("state", 0)
			u.stats.deserialize(u_data.get("stats", {}))
			u.position = grid_map.cells[u.grid_pos].elevation if grid_map and grid_map.is_valid_cell(u.grid_pos) else Vector2.ZERO

	objectives.clear()
	var objs_arr = data.get("objectives", [])
	for obj_dict in objs_arr:
		var obj = MissionObjectiveScript.new()
		obj.deserialize(obj_dict)
		objectives.append(obj)

	return true
