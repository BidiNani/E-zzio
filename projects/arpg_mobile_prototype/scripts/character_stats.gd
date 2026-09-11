class_name CharacterStats
extends Resource

signal health_changed(current: int, max_hp: int)
signal died
signal level_changed(new_level: int)

@export var character_name: String = "Hero"
@export var max_health: int = 100
@export var current_health: int = 100
@export var attack_damage: int = 25
@export var move_speed: float = 280.0
@export var level: int = 1
@export var experience: int = 0

func initialize() -> void:
	current_health = max_health
	health_changed.emit(current_health, max_health)

func take_damage(amount: int) -> int:
	var actual_damage = max(0, amount)
	current_health = max(0, current_health - actual_damage)
	health_changed.emit(current_health, max_health)
	if current_health == 0:
		died.emit()
	return actual_damage

func heal(amount: int) -> void:
	current_health = min(max_health, current_health + amount)
	health_changed.emit(current_health, max_health)

func add_experience(amount: int) -> void:
	experience += amount
	if experience >= level * 100:
		level += 1
		max_health += 20
		attack_damage += 5
		current_health = max_health
		level_changed.emit(level)
		health_changed.emit(current_health, max_health)
