class_name UnitStats
extends RefCounted

## UnitStats - Manages Action Points (AP), Health (HP) and tactical attributes

signal ap_changed(current: int, max_val: int)
signal hp_changed(current: int, max_val: int)

var max_ap: int = 6
var current_ap: int = 6
var max_hp: int = 20
var current_hp: int = 20

func _init(p_max_ap: int = 6, p_max_hp: int = 20) -> void:
	max_ap = p_max_ap
	current_ap = p_max_ap
	max_hp = p_max_hp
	current_hp = p_max_hp

func can_afford(cost: int) -> bool:
	return current_ap >= cost

func consume_ap(cost: int) -> bool:
	if can_afford(cost):
		current_ap -= cost
		ap_changed.emit(current_ap, max_ap)
		return true
	return false

func restore_ap(amount: int = -1) -> void:
	if amount < 0:
		current_ap = max_ap
	else:
		current_ap = min(current_ap + amount, max_ap)
	ap_changed.emit(current_ap, max_ap)

func take_damage(amount: int) -> void:
	current_hp = max(0, current_hp - amount)
	hp_changed.emit(current_hp, max_hp)

func is_alive() -> bool:
	return current_hp > 0

func serialize() -> Dictionary:
	return {
		"max_ap": max_ap,
		"current_ap": current_ap,
		"max_hp": max_hp,
		"current_hp": current_hp
	}

func deserialize(data: Dictionary) -> void:
	max_ap = data.get("max_ap", 6)
	current_ap = data.get("current_ap", 6)
	max_hp = data.get("max_hp", 20)
	current_hp = data.get("current_hp", 20)
