class_name AttackAction
extends "res://src/actions/base_action.gd"

## AttackAction - Tactical command with strict checks, directional cover and Game Over protection

const LOSScript = preload("res://src/combat/line_of_sight_2d.gd")
const CombatResolverScript = preload("res://src/combat/combat_resolver.gd")

var target_id: String = ""

func _init(p_attacker_id: String, p_target_id: String, p_cost: int = 2) -> void:
	super._init("attack_" + p_attacker_id + "_" + p_target_id, p_attacker_id, max(0, p_cost))
	target_id = p_target_id

func can_execute(game_state) -> Array:
	if game_state.match_state != 0:
		return [false, "Match is already over (Game Over)."]
	if is_executed:
		return [false, "Action was already executed."]
	if is_cancelled:
		return [false, "Action was cancelled."]

	if unit_id == target_id:
		return [false, "Cannot attack self (Self-fire prevented)."]

	var attacker = game_state.get_unit(unit_id)
	if not attacker:
		return [false, "Attacker not found."]
	if attacker.state == attacker.State.DISABLED or not attacker.stats.is_alive():
		return [false, "Attacker is disabled or defeated."]
	if not attacker.stats.can_afford(ap_cost):
		return [false, "Insufficient Action Points (requires %d, has %d)." % [ap_cost, attacker.stats.current_ap]]

	var target = game_state.get_unit(target_id)
	if not target:
		return [false, "Target unit not found."]
	if not target.stats.is_alive():
		return [false, "Target is already defeated."]
	if target.team_id == attacker.team_id:
		return [false, "Cannot attack friendly units (Friendly Fire blocked)."]

	if not CombatResolverScript.is_in_range(attacker.grid_pos, attacker.current_elevation, target.grid_pos, target.current_elevation, attacker.min_range, attacker.max_range):
		return [false, "Target is out of range."]

	if not LOSScript.has_los(attacker.grid_pos, attacker.current_elevation, target.grid_pos, target.current_elevation, game_state.grid_map):
		return [false, "Line of sight to target is blocked."]

	return [true, "OK"]

func execute(game_state) -> bool:
	var validation = can_execute(game_state)
	if not validation[0]:
		return false

	var attacker = game_state.get_unit(unit_id)
	var target = game_state.get_unit(target_id)

	attacker.stats.consume_ap(ap_cost)
	var damage = CombatResolverScript.calculate_damage(attacker, target, game_state.grid_map)
	target.stats.take_damage(damage)

	if not target.stats.is_alive():
		target.state = target.State.DISABLED
		target.queue_redraw()

	is_executed = true
	game_state.evaluate_victory()
	return true
