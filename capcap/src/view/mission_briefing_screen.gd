class_name MissionBriefingScreen
extends CanvasLayer

## MissionBriefingScreen - Tactical briefing overlay with objectives, squad info and launch button

signal start_mission_requested

var panel: PanelContainer
var start_btn: Button

func _init() -> void:
	layer = 20

func _ready() -> void:
	build_ui()

func build_ui() -> void:
	panel = PanelContainer.new()
	panel.set_anchors_preset(Control.PRESET_FULL_RECT)
	panel.offset_left = 60
	panel.offset_top = 40
	panel.offset_right = -60
	panel.offset_bottom = -40

	var style = StyleBoxFlat.new()
	style.bg_color = Color(0.05, 0.07, 0.10, 0.96)
	style.border_color = Color(0.3, 0.6, 0.9, 0.8)
	style.set_border_width_all(2)
	style.set_corner_radius_all(8)
	panel.add_theme_stylebox_override("panel", style)
	add_child(panel)

	var margin = MarginContainer.new()
	margin.add_theme_constant_override("margin_left", 30)
	margin.add_theme_constant_override("margin_top", 25)
	margin.add_theme_constant_override("margin_right", 30)
	margin.add_theme_constant_override("margin_bottom", 25)
	panel.add_child(margin)

	var vbox = VBoxContainer.new()
	vbox.add_theme_constant_override("separation", 16)
	margin.add_child(vbox)

	# Title
	var title = Label.new()
	title.text = "★ BRIEFING TACTIQUE : OPÉRATION AVANT-POSTE ALPHA ★"
	title.add_theme_font_size_override("font_size", 20)
	title.add_theme_color_override("font_color", Color.GOLD)
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	vbox.add_child(title)

	var desc = Label.new()
	desc.text = "Un avant-poste ennemi a été établi sur le plateau surélevé (altitude z=2).\nVotre escouade d'assaut doit s'infiltrer sous couvert, sécuriser le relais d'antenne et éliminer le commandement orc."
	desc.add_theme_font_size_override("font_size", 13)
	desc.add_theme_color_override("font_color", Color(0.85, 0.9, 0.95))
	desc.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	vbox.add_child(desc)

	var sep = HSeparator.new()
	vbox.add_child(sep)

	# Objectives List
	var obj_header = Label.new()
	obj_header.text = "OBJECTIFS DE MISSION :"
	obj_header.add_theme_font_size_override("font_size", 14)
	obj_header.add_theme_color_override("font_color", Color(0.3, 0.8, 1.0))
	vbox.add_child(obj_header)

	var obj_list = Label.new()
	obj_list.text = "  [1] Sécuriser l'antenne sur le plateau en case (6, 6)\n  [2] Éliminer le Commandant Orc retranché\n  [!] Éviter l'anéantissement de l'escouade (Limite : 15 Tours)"
	obj_list.add_theme_font_size_override("font_size", 13)
	obj_list.add_theme_color_override("font_color", Color.WHITE)
	vbox.add_child(obj_list)

	# Squad List
	var squad_header = Label.new()
	squad_header.text = "COMPOSITION DE L'ESCOUADE ALLIÉE :"
	squad_header.add_theme_font_size_override("font_size", 14)
	squad_header.add_theme_color_override("font_color", Color(0.3, 0.8, 1.0))
	vbox.add_child(squad_header)

	var squad_list = Label.new()
	squad_list.text = "  • Vanguard 01 : Assaut Lourd (20 PV, 6 AP, Bouclier)\n  • Vanguard 02 : Flanqueur Tactique (20 PV, 6 AP, Bouclier)\n  • Sniper 01   : Tir longue distance & Overwatch (15 PV, 5 AP, Portée 8)"
	squad_list.add_theme_font_size_override("font_size", 13)
	squad_list.add_theme_color_override("font_color", Color(0.9, 0.9, 0.9))
	vbox.add_child(squad_list)

	var spacer = Control.new()
	spacer.size_flags_vertical = Control.SIZE_EXPAND_FILL
	vbox.add_child(spacer)

	# Launch Button
	start_btn = Button.new()
	start_btn.text = "  [ DÉPLOYER L'ESCOUADE TACTIQUE (ESPACE) ]  "
	start_btn.custom_minimum_size = Vector2(0, 42)
	start_btn.add_theme_font_size_override("font_size", 15)
	start_btn.pressed.connect(func(): emit_signal("start_mission_requested"))
	vbox.add_child(start_btn)
