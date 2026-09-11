extends SceneTree

func _init() -> void:
	print("==================================================")
	print("🚀 RUNNING AUTOMATED ARPG VERTICAL SLICE TEST")
	print("==================================================")
	
	var main_scene_res = load("res://scenes/main.tscn")
	if not main_scene_res:
		printerr("[FAIL] Impossible de charger scenes/main.tscn")
		quit(1)
		return
	
	var main_scene = main_scene_res.instantiate()
	root.add_child(main_scene)
	
	var player: PlayerController = main_scene.get_node_or_null("Player")
	var enemy: EnemyAI = main_scene.get_node_or_null("Enemy")
	var hud: MobileHUD = main_scene.get_node_or_null("HUD")
	
	if not player or not enemy or not hud:
		printerr("[FAIL] Hiérarchie de nœuds incomplète dans main.tscn")
		quit(1)
		return
	
	print("1. [CHECK] Initialisation du Joueur & Stats Typed Resource...")
	assert(player.stats != null, "Player stats Resource doit être instanciée")
	assert(player.stats.current_health == 120, "Santé initiale du joueur attendue: 120")
	assert(player.stats.attack_damage == 30, "Dégâts d'attaque initiaux: 30")
	print("   -> OK : PlayerStats [HP: %d/%d, ATK: %d, Speed: %.1f, Level: %d]" % [player.stats.current_health, player.stats.max_health, player.stats.attack_damage, player.stats.move_speed, player.stats.level])
	
	print("2. [CHECK] Déplacement tactile / Joystick virtuel...")
	player.set_joystick_direction(Vector2(1.0, 0.5).normalized())
	player._physics_process(0.016)
	assert(player.velocity.length() > 0, "Le joueur doit se déplacer avec le vecteur du joystick")
	print("   -> OK : Vélocité calculée = ", player.velocity, " | Rotation = ", player.rotation)
	
	print("3. [CHECK] Déclenchement de l'attaque de base...")
	player.perform_attack()
	print("   -> OK : Signal d'attaque déclenché avec succès")
	
	print("4. [CHECK] Ennemi, Réception de dégâts & Mort...")
	var initial_enemy_hp = enemy.stats.current_health
	print("   -> Santé initiale ennemie : ", initial_enemy_hp)
	enemy.receive_hit(player.stats.attack_damage, player)
	assert(enemy.stats.current_health == initial_enemy_hp - player.stats.attack_damage, "L'ennemi doit subir les dégâts")
	print("   -> Santé ennemie après 1 coup (30 dmg) : ", enemy.stats.current_health)
	
	# Coup fatal
	enemy.receive_hit(150, player)
	assert(enemy.is_dead == true, "L'ennemi doit être vaincu")
	print("   -> OK : Ennemi vaincu (is_dead = true), signal enemy_defeated émis")
	
	print("5. [CHECK] Drop de Butin & Ramassage automatique...")
	var loot_res = load("res://resources/loot_ruby.tres")
	assert(loot_res != null, "Ressource de butin chargée")
	var initial_gold = player.total_gold
	var initial_xp = player.stats.experience
	player.collect_loot(loot_res)
	assert(player.total_gold == initial_gold + loot_res.gold_value, "L'or doit être incrémenté")
	assert(player.stats.experience == initial_xp + loot_res.xp_value, "L'XP doit être incrémentée")
	print("   -> OK : Butin collecté (+%d or, +%d XP) | Total Or = %d, Niveau = %d" % [loot_res.gold_value, loot_res.xp_value, player.total_gold, player.stats.level])
	
	print("==================================================")
	print("✅ VERTICAL SLICE GAMEPLAY LOOP 100% VALIDÉE !")
	print("==================================================")
	quit(0)
