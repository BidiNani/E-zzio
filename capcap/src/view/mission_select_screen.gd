class_name MissionSelectScreen
extends CanvasLayer

## MissionSelectScreen - Tactical Campaign Operations Browser with Visual Progress Bar, Threat Level & Records

signal mission_selected(mission_id: String)
signal reset_campaign_requested

var panel: PanelContainer
var mission_list_container: VBoxContainer
var detail_title: Label
var detail_threat: Label
var detail_briefing: Label
var detail_objectives: Label
var detail_squad: Label
var deploy_btn: Button
var reset_btn: Button
var progress_bar_label: Label
var footer_label: Label

var available_missions: Array = []
var selected_mission_id: String = "alpha_01"
var current_campaign_state = null

func _init() -> void:
	layer = 25

func _ready() -> void:
	build_ui()

func build_ui() -> void:
	panel = PanelContainer.new()
	panel.set_anchors_preset(Control.PRESET_FULL_RECT)
	panel.offset_left = 30
	panel.offset_top = 20
	panel.offset_right = -30
	panel.offset_bottom = -20

	var style = StyleBoxFlat.new()
	style.bg_color = Color(0.04, 0.06, 0.09, 0.98)
	style.border_color = Color(0.2, 0.5, 0.8, 0.8)
	style.set_border_width_all(2)
	style.set_corner_radius_all(8)
	panel.add_theme_stylebox_override("panel", style)
	add_child(panel)

	var margin = MarginContainer.new()
	margin.add_theme_constant_override("margin_left", 22)
	margin.add_theme_constant_override("margin_top", 16)
	margin.add_theme_constant_override("margin_right", 22)
	margin.add_theme_constant_override("margin_bottom", 16)
	panel.add_child(margin)

	var main_vbox = VBoxContainer.new()
	main_vbox.add_theme_constant_override("separation", 10)
	margin.add_child(main_vbox)

	# Header Title
	var header = Label.new()
	header.text = "★ CAPCAP — SÉLECTEUR DE CAMPAGNE TACTIQUE ★"
	header.add_theme_font_size_override("font_size", 20)
	header.add_theme_color_override("font_color", Color.GOLD)
	header.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	main_vbox.add_child(header)

	progress_bar_label = Label.new()
	progress_bar_label.text = "PROGRESSION DE LA CAMPAGNE : [ □□□□□□□□ ] 0% (0/3 Complétée)"
	progress_bar_label.add_theme_font_size_override("font_size", 12)
	progress_bar_label.add_theme_color_override("font_color", Color(0.4, 0.9, 1.0))
	progress_bar_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	main_vbox.add_child(progress_bar_label)

	var sep1 = HSeparator.new()
	main_vbox.add_child(sep1)

	# Split Body: Left List / Right Details
	var hbox = HBoxContainer.new()
	hbox.add_theme_constant_override("separation", 22)
	hbox.size_flags_vertical = Control.SIZE_EXPAND_FILL
	main_vbox.add_child(hbox)

	# Left Column: Missions List
	var left_vbox = VBoxContainer.new()
	left_vbox.custom_minimum_size = Vector2(330, 0)
	left_vbox.add_theme_constant_override("separation", 8)
	hbox.add_child(left_vbox)

	var list_title = Label.new()
	list_title.text = "OPÉRATIONS DISPONIBLES :"
	list_title.add_theme_font_size_override("font_size", 14)
	list_title.add_theme_color_override("font_color", Color(0.3, 0.8, 1.0))
	left_vbox.add_child(list_title)

	mission_list_container = VBoxContainer.new()
	mission_list_container.add_theme_constant_override("separation", 8)
	left_vbox.add_child(mission_list_container)

	# Right Column: Mission Details
	var right_panel = PanelContainer.new()
	right_panel.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var r_style = StyleBoxFlat.new()
	r_style.bg_color = Color(0.08, 0.11, 0.16, 0.8)
	r_style.set_corner_radius_all(6)
	right_panel.add_theme_stylebox_override("panel", r_style)
	hbox.add_child(right_panel)

	var r_margin = MarginContainer.new()
	r_margin.add_theme_constant_override("margin_left", 20)
	r_margin.add_theme_constant_override("margin_top", 14)
	r_margin.add_theme_constant_override("margin_right", 20)
	r_margin.add_theme_constant_override("margin_bottom", 14)
	right_panel.add_child(r_margin)

	var right_vbox = VBoxContainer.new()
	right_vbox.add_theme_constant_override("separation", 8)
	r_margin.add_child(right_vbox)

	detail_title = Label.new()
	detail_title.text = "Détails de l'opération"
	detail_title.add_theme_font_size_override("font_size", 16)
	detail_title.add_theme_color_override("font_color", Color(0.95, 0.85, 0.2))
	right_vbox.add_child(detail_title)

	detail_threat = Label.new()
	detail_threat.text = "NIVEAU DE MENACE : ★☆☆ (Standard)"
	detail_threat.add_theme_font_size_override("font_size", 12)
	detail_threat.add_theme_color_override("font_color", Color(1.0, 0.4, 0.4))
	right_vbox.add_child(detail_threat)

	detail_briefing = Label.new()
	detail_briefing.text = "Briefing..."
	detail_briefing.add_theme_font_size_override("font_size", 12)
	detail_briefing.add_theme_color_override("font_color", Color.WHITE)
	detail_briefing.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	right_vbox.add_child(detail_briefing)

	var sep2 = HSeparator.new()
	right_vbox.add_child(sep2)

	detail_objectives = Label.new()
	detail_objectives.text = "Objectifs..."
	detail_objectives.add_theme_font_size_override("font_size", 12)
	detail_objectives.add_theme_color_override("font_color", Color(0.8, 0.9, 1.0))
	right_vbox.add_child(detail_objectives)

	detail_squad = Label.new()
	detail_squad.text = "Escouade..."
	detail_squad.add_theme_font_size_override("font_size", 12)
	detail_squad.add_theme_color_override("font_color", Color(0.7, 0.8, 0.9))
	right_vbox.add_child(detail_squad)

	var spacer = Control.new()
	spacer.size_flags_vertical = Control.SIZE_EXPAND_FILL
	right_vbox.add_child(spacer)

	# Footer Stats
	footer_label = Label.new()
	footer_label.text = "STATISTIQUES : Victoires : 0  |  Défaites : 0  |  Tours Totaux : 0"
	footer_label.add_theme_font_size_override("font_size", 12)
	footer_label.add_theme_color_override("font_color", Color(0.6, 0.9, 0.6))
	main_vbox.add_child(footer_label)

	# Bottom Buttons Row
	var b_box = HBoxContainer.new()
	b_box.add_theme_constant_override("separation", 12)
	main_vbox.add_child(b_box)

	deploy_btn = Button.new()
	deploy_btn.text = "  [ DÉPLOYER L'OPÉRATION SÉLECTIONNÉE (ESPACE) ]  "
	deploy_btn.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	deploy_btn.custom_minimum_size = Vector2(0, 40)
	deploy_btn.add_theme_font_size_override("font_size", 14)
	deploy_btn.pressed.connect(func(): emit_signal("mission_selected", selected_mission_id))
	b_box.add_child(deploy_btn)

	reset_btn = Button.new()
	reset_btn.text = "  [ RÉINITIALISER LA CAMPAGNE ]  "
	reset_btn.custom_minimum_size = Vector2(200, 40)
	reset_btn.add_theme_font_size_override("font_size", 12)
	reset_btn.pressed.connect(func(): emit_signal("reset_campaign_requested"))
	b_box.add_child(reset_btn)

func update_campaign_view(missions: Array, campaign_state) -> void:
	available_missions = missions
	current_campaign_state = campaign_state

	for child in mission_list_container.get_children():
		child.queue_free()

	for mis in missions:
		var mis_id = mis["id"]
		var btn = Button.new()
		var is_unlocked = campaign_state.is_mission_unlocked(mis_id) if campaign_state else true
		var is_completed = campaign_state.is_mission_completed(mis_id) if campaign_state else false

		var rec = campaign_state.mission_records.get(mis_id, {}) if campaign_state else {}
		var best_turns = rec.get("best_turns", 0)

		var label_text = ""
		if is_completed:
			label_text = "✓ " + mis["title"] + (" (Record: %d T)" % best_turns if best_turns > 0 else "")
			btn.add_theme_color_override("font_color", Color(0.4, 0.95, 0.4))
		elif is_unlocked:
			label_text = "▶ " + mis["title"] + " [DISPONIBLE]"
			btn.add_theme_color_override("font_color", Color.WHITE)
		else:
			label_text = "🔒 " + mis["title"] + " [VERROUILLÉE]"
			btn.add_theme_color_override("font_color", Color(0.55, 0.55, 0.55))

		btn.text = "  " + label_text + "  "
		btn.add_theme_font_size_override("font_size", 12)
		btn.alignment = HORIZONTAL_ALIGNMENT_LEFT
		btn.pressed.connect(func(): select_mission(mis_id))
		mission_list_container.add_child(btn)

	# Update Progress Bar & Footer
	if campaign_state:
		var completed_count = campaign_state.completed_missions.size()
		var total_count = missions.size()
		var pct = int((float(completed_count) / float(max(1, total_count))) * 100.0)

		var bar = ""
		for i in range(total_count):
			bar += "■ " if i < completed_count else "□ "

		progress_bar_label.text = "PROGRESSION DE LA CAMPAGNE : [ %s] %d%% (%d/%d Opérations Complétées)" % [bar, pct, completed_count, total_count]

		var st = campaign_state.stats
		footer_label.text = "STATISTIQUES GLOBALES : Victoires : %d  |  Défaites : %d  |  Tours Totaux : %d  |  Ennemis Éliminés : %d" % [st.get("victories", 0), st.get("defeats", 0), st.get("total_turns", 0), st.get("total_enemies_killed", 0)]

	if missions.size() > 0:
		select_mission(missions[0]["id"])

func select_mission(mis_id: String) -> void:
	selected_mission_id = mis_id
	var is_unlocked = current_campaign_state.is_mission_unlocked(mis_id) if current_campaign_state else true
	var is_completed = current_campaign_state.is_mission_completed(mis_id) if current_campaign_state else false

	for mis in available_missions:
		if mis["id"] == mis_id:
			var status_str = " (DISPONIBLE)" if is_unlocked else " [VERROUILLÉE 🔒]"
			if is_completed:
				status_str = " [COMPLÉTÉE ✓]"
			detail_title.text = "OPÉRATION : " + mis["title"].to_upper() + status_str

			if mis_id == "alpha_01":
				detail_threat.text = "NIVEAU DE MENACE : ★☆☆ (Reconnaissance)"
			elif mis_id == "bravo_01":
				detail_threat.text = "NIVEAU DE MENACE : ★★☆ (Embuscade & Extraction)"
			else:
				detail_threat.text = "NIVEAU DE MENACE : ★★★ (Bastion Hautement Fortifié)"

			detail_briefing.text = mis["briefing"]

			var obj_txt = "OBJECTIFS PRINCIPAUX :\n"
			for obj in mis.get("objectives", []):
				obj_txt += "  • " + obj.get("title", "") + "\n"
			obj_txt += "  • Limite maximale : %d tours" % mis.get("max_turns", 15)
			detail_objectives.text = obj_txt

			var player_count = 0
			var enemy_count = 0
			for u in mis.get("units", []):
				if u.get("team", "") == "Player":
					player_count += 1
				else:
					enemy_count += 1
			detail_squad.text = "FORCES EN PRÉSENCE :\n  • Escouade Alliée : %d unités\n  • Garnison Ennemie : %d unités\n  • Carte : %dx%d cellules" % [player_count, enemy_count, mis.get("map_width", 16), mis.get("map_height", 16)]
			break

	if is_unlocked:
		deploy_btn.text = "  [ DÉPLOYER L'OPÉRATION SÉLECTIONNÉE (ESPACE) ]  "
		deploy_btn.disabled = false
	else:
		deploy_btn.text = "  [ OPÉRATION VERROUILLÉE (Accomplissez la mission précédente) ]  "
		deploy_btn.disabled = true

func show_screen() -> void:
	panel.visible = true

func hide_screen() -> void:
	panel.visible = false
