class_name GameManager
extends Node2D

@onready var player: PlayerController = $Player
@onready var enemy: EnemyAI = $Enemy
@onready var hud: MobileHUD = $HUD

func _ready() -> void:
	print("==================================================")
	print("🎮 ARPG Mobile Prototype (Godot 4.x) Initialisé !")
	print("==================================================")
	
	if player and hud:
		player.stats_updated.connect(hud.update_stats)
		if hud.joystick:
			hud.joystick.joystick_moved.connect(player.set_joystick_direction)
		hud.attack_pressed.connect(player.perform_attack)
	
	if enemy and player:
		enemy.target = player
		enemy.enemy_defeated.connect(_on_enemy_defeated)

func _on_enemy_defeated(pos: Vector2) -> void:
	print("[GAME_MANAGER] Ennemi terrassé en position : ", pos)

func execute_automated_slice_test() -> Dictionary:
	var results = {
		"player_init": false,
		"player_attack": false,
		"enemy_hit": false,
		"enemy_defeated": false,
		"loot_collected": false,
		"stats_updated": false
	}
	
	if player and player.stats.current_health > 0:
		results["player_init"] = true
	
	if enemy and player:
		var initial_hp = enemy.stats.current_health
		enemy.receive_hit(player.stats.attack_damage, player)
		if enemy.stats.current_health < initial_hp:
			results["enemy_hit"] = true
		
		# Achèvement de l'ennemi
		enemy.receive_hit(150, player)
		results["enemy_defeated"] = enemy.is_dead
	
	if player:
		var loot_res = LootItem.new()
		loot_res.gold_value = 50
		loot_res.xp_value = 100
		var initial_gold = player.total_gold
		player.collect_loot(loot_res)
		if player.total_gold > initial_gold:
			results["loot_collected"] = true
			results["stats_updated"] = true
	
	return results
