class_name LootDrop
extends Area2D

@export var loot_data: LootItem

@onready var sprite: Sprite2D = $Sprite2D

var target_player: PlayerController = null
var is_collected: bool = false

func _ready() -> void:
	if not loot_data:
		loot_data = LootItem.new()
	body_entered.connect(_on_body_entered)

func _physics_process(delta: float) -> void:
	if target_player and not is_collected:
		var dir = (target_player.global_position - global_position).normalized()
		global_position += dir * 350.0 * delta
		if global_position.distance_to(target_player.global_position) < 25.0:
			collect()

func _on_body_entered(body: Node2D) -> void:
	if body is PlayerController and not is_collected:
		target_player = body
		collect()

func collect() -> void:
	if is_collected:
		return
	is_collected = true
	if target_player:
		target_player.collect_loot(loot_data)
	queue_free()
