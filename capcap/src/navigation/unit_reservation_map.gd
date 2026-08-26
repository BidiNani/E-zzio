class_name UnitReservationMap
extends RefCounted

## UnitReservationMap - Manages exclusive cell destinations & temporary reservations

var reserved_cells: Dictionary = {} # Vector2i -> unit_id

func reserve(cell: Vector2i, unit_id: String) -> bool:
	if reserved_cells.has(cell) and reserved_cells[cell] != unit_id:
		return false
	reserved_cells[cell] = unit_id
	return true

func release_unit(unit_id: String) -> void:
	var keys_to_erase: Array[Vector2i] = []
	for cell in reserved_cells.keys():
		if reserved_cells[cell] == unit_id:
			keys_to_erase.append(cell)
	for k in keys_to_erase:
		reserved_cells.erase(k)

func is_reserved_by_other(cell: Vector2i, unit_id: String) -> bool:
	return reserved_cells.has(cell) and reserved_cells[cell] != unit_id
