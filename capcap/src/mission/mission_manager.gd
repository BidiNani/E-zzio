class_name MissionManager
extends RefCounted

## MissionManager - Manages Mission State Machine (Briefing -> Playing -> Results) and Game Statistics

enum State { BRIEFING = 0, PLAYING = 1, RESULTS = 2 }

var current_state: State = State.BRIEFING
var mission_title: String = "Opération : Avant-poste Alpha"
var turns_elapsed: int = 1
var max_turns: int = 15
var damage_dealt: int = 0
var damage_taken: int = 0
var enemies_killed: int = 0
var is_victory: bool = false

signal mission_state_changed(new_state)

func start_mission() -> void:
	current_state = State.PLAYING
	emit_signal("mission_state_changed", current_state)

func record_damage_dealt(amount: int) -> void:
	damage_dealt += max(0, amount)

func record_damage_taken(amount: int) -> void:
	damage_taken += max(0, amount)

func record_enemy_killed() -> void:
	enemies_killed += 1

func complete_mission(victory: bool, turns: int) -> void:
	is_victory = victory
	turns_elapsed = turns
	current_state = State.RESULTS
	emit_signal("mission_state_changed", current_state)

func reset() -> void:
	current_state = State.BRIEFING
	turns_elapsed = 1
	damage_dealt = 0
	damage_taken = 0
	enemies_killed = 0
	is_victory = false
	emit_signal("mission_state_changed", current_state)
