extends StaticBody3D

@export var mission_id: String = "silent-breach"
@export var prompt: String = "[E] Accept Mission"

signal mission_requested(mission_id: String)

func interact(_player: Node) -> void:
	mission_requested.emit(mission_id)
