class_name OverwatchAction
extends "res://src/actions/base_action.gd"

## OverwatchAction - Enters tactical Overwatch reaction stance (Cost: 2 AP)

func _init(p_unit_id: String, p_cost: int = 2) -> void:
	super._init("overwatch_" + p_unit_id, p_unit_id, max(0, p_cost))

func can_execute(game_state) -> Array:
	if is_executed:
		return [false, "Action was already executed."]
	if is_cancelled:
		return [false, "Action was cancelled."]

	var unit = game_state.get_unit(unit_id)
	if not unit:
		return [false, "Unit not found."]
	if unit.state == unit.State.DISABLED or not unit.stats.is_alive():
		return [false, "Unit is disabled or defeated."]
	if not unit.stats.can_afford(ap_cost):
		return [false, "Insufficient Action Points (requires %d, has %d)." % [ap_cost, unit.stats.current_ap]]

	return [true, "OK"]

func execute(game_state) -> bool:
	var validation = can_execute(game_state)
	if not validation[0]:
		return false

	var unit = game_state.get_unit(unit_id)
	unit.stats.consume_ap(ap_cost)
	unit.is_overwatch = true
	unit.queue_redraw()
	is_executed = true
	return true
