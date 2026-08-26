class_name MissionResultsScreen
extends CanvasLayer

## MissionResultsScreen - Debriefing overlay with Unlock Alerts, Record Badges and Campaign Flow

signal restart_mission_requested
signal return_to_menu_requested

var panel: PanelContainer
var title_label: Label
var stats_label: Label
var unlock_banner: PanelContainer
var unlock_label: Label
var restart_btn: Button
var continue_btn: Button

func _init() -> void:
	layer = 20

func _ready() -> void:
	build_ui()

func build_ui() -> void:
	panel = PanelContainer.new()
	panel.set_anchors_preset(Control.PRESET_CENTER)
	panel.offset_left = -300
	panel.offset_top = -220
	panel.offset_right = 300
	panel.offset_bottom = 220
	panel.visible = false

	var style = StyleBoxFlat.new()
	style.bg_color = Color(0.04, 0.06, 0.09, 0.98)
	style.border_color = Color(0.9, 0.7, 0.2, 0.9)
	style.set_border_width_all(2)
	style.set_corner_radius_all(8)
	panel.add_theme_stylebox_override("panel", style)
	add_child(panel)

	var margin = MarginContainer.new()
	margin.add_theme_constant_override("margin_left", 24)
	margin.add_theme_constant_override("margin_top", 18)
	margin.add_theme_constant_override("margin_right", 24)
	margin.add_theme_constant_override("margin_bottom", 18)
	panel.add_child(margin)

	var vbox = VBoxContainer.new()
	vbox.add_theme_constant_override("separation", 10)
	margin.add_child(vbox)

	title_label = Label.new()
	title_label.text = "★ VICTOIRE DE MISSION ★"
	title_label.add_theme_font_size_override("font_size", 20)
	title_label.add_theme_color_override("font_color", Color.GOLD)
	title_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	vbox.add_child(title_label)

	var sep = HSeparator.new()
	vbox.add_child(sep)

	stats_label = Label.new()
	stats_label.text = "Bilan opérationnel..."
	stats_label.add_theme_font_size_override("font_size", 13)
	stats_label.add_theme_color_override("font_color", Color.WHITE)
	vbox.add_child(stats_label)

	# Unlock Notification Banner
	unlock_banner = PanelContainer.new()
	var u_style = StyleBoxFlat.new()
	u_style.bg_color = Color(0.12, 0.22, 0.15, 0.95)
	u_style.border_color = Color(0.3, 0.9, 0.4, 0.9)
	u_style.set_border_width_all(2)
	u_style.set_corner_radius_all(6)
	unlock_banner.add_theme_stylebox_override("panel", u_style)
	vbox.add_child(unlock_banner)

	var u_margin = MarginContainer.new()
	u_margin.add_theme_constant_override("margin_left", 12)
	u_margin.add_theme_constant_override("margin_top", 8)
	u_margin.add_theme_constant_override("margin_right", 12)
	u_margin.add_theme_constant_override("margin_bottom", 8)
	unlock_banner.add_child(u_margin)

	unlock_label = Label.new()
	unlock_label.text = "★ NOUVELLE OPÉRATION DÉBLOQUÉE ★\n▶ BRAVO 01 — CANYON ENCLAVÉ"
	unlock_label.add_theme_font_size_override("font_size", 13)
	unlock_label.add_theme_color_override("font_color", Color(0.4, 1.0, 0.5))
	unlock_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	u_margin.add_child(unlock_label)

	var spacer = Control.new()
	spacer.size_flags_vertical = Control.SIZE_EXPAND_FILL
	vbox.add_child(spacer)

	var btn_box = HBoxContainer.new()
	btn_box.add_theme_constant_override("separation", 10)
	vbox.add_child(btn_box)

	continue_btn = Button.new()
	continue_btn.text = "  CONTINUER VERS LA CAMPAGNE (ESPACE / C)  "
	continue_btn.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	continue_btn.custom_minimum_size = Vector2(0, 38)
	continue_btn.add_theme_font_size_override("font_size", 13)
	continue_btn.pressed.connect(func(): emit_signal("return_to_menu_requested"))
	btn_box.add_child(continue_btn)

	restart_btn = Button.new()
	restart_btn.text = "  REJOUER (R)  "
	restart_btn.custom_minimum_size = Vector2(110, 38)
	restart_btn.add_theme_font_size_override("font_size", 13)
	restart_btn.pressed.connect(func(): emit_signal("restart_mission_requested"))
	btn_box.add_child(restart_btn)

func show_results(mission_mgr, eval_report: Dictionary = {}) -> void:
	if mission_mgr.is_victory:
		title_label.text = "★ MISSION ACCOMPLIE ★\nOBJECTIFS TACTIQUES SÉCURISÉS"
		title_label.add_theme_color_override("font_color", Color.GOLD)
	else:
		title_label.text = "☠ ÉCHEC TACTIQUE ☠\nESCOUADE NEUTRALISÉE"
		title_label.add_theme_color_override("font_color", Color.RED)

	var is_record = eval_report.get("is_new_record", false)
	var record_tag = "  [★ NOUVEAU RECORD PERSONNEL !]" if is_record else ""

	var txt = "BILAN OPÉRATIONNEL :\n"
	txt += "  • Durée de l'assaut : %d tours (Limite : %d)%s\n" % [mission_mgr.turns_elapsed, mission_mgr.max_turns, record_tag]
	txt += "  • Ennemis neutralisés : %d\n" % mission_mgr.enemies_killed
	txt += "  • Dégâts totaux infligés : %d PV\n" % mission_mgr.damage_dealt
	txt += "  • Dégâts subis par l'escouade : %d PV" % mission_mgr.damage_taken
	stats_label.text = txt

	var newly_unlocked = eval_report.get("newly_unlocked_id", "")
	if newly_unlocked != "":
		unlock_banner.visible = true
		var mis_name = "OPÉRATION SUIVANTE"
		if newly_unlocked == "bravo_01":
			mis_name = "BRAVO 01 — CANYON ENCLAVÉ"
		elif newly_unlocked == "gamma_01":
			mis_name = "GAMMA 01 — RUINES FORTIFIÉES"
		unlock_label.text = "★ NOUVELLE OPÉRATION DÉBLOQUÉE ★\n▶ " + mis_name
	else:
		unlock_banner.visible = false

	panel.visible = true

func hide_results() -> void:
	panel.visible = false
