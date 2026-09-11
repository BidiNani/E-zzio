extends Node2D

@onready var player: Player = $Player

func _ready() -> void:
    if player:
        player.health_changed.connect(_on_player_health_changed)
        player.player_died.connect(_on_player_died)
    print("Jeu Godot initialisé avec architecture découplée.")

func _on_player_health_changed(new_health: int) -> void:
    print("Santé du joueur : ", new_health)

func _on_player_died() -> void:
    print("Partie terminée.")
