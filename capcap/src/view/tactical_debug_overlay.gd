class_name TacticalDebugOverlay
extends CanvasLayer

## TacticalDebugOverlay - Real-time state inspector toggled with F3 key

var is_visible_overlay: bool = true
var panel: PanelContainer
var text_label: Label

func _init() -> void:
	layer = 15

func _ready() -> void:
	panel = PanelContainer.new()
	panel.offset_left = 16
	panel.offset_top = 64
	panel.offset_right = 320
	panel.offset_bottom = 380
	panel.visible = is_visible_overlay
	add_child(panel)

	text_label = Label.new()
	text_label.add_theme_font_size_override("font_size", 11)
	text_label.add_theme_color_override("font_color", Color(0.3, 1.0, 0.4)) # Terminal green
	panel.add_child(text_label)

func toggle() -> void:
	is_visible_overlay = not is_visible_overlay
	panel.visible = is_visible_overlay

func update_debug_info(game_state, selected_units: Array, hovered_pos: Vector2i, hovered_elev: int, hovered_walkable: bool, combat_info: Dictionary) -> void:
	if not is_visible_overlay or not text_label:
		return

	var txt = "=== CAPCAP REAL-TIME DEBUG (F3) ===\n"
	txt += "TOUR        : %d  |  ÉQUIPE : %s\n" % [game_state.turn_number, game_state.active_team]
	txt += "MATCH STATE : %s\n" % ["EN COURS (0)" if game_state.match_state == 0 else ("VICTOIRE (1)" if game_state.match_state == 1 else "DÉFAITE (2)")]
	txt += "-----------------------------------\n"

	if selected_units.size() > 0:
		var u = selected_units[0]
		txt += "SÉLECTION   : %s (%s)\n" % [u.unit_name, u.unit_id]
		txt += "POSITION    : (%d, %d, z=%d)\n" % [u.grid_pos.x, u.grid_pos.y, u.current_elevation]
		txt += "PV / AP     : %d/%d  |  %d/%d AP\n" % [u.stats.current_hp, u.stats.max_hp, u.stats.current_ap, u.stats.max_ap]
		txt += "OVERWATCH   : %s  |  ÉTAT : %s\n" % ["ACTIF" if u.is_overwatch else "NON", str(u.state)]
	else:
		txt += "SÉLECTION   : Aucune unité\n"

	txt += "-----------------------------------\n"
	txt += "SURVOL CASE : (%d, %d, z=%d)\n" % [hovered_pos.x, hovered_pos.y, hovered_elev]
	txt += "PRATICABLE  : %s\n" % ["OUI" if hovered_walkable else "BLOQUÉ"]

	if combat_info.has("target_id"):
		txt += "-----------------------------------\n"
		txt += "CIBLE COMBAT: %s (Dist: %.1f)\n" % [combat_info.get("target_name", ""), combat_info.get("dist", 0.0)]
		txt += "LOS / VUE   : %s\n" % ["DÉGAGÉE" if combat_info.get("has_los", false) else "BLOQUÉE"]
		txt += "COUVERT     : %s (-%d dégâts)\n" % [combat_info.get("cover_type", "NONE"), combat_info.get("mitigation", 0)]
		txt += "DÉGÂTS EST. : %d PV\n" % combat_info.get("est_damage", 0)

	text_label.text = txt
