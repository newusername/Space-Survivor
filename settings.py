class GameSettings:
    """Holds the general game settings.

    :param energy_multiplier: Is multiplied with the cost of activating a system.
    :param player_dynamic: either "inertia" or "static". Defines which dynamics model is used to steer the ship.
    :param simulation_speed: how often per second the game simulation is updated. (aka ticks per second)
    :param translation_speed_max: This is the upper limit the game allows for an object to move.
    :param rotation_speed_max: This is the upper limit the game allows for an object to spin.
    :param min_drift_strength: The minimum absolute stick strength required to register. In the interval [0, 1). Values
        smaller are set to 0 and basically ignored. Useful for combating stick drifts.
    """
    energy_multiplier: float = 1.
    player_dynamic: str = "inertia"
    simulation_speed: float = 60
    translation_speed_max: float = 10
    rotation_speed_max: float = 10
    min_drift_strength: float = 0.1