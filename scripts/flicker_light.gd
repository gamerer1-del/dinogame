class_name FlickerLight
extends OmniLight3D
## ときどき明滅する非常灯。

var base_energy := 1.0
var _t := 0.0


func _process(delta: float) -> void:
	_t -= delta
	if _t <= 0.0:
		_t = randf_range(0.05, 0.4)
		light_energy = base_energy * (0.1 if randf() < 0.3 else randf_range(0.7, 1.1))
