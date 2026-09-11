class_name Player
extends CharacterBody2D

signal health_changed(new_health: int)
signal player_died

@export var config: GameConfig
var current_health: int = 100

func _ready() -> void:
    if config:
        current_health = config.max_health

func take_damage(amount: int) -> void:
    current_health = max(0, current_health - amount)
    health_changed.emit(current_health)
    if current_health == 0:
        player_died.emit()
