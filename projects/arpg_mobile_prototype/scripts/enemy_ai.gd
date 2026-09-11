class_name EnemyAI
extends CharacterBody2D

signal enemy_defeated(position: Vector2)

@export var stats: CharacterStats
@export var target: Node2D
@export var loot_scene: PackedScene

@onready var sprite: Sprite2D = $Sprite2D
@onready var hp_bar: ProgressBar = $HPBar

var is_dead: bool = false

func _ready() -> void:
	if not stats:
		stats = CharacterStats.new()
		stats.character_name = "Shadow Goblin"
		stats.max_health = 60
		stats.attack_damage = 10
		stats.move_speed = 120.0
	stats.initialize()
	if hp_bar:
		hp_bar.max_value = stats.max_health
		hp_bar.value = stats.current_health

func _physics_process(_delta: float) -> void:
	if is_dead or not target:
		return
	
	var dist = global_position.distance_to(target.global_position)
	if dist > 60.0 and dist < 450.0:
		var dir = (target.global_position - global_position).normalized()
		velocity = dir * stats.move_speed
		move_and_slide()
	else:
		velocity = Vector2.ZERO

func receive_hit(damage: int, _attacker: Node2D) -> void:
	if is_dead:
		return
	var _taken = stats.take_damage(damage)
	if hp_bar:
		hp_bar.value = stats.current_health
	
	if is_inside_tree() and get_tree():
		modulate = Color(1.8, 0.4, 0.4, 1.0)
		await get_tree().create_timer(0.1).timeout
		modulate = Color(1.0, 1.0, 1.0, 1.0)
	
	if stats.current_health <= 0:
		die()

func die() -> void:
	if is_dead:
		return
	is_dead = true
	var drop_pos = global_position
	enemy_defeated.emit(drop_pos)
	
	if loot_scene and is_inside_tree() and get_parent():
		var drop = loot_scene.instantiate()
		drop.global_position = drop_pos
		get_parent().add_child(drop)
	
	if is_inside_tree():
		queue_free()
