class_name MainScene
extends Node2D

const IsoMathScript = preload("res://src/core/iso_math.gd")
const GridMapScript = preload("res://src/core/grid_map.gd")
const AStarScript = preload("res://src/navigation/astar_pathfinder.gd")
const UnitScript = preload("res://src/entities/unit.gd")
const SelectionManagerScript = preload("res://src/selection/unit_selection_manager.gd")
const FormationSolverScript = preload("res://src/formation/formation_solver.gd")
const GridRendererScript = preload("res://src/view/iso_grid_renderer.gd")
const CursorScript = preload("res://src/view/iso_cursor.gd")
const IsoCameraScript = preload("res://src/view/iso_camera.gd")
const SelectionRendererScript = preload("res://src/view/selection_renderer.gd")
const GameStateScript = preload("res://src/state/game_state.gd")
const ActionQueueScript = preload("res://src/actions/action_queue.gd")
const MoveActionScript = preload("res://src/actions/move_action.gd")
const AttackActionScript = preload("res://src/actions/attack_action.gd")
const OverwatchActionScript = preload("res://src/actions/overwatch_action.gd")
const CombatRendererScript = preload("res://src/view/combat_renderer.gd")
const HUDScript = preload("res://src/view/hud_action_bar.gd")
const AIControllerScript = preload("res://src/ai/ai_controller.gd")
const VisibilityMapScript = preload("res://src/vision/visibility_map.gd")
const VisionSystemScript = preload("res://src/vision/vision_system.gd")
const FogRendererScript = preload("res://src/view/fog_renderer.gd")
const CoverSystemScript = preload("res://src/combat/cover_system.gd")
const CombatResolverScript = preload("res://src/combat/combat_resolver.gd")
const LineOfSight2DScript = preload("res://src/combat/line_of_sight_2d.gd")
const MissionObjectiveScript = preload("res://src/objectives/mission_objective.gd")
const DebugOverlayScript = preload("res://src/view/tactical_debug_overlay.gd")
const MissionManagerScript = preload("res://src/mission/mission_manager.gd")
const MissionRegistryScript = preload("res://src/loaders/mission_registry.gd")
const MissionLoaderScript = preload("res://src/loaders/mission_loader.gd")
const MissionSelectScreenScript = preload("res://src/view/mission_select_screen.gd")
const BriefingScreenScript = preload("res://src/view/mission_briefing_screen.gd")
const ResultsScreenScript = preload("res://src/view/mission_results_screen.gd")
const CampaignStateScript = preload("res://src/campaign/campaign_state.gd")
const CampaignEvaluatorScript = preload("res://src/campaign/campaign_evaluator.gd")

enum GameMode { MENU, BRIEFING, PLAYING, RESULTS }

@onready var camera = $Camera2D

var current_mode: GameMode = GameMode.MENU
var grid_map
var pathfinder
var grid_renderer
var fog_renderer
var cursor
var selection_mgr
var selection_renderer
var combat_renderer
var game_state
var action_queue
var hud
var debug_overlay
var player_visibility_map

var campaign_state
var mission_mgr
var mission_select_screen
var briefing_screen
var results_screen

var current_mission_id: String = "alpha_01"
var is_box_selecting: bool = false
var box_start_screen: Vector2 = Vector2.ZERO
var box_current_screen: Vector2 = Vector2.ZERO

var hovered_grid: Vector2i = Vector2i.ZERO
var hovered_elev: int = 0
var is_hovered_walkable: bool = true
var combat_debug_info: Dictionary = {}

var frame_count: int = 0
var screenshot_taken: bool = false

func _ready() -> void:
	campaign_state = CampaignStateScript.new()
	campaign_state.load_from_file()

	mission_mgr = MissionManagerScript.new()

	mission_select_screen = MissionSelectScreenScript.new()
	add_child(mission_select_screen)
	mission_select_screen.mission_selected.connect(on_mission_chosen_from_menu)
	mission_select_screen.reset_campaign_requested.connect(on_reset_campaign)

	briefing_screen = BriefingScreenScript.new()
	add_child(briefing_screen)
	briefing_screen.start_mission_requested.connect(start_mission)

	results_screen = ResultsScreenScript.new()
	add_child(results_screen)
	results_screen.restart_mission_requested.connect(restart_mission)
	results_screen.return_to_menu_requested.connect(return_to_menu)

	open_mission_menu()

func open_mission_menu() -> void:
	current_mode = GameMode.MENU
	var available = MissionRegistryScript.get_available_missions()
	mission_select_screen.update_campaign_view(available, campaign_state)
	mission_select_screen.show_screen()
	briefing_screen.visible = false
	results_screen.hide_results()
	if hud:
		hud.visible = false
	if debug_overlay:
		debug_overlay.panel.visible = false

func on_reset_campaign() -> void:
	campaign_state = CampaignStateScript.new()
	campaign_state.save_to_file()
	open_mission_menu()

func on_mission_chosen_from_menu(mission_id: String) -> void:
	if not campaign_state.is_mission_unlocked(mission_id):
		return # Block locked deployment

	current_mission_id = mission_id
	mission_select_screen.hide_screen()
	init_tactical_world(current_mission_id)
	current_mode = GameMode.BRIEFING
	briefing_screen.visible = true

func init_tactical_world(mission_id: String) -> void:
	current_mission_id = mission_id

	# 1. Clean previous units from scene tree
	if selection_mgr:
		for u in selection_mgr.registered_units:
			if is_instance_valid(u):
				u.queue_free()
	if game_state:
		for uid in game_state.units.keys():
			var u = game_state.units[uid]
			if is_instance_valid(u) and u.get_parent() == self:
				u.queue_free()

	# 2. Load declarative package
	var pkg = MissionLoaderScript.load_mission_package("res://data/missions/" + mission_id)
	if not pkg.get("success", false):
		push_error("[CAPCAP] Failed to load mission package: " + pkg.get("error", "Unknown error"))
		return

	grid_map = pkg["grid_map"]
	game_state = pkg["game_state"]
	var spawned_units = pkg["units"]

	pathfinder = AStarScript.new(grid_map)
	action_queue = ActionQueueScript.new()
	selection_mgr = SelectionManagerScript.new()
	player_visibility_map = VisibilityMapScript.new(grid_map.width, grid_map.height)

	# 3. Renderers & HUD
	if not grid_renderer:
		grid_renderer = GridRendererScript.new(grid_map)
		add_child(grid_renderer)
	else:
		grid_renderer.grid_map = grid_map
		grid_renderer.queue_redraw()

	if not selection_renderer:
		selection_renderer = SelectionRendererScript.new()
		add_child(selection_renderer)

	if not combat_renderer:
		combat_renderer = CombatRendererScript.new()
		add_child(combat_renderer)

	# Register units in selection manager and scene tree
	for u in spawned_units:
		add_child(u)
		if u.team_id == "Player":
			selection_mgr.register_unit(u)

	# 4. Fog of War Layer
	if not fog_renderer:
		fog_renderer = FogRendererScript.new()
		fog_renderer.setup(player_visibility_map, grid_map)
		add_child(fog_renderer)
	else:
		fog_renderer.setup(player_visibility_map, grid_map)

	if not cursor:
		cursor = CursorScript.new()
		add_child(cursor)

	if not hud:
		hud = HUDScript.new()
		add_child(hud)
		hud.end_turn_requested.connect(handle_end_turn)
		hud.action_button_pressed.connect(handle_hud_action)

	if not debug_overlay:
		debug_overlay = DebugOverlayScript.new()
		add_child(debug_overlay)

	# 5. Initial Vision Update & Camera
	update_fog_of_war()
	var player_units = selection_mgr.registered_units
	if player_units.size() > 0:
		selection_mgr.select_single(player_units[0])
		hud.update_selection(selection_mgr.get_selected_units())

	if camera:
		camera.setup_bounds(grid_map.width, grid_map.height)
		camera.focus_on(IsoMathScript.grid_to_world(Vector2i(3, 3)), true)

func start_mission() -> void:
	mission_mgr.start_mission()
	current_mode = GameMode.PLAYING
	briefing_screen.visible = false
	results_screen.hide_results()
	if hud:
		hud.visible = true
	if debug_overlay:
		debug_overlay.panel.visible = debug_overlay.is_visible_overlay

func restart_mission() -> void:
	mission_mgr.reset()
	init_tactical_world(current_mission_id)
	current_mode = GameMode.BRIEFING
	briefing_screen.visible = true
	results_screen.hide_results()

func return_to_menu() -> void:
	mission_mgr.reset()
	open_mission_menu()

func _process(delta: float) -> void:
	frame_count += 1
	if frame_count == 15 and not screenshot_taken:
		take_screenshot()

	if debug_overlay and game_state and current_mode == GameMode.PLAYING:
		debug_overlay.update_debug_info(game_state, selection_mgr.get_selected_units(), hovered_grid, hovered_elev, is_hovered_walkable, combat_debug_info)

func take_screenshot() -> void:
	screenshot_taken = true
	if DisplayServer.get_name() == "headless":
		return
	var vp = get_viewport()
	if not vp:
		return
	var tex = vp.get_texture()
	if not tex:
		return
	var img = tex.get_image()
	if img:
		img.save_png("C:/Users/enrik/.gemini/antigravity/brain/fb4cb5f8-9b4d-4919-bc2f-fc4049c78127/capcap_live_screenshot.png")
		print("[CAPCAP] Live visual screenshot captured successfully under Godot 4.7.2!")

func update_fog_of_war() -> void:
	if not game_state or not player_visibility_map:
		return
	var visible_cells = VisionSystemScript.compute_team_vision("Player", game_state)
	player_visibility_map.update_visibility(visible_cells)
	if fog_renderer:
		fog_renderer.refresh()

	for uid in game_state.units.keys():
		var u = game_state.units[uid]
		if u.team_id == "Enemy":
			u.visible = player_visibility_map.is_cell_visible(u.grid_pos)

	var verdict = game_state.evaluate_victory()
	if verdict != 0 and current_mode == GameMode.PLAYING:
		current_mode = GameMode.RESULTS
		var is_win = (verdict == 1)
		mission_mgr.complete_mission(is_win, game_state.turn_number)

		# Apply result to campaign and get detailed report
		var result_dict = {
			"mission_id": current_mission_id,
			"is_victory": is_win,
			"turns": game_state.turn_number,
			"damage_dealt": mission_mgr.damage_dealt,
			"damage_taken": mission_mgr.damage_taken,
			"enemies_killed": mission_mgr.enemies_killed
		}
		var eval_report = CampaignEvaluatorScript.apply_mission_result(campaign_state, result_dict)
		results_screen.show_results(mission_mgr, eval_report)

func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo:
		if event.keycode == KEY_SPACE or event.keycode == KEY_C:
			if current_mode == GameMode.MENU:
				on_mission_chosen_from_menu(mission_select_screen.selected_mission_id)
			elif current_mode == GameMode.BRIEFING:
				start_mission()
			elif current_mode == GameMode.RESULTS:
				return_to_menu()
		elif event.keycode == KEY_R and current_mode == GameMode.RESULTS:
			restart_mission()
		elif event.keycode == KEY_M and current_mode == GameMode.RESULTS:
			return_to_menu()
		elif event.keycode == KEY_F3:
			if debug_overlay:
				debug_overlay.toggle()
		elif event.keycode == KEY_F12:
			take_screenshot()
		elif event.keycode == KEY_E and current_mode == GameMode.PLAYING:
			handle_end_turn()

	if current_mode != GameMode.PLAYING:
		return

	if event is InputEventMouseButton:
		if event.button_index == MOUSE_BUTTON_LEFT:
			if event.pressed:
				handle_left_click_pressed(event.position, event.is_command_or_control_pressed())
			else:
				handle_left_click_released(event.position, event.is_command_or_control_pressed())
		elif event.button_index == MOUSE_BUTTON_RIGHT and event.pressed:
			handle_right_click(event.position)

	elif event is InputEventMouseMotion:
		if is_box_selecting:
			box_current_screen = event.position
			var rect = get_box_rect(box_start_screen, box_current_screen)
			selection_renderer.set_selection_rect(true, rect)
		else:
			handle_mouse_hover(event.position)

func handle_left_click_pressed(screen_pos: Vector2, is_ctrl: bool) -> void:
	var world_mouse: Vector2 = get_global_mouse_position()
	var clicked_cell: Vector2i = IsoMathScript.world_to_grid_raycast(world_mouse, grid_map)
	var clicked_unit = selection_mgr.get_unit_at_grid(clicked_cell)

	if clicked_unit and clicked_unit.team_id == "Player":
		if is_ctrl:
			selection_mgr.toggle_selection(clicked_unit)
		else:
			selection_mgr.select_single(clicked_unit)
	else:
		is_box_selecting = true
		box_start_screen = screen_pos
		box_current_screen = screen_pos
	hud.update_selection(selection_mgr.get_selected_units())

func handle_left_click_released(screen_pos: Vector2, is_ctrl: bool) -> void:
	if is_box_selecting:
		is_box_selecting = false
		selection_renderer.set_selection_rect(false, Rect2())
		var rect = get_box_rect(box_start_screen, screen_pos)
		if rect.size.length() > 8.0:
			selection_mgr.select_in_box(rect, camera)
		else:
			if not is_ctrl:
				selection_mgr.clear_selection()
	hud.update_selection(selection_mgr.get_selected_units())

func handle_right_click(screen_pos: Vector2) -> void:
	var selected = selection_mgr.get_selected_units()
	if selected.size() == 0 or game_state.match_state != 0:
		return

	var world_mouse: Vector2 = get_global_mouse_position()
	var target_cell: Vector2i = IsoMathScript.world_to_grid_raycast(world_mouse, grid_map)

	# Attack Check
	for uid in game_state.units.keys():
		var u = game_state.units[uid]
		if u.grid_pos == target_cell and u.team_id != "Player" and u.stats.is_alive() and u.visible:
			for attacker in selected:
				var atk_act = AttackActionScript.new(attacker.unit_id, u.unit_id)
				action_queue.push_action(atk_act)
				combat_renderer.fire_tracer(attacker.grid_pos, attacker.current_elevation, u.grid_pos, u.current_elevation)
				u.trigger_hit_feedback()
				mission_mgr.record_damage_dealt(attacker.base_damage)
				if not u.stats.is_alive():
					mission_mgr.record_enemy_killed()
			action_queue.execute_all(game_state)
			update_fog_of_war()
			hud.update_selection(selected)
			return

	if not grid_map.is_cell_walkable(target_cell):
		return

	var assignments = FormationSolverScript.solve_formation(selected, target_cell, grid_map, FormationSolverScript.FormationType.GRID)
	var markers: Array = []
	for unit in assignments.keys():
		var dest = assignments[unit]
		var path = pathfinder.find_path(unit.grid_pos, dest)
		if path.size() > 1:
			var max_steps = min(unit.stats.current_ap, path.size() - 1)
			var trunc_path = path.slice(0, max_steps + 1)
			if trunc_path.size() > 1:
				var move_act = MoveActionScript.new(unit.unit_id, trunc_path)
				action_queue.push_action(move_act)
				var dest_elev = grid_map.get_cell(dest).elevation if grid_map.is_valid_cell(dest) else 0
				markers.append({"pos": dest, "elevation": dest_elev})

	selection_renderer.set_destination_markers(markers)
	action_queue.execute_all(game_state)
	update_fog_of_war()
	hud.update_selection(selected)

func handle_hud_action(action_type: String) -> void:
	var selected = selection_mgr.get_selected_units()
	if selected.size() == 0 or game_state.match_state != 0:
		return

	if action_type == "overwatch":
		for u in selected:
			var ow_act = OverwatchActionScript.new(u.unit_id, 2)
			action_queue.push_action(ow_act)
		action_queue.execute_all(game_state)
		hud.update_selection(selected)
	elif action_type == "wait":
		for u in selected:
			u.stats.current_ap = 0
		hud.update_selection(selected)

func handle_mouse_hover(screen_pos: Vector2) -> void:
	if not grid_map:
		return
	var world_mouse: Vector2 = get_global_mouse_position()
	hovered_grid = IsoMathScript.world_to_grid_raycast(world_mouse, grid_map)
	is_hovered_walkable = grid_map.is_cell_walkable(hovered_grid)
	hovered_elev = grid_map.get_cell(hovered_grid).elevation if grid_map.is_valid_cell(hovered_grid) else 0
	cursor.update_cursor(hovered_grid, hovered_elev, is_hovered_walkable)

	# Combat Target Hover Evaluation
	combat_debug_info.clear()
	var selected = selection_mgr.get_selected_units()
	if selected.size() > 0 and game_state:
		var att = selected[0]
		for uid in game_state.units.keys():
			var u = game_state.units[uid]
			if u.grid_pos == hovered_grid and u.team_id != att.team_id and u.stats.is_alive() and u.visible:
				var dist = CombatResolverScript.get_distance_3d(att.grid_pos, att.current_elevation, u.grid_pos, u.current_elevation)
				var has_los = LineOfSight2DScript.has_los(att.grid_pos, att.current_elevation, u.grid_pos, u.current_elevation, grid_map)
				var cover = CoverSystemScript.get_cover_type(att.grid_pos, att.current_elevation, u.grid_pos, u.current_elevation, grid_map)
				var mit = CoverSystemScript.get_mitigation(cover)
				var est_dmg = CombatResolverScript.calculate_damage(att, u, grid_map)

				combat_debug_info = {
					"target_id": u.unit_id,
					"target_name": u.unit_name,
					"dist": dist,
					"has_los": has_los,
					"cover_type": "HALF" if cover == 1 else ("FULL" if cover == 2 else "NONE"),
					"mitigation": mit,
					"est_damage": est_dmg
				}
				break

func handle_end_turn() -> void:
	if not game_state or game_state.match_state != 0:
		return

	# 1. Enemy Turn (IA)
	game_state.next_turn()
	game_state.active_team = "Enemy"
	hud.update_turn(game_state.turn_number, game_state.active_team)

	AIControllerScript.execute_ai_turn(game_state, action_queue, pathfinder, combat_renderer)

	# 2. Return to Player Turn
	game_state.next_turn()
	game_state.active_team = "Player"
	hud.update_turn(game_state.turn_number, game_state.active_team)
	update_fog_of_war()
	hud.update_selection(selection_mgr.get_selected_units())

func get_box_rect(p1: Vector2, p2: Vector2) -> Rect2:
	var top_left = Vector2(min(p1.x, p2.x), min(p1.y, p2.y))
	var size = Vector2(abs(p1.x - p2.x), abs(p1.y - p2.y))
	return Rect2(top_left, size)
