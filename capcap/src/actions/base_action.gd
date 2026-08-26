class_name BaseAction
extends RefCounted

## BaseAction - Abstract Command Pattern Base Class with Strict Game Over & State Invariance

var action_id: String = ""
var unit_id: String = ""
var ap_cost: int = 0
var is_executed: bool = false
var is_cancelled: bool = false

func _init(p_action_id: String = "", p_unit_id: String = "", p_cost: int = 0) -> void:
	action_id = p_action_id
	unit_id = p_unit_id
	ap_cost = max(0, p_cost)

func can_execute(game_state) -> Array:
	if game_state.match_state != 0: # MatchState.ONGOING == 0
		return [false, "Match is already over (Game Over)."]
	if is_executed:
		return [false, "Action was already executed."]
	if is_cancelled:
		return [false, "Action was cancelled."]
	return [false, "Abstract action cannot be executed."]

func execute(game_state) -> bool:
	return false

func cancel() -> void:
	is_cancelled = true
