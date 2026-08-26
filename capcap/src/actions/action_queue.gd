class_name ActionQueue
extends RefCounted

## ActionQueue - Sequential, deterministic FIFO action scheduler

signal action_enqueued(action)
signal action_started(action)
signal action_completed(action)
signal action_failed(action, reason: String)

var queue: Array = []
var current_action = null
var is_processing: bool = false

func push_action(action) -> void:
	queue.append(action)
	action_enqueued.emit(action)

func execute_all(game_state) -> void:
	if is_processing:
		return
	is_processing = true

	while queue.size() > 0:
		current_action = queue.pop_front()
		action_started.emit(current_action)

		var validation = current_action.can_execute(game_state)
		if validation[0]:
			var success = current_action.execute(game_state)
			if success:
				action_completed.emit(current_action)
			else:
				action_failed.emit(current_action, "Execution failed.")
		else:
			action_failed.emit(current_action, validation[1])

	current_action = null
	is_processing = false

func clear_queue() -> void:
	for action in queue:
		action.cancel()
	queue.clear()
