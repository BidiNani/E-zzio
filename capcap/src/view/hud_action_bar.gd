class_name HUDActionBar
extends CanvasLayer

## HUDActionBar - Modern Tactical HUD with Unit Card, AP Beads, Action Buttons & Top Objective Bar

signal end_turn_requested
signal action_button_pressed(action_type: String)

var top_bar: PanelContainer
var turn_label: Label
var objective_label: Label
var end_turn_btn: Button

var bottom_bar: PanelContainer
var unit_card: VBoxContainer
var name_label: Label
var stats_label: Label
var ap_container: HBoxContainer

var actions_container: HBoxContainer
var btn_move: Button
var btn_attack: Button
var btn_overwatch: Button
var btn_wait: Button

var banner_label: Label

func _init() -> void:
	layer = 10

func _ready() -> void:
	build_ui()

func build_ui() -> void:
	# 1. Top Navigation Bar
	top_bar = PanelContainer.new()
	top_bar.set_anchors_preset(Control.PRESET_TOP_WIDE)
	top_bar.offset_left = 16
	top_bar.offset_top = 12
	top_bar.offset_right = -16
	top_bar.offset_bottom = 54
	add_child(top_bar)

	var top_box = HBoxContainer.new()
	top_box.alignment = BoxContainer.ALIGNMENT_BEGIN
	top_bar.add_child(top_box)

	turn_label = Label.new()
	turn_label.text = "TOUR 1 — TOUR JOUEUR"
	turn_label.add_theme_font_size_override("font_size", 16)
	turn_label.add_theme_color_override("font_color", Color(0.95, 0.85, 0.2))
	top_box.add_child(turn_label)

	var spacer1 = Control.new()
	spacer1.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	top_box.add_child(spacer1)

	objective_label = Label.new()
	objective_label.text = "OBJECTIF : ÉLIMINATION & PRISE DE PLATEAU"
	objective_label.add_theme_font_size_override("font_size", 14)
	objective_label.add_theme_color_override("font_color", Color(0.8, 0.9, 1.0))
	top_box.add_child(objective_label)

	var spacer2 = Control.new()
	spacer2.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	top_box.add_child(spacer2)

	end_turn_btn = Button.new()
	end_turn_btn.text = "  FIN DE TOUR (E)  "
	end_turn_btn.add_theme_font_size_override("font_size", 14)
	end_turn_btn.pressed.connect(func(): emit_signal("end_turn_requested"))
	top_box.add_child(end_turn_btn)

	# 2. Bottom Action & Unit Bar
	bottom_bar = PanelContainer.new()
	bottom_bar.set_anchors_preset(Control.PRESET_BOTTOM_WIDE)
	bottom_bar.offset_left = 20
	bottom_bar.offset_top = -80
	bottom_bar.offset_right = -20
	bottom_bar.offset_bottom = -16
	add_child(bottom_bar)

	var bot_box = HBoxContainer.new()
	bot_box.alignment = BoxContainer.ALIGNMENT_BEGIN
	bottom_bar.add_child(bot_box)

	unit_card = VBoxContainer.new()
	unit_card.custom_minimum_size = Vector2(280, 0)
	bot_box.add_child(unit_card)

	name_label = Label.new()
	name_label.text = "SÉLECTION : AUCUNE UNITÉ"
	name_label.add_theme_font_size_override("font_size", 14)
	name_label.add_theme_color_override("font_color", Color.WHITE)
	unit_card.add_child(name_label)

	stats_label = Label.new()
	stats_label.text = "PV : --/--  |  AP : --/--"
	stats_label.add_theme_font_size_override("font_size", 12)
	stats_label.add_theme_color_override("font_color", Color(0.7, 0.8, 0.9))
	unit_card.add_child(stats_label)

	var spacer3 = Control.new()
	spacer3.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	bot_box.add_child(spacer3)

	# Action Buttons
	actions_container = HBoxContainer.new()
	actions_container.add_theme_constant_override("separation", 10)
	bot_box.add_child(actions_container)

	btn_move = create_action_btn("DÉPLACEMENT", "move")
	btn_attack = create_action_btn("ATTAQUER (2 AP)", "attack")
	btn_overwatch = create_action_btn("OVERWATCH (2 AP)", "overwatch")
	btn_wait = create_action_btn("ATTENDRE", "wait")

	# Banner (Victory / Defeat)
	banner_label = Label.new()
	banner_label.set_anchors_preset(Control.PRESET_CENTER)
	banner_label.offset_left = -200
	banner_label.offset_top = -40
	banner_label.offset_right = 200
	banner_label.offset_bottom = 40
	banner_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	banner_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	banner_label.add_theme_font_size_override("font_size", 32)
	banner_label.visible = false
	add_child(banner_label)

func create_action_btn(label: String, action_id: String) -> Button:
	var btn = Button.new()
	btn.text = "  " + label + "  "
	btn.add_theme_font_size_override("font_size", 12)
	btn.pressed.connect(func(): emit_signal("action_button_pressed", action_id))
	actions_container.add_child(btn)
	return btn

func update_turn(turn: int, team: String) -> void:
	if turn_label:
		turn_label.text = "TOUR %d — TOUR %s" % [turn, "JOUEUR" if team == "Player" else "ENNEMI (IA)"]
		turn_label.add_theme_color_override("font_color", Color(0.95, 0.85, 0.2) if team == "Player" else Color(0.95, 0.3, 0.3))

func update_selection(selected_units: Array) -> void:
	if selected_units.size() == 0:
		name_label.text = "SÉLECTION : AUCUNE UNITÉ"
		stats_label.text = "Cliquez sur une unité alliée pour donner un ordre."
		btn_move.disabled = true
		btn_attack.disabled = true
		btn_overwatch.disabled = true
		btn_wait.disabled = true
	elif selected_units.size() == 1:
		var u = selected_units[0]
		name_label.text = "[ %s ]  Rôle : %s" % [u.unit_name.to_upper(), u.unit_name]
		var ap_dots = ""
		for i in range(u.stats.current_ap):
			ap_dots += "●"
		for i in range(u.stats.max_ap - u.stats.current_ap):
			ap_dots += "○"
		stats_label.text = "PV : %d/%d  |  AP : %s (%d/%d)" % [u.stats.current_hp, u.stats.max_hp, ap_dots, u.stats.current_ap, u.stats.max_ap]
		btn_move.disabled = (u.stats.current_ap < 1)
		btn_attack.disabled = (u.stats.current_ap < 2)
		btn_overwatch.disabled = (u.stats.current_ap < 2 or u.is_overwatch)
		btn_wait.disabled = false
	else:
		name_label.text = "SÉLECTION MULTIPLE : %d UNITÉS" % selected_units.size()
		stats_label.text = "Formation en grille prête. Clic droit pour déplacer le groupe."
		btn_move.disabled = false
		btn_attack.disabled = false
		btn_overwatch.disabled = false
		btn_wait.disabled = false

func show_match_verdict(match_state: int) -> void:
	if match_state == 1: # VICTORY_PLAYER
		banner_label.text = "★ VICTOIRE DE MISSION ★\nOBJECTIFS ATTEINTS"
		banner_label.add_theme_color_override("font_color", Color.GOLD)
		banner_label.visible = true
	elif match_state == 2: # DEFEAT_PLAYER
		banner_label.text = "☠ DÉFAITE TACTIQUE ☠\nESCOUADE NEUTRALISÉE"
		banner_label.add_theme_color_override("font_color", Color.RED)
		banner_label.visible = true
