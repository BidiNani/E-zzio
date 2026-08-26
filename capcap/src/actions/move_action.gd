class_name MoveAction
extends "res://src/actions/base_action.gd"

## MoveAction - Command for unit movement across waypoints respecting AP cost & Game Over state

var path: Array[Vector2i] = []
var target_cell: Vector2i = Vector2i.ZERO

func _init(p_unit_id: String, p_path: Array[Vector2i]) -> void:
	super._init("move_" + p_unit_id, p_unit_id, max(0, p_path.size() - 1))
	path = p_path
	if path.size() > 0:
		target_cell = path[path.size() - 1]

func can_execute(game_state) -> Array:
	if game_state.match_state != 0:
		return [false, "Match is already over (Game Over)."]
	if is_executed:
		return [false, "Action was already executed."]
	if is_cancelled:
		return [false, "Action was cancelled."]
	if path.size() <= 1:
		return [false, "Path is empty or already at destination."]

	var unit = game_state.get_unit(unit_id)
	if not unit:
		return [false, "Unit not found."]
	if unit.state == unit.State.DISABLED or not unit.stats.is_alive():
		return [false, "Unit is disabled or defeated."]
	if not unit.stats.can_afford(ap_cost):
		return [false, "Insufficient Action Points (requires %d, has %d)." % [ap_cost, unit.stats.current_ap]]

	for i in range(path.size() - 1):
		var c_curr = path[i]
		var c_next = path[i + 1]
		if not game_state.grid_map.is_cell_walkable(c_next) or not game_state.grid_map.can_traverse(c_curr, c_next):
			return [false, "Path obstructed at (%d, %d)." % [c_next.x, c_next.y]]

	return [true, "OK"]

func execute(game_state) -> bool:
	var validation = can_execute(game_state)
	if not validation[0]:
		return false

	var unit = game_state.get_unit(unit_id)
	unit.stats.consume_ap(ap_cost)
	unit.follow_path(path, game_state.grid_map)
	is_executed = true
	game_state.evaluate_victory()
	return true
