class_name UnitSelectionManager
extends RefCounted

## UnitSelectionManager - Handles single click, Ctrl-toggle, and box selection

var registered_units: Array = [] # Array of UnitEntity
var selected_units: Array = []   # Array of UnitEntity

func register_unit(unit) -> void:
	if not registered_units.has(unit):
		registered_units.append(unit)

func unregister_unit(unit) -> void:
	registered_units.erase(unit)
	selected_units.erase(unit)

func select_single(unit) -> void:
	clear_selection()
	if unit:
		selected_units.append(unit)
		unit.set_selected(true)

func toggle_selection(unit) -> void:
	if not unit:
		return
	if selected_units.has(unit):
		selected_units.erase(unit)
		unit.set_selected(false)
	else:
		selected_units.append(unit)
		unit.set_selected(true)

func select_in_box(screen_rect: Rect2, camera: Camera2D) -> void:
	clear_selection()
	var viewport = camera.get_viewport()
	for unit in registered_units:
		var screen_pos = camera.get_viewport_transform() * unit.global_position
		if screen_rect.has_point(screen_pos):
			selected_units.append(unit)
			unit.set_selected(true)

func clear_selection() -> void:
	for unit in selected_units:
		unit.set_selected(false)
	selected_units.clear()

func get_selected_units() -> Array:
	return selected_units.duplicate()

func get_unit_at_grid(pos: Vector2i):
	for unit in registered_units:
		if unit.grid_pos == pos:
			return unit
	return null
