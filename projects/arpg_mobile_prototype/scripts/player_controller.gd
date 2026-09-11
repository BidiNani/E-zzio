class_name PlayerController
extends CharacterBody2D

signal attack_performed
signal stats_updated(current_hp: int, max_hp: int, gold: int, level: int)

@export var stats: CharacterStats

@onready var sprite: Sprite2D = $Sprite2D
@onready var attack_area: Area2D = $AttackArea
@onready var attack_sprite: Sprite2D = $AttackArea/AttackSprite

var move_direction: Vector2 = Vector2.ZERO
var total_gold: int = 0
var is_attacking: bool = false

func _ready() -> void:
	if not stats:
		stats = CharacterStats.new()
	stats.initialize()
	stats.health_changed.connect(_on_health_changed)
	stats.died.connect(_on_died)
	if attack_sprite:
		attack_sprite.visible = false
	if attack_area:
		attack_area.monitoring = false
	_emit_stats()

func _physics_process(_delta: float) -> void:
	var input_dir = move_direction
	if input_dir == Vector2.ZERO:
		input_dir = Input.get_vector("ui_left", "ui_right", "ui_up", "ui_down")
	
	if input_dir.length() > 0.1:
		velocity = input_dir.normalized() * stats.move_speed
		rotation = lerp_angle(rotation, input_dir.angle(), 0.2)
	else:
		velocity = velocity.move_toward(Vector2.ZERO, 35.0)
	
	if is_inside_tree():
		move_and_slide()

func set_joystick_direction(dir: Vector2) -> void:
	move_direction = dir

func perform_attack() -> void:
	if is_attacking:
		return
	is_attacking = true
	attack_performed.emit()
	
	if attack_sprite:
		attack_sprite.visible = true
	if attack_area:
		attack_area.monitoring = true
		for body in attack_area.get_overlapping_bodies():
			if body.has_method("receive_hit") and body != self:
				body.receive_hit(stats.attack_damage, self)
	
	if is_inside_tree() and get_tree():
		await get_tree().create_timer(0.2).timeout
	if attack_sprite:
		attack_sprite.visible = false
	if attack_area:
		attack_area.monitoring = false
	is_attacking = false

func collect_loot(item: LootItem) -> void:
	total_gold += item.gold_value
	stats.add_experience(item.xp_value)
	stats.heal(item.heal_value)
	_emit_stats()

func _on_health_changed(_cur: int, _m: int) -> void:
	_emit_stats()

func _on_died() -> void:
	print("[PLAYER] Le joueur a succombé !")

func _emit_stats() -> void:
	stats_updated.emit(stats.current_health, stats.max_health, total_gold, stats.level)
