class_name MobileHUD
extends CanvasLayer

signal attack_pressed

@onready var hp_progress: ProgressBar = $MarginContainer/TopBar/HPBar
@onready var gold_label: Label = $MarginContainer/TopBar/GoldLabel
@onready var level_label: Label = $MarginContainer/TopBar/LevelLabel
@onready var joystick: TouchVirtualJoystick = $MarginContainer/BottomControls/VirtualJoystick
@onready var attack_btn: TextureButton = $MarginContainer/BottomControls/AttackButton

func _ready() -> void:
	if attack_btn:
		attack_btn.pressed.connect(_on_attack_pressed)

func update_stats(current_hp: int, max_hp: int, gold: int, level: int) -> void:
	if hp_progress:
		hp_progress.max_value = max_hp
		hp_progress.value = current_hp
	if gold_label:
		gold_label.text = "💰 Or: %d" % gold
	if level_label:
		level_label.text = "⭐ Niv. %d" % level

func _on_attack_pressed() -> void:
	attack_pressed.emit()
