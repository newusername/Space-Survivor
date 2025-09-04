class GameSettings:
    """Holds the general game settings.

    :param player_dynamic: either "inertia" or "static". Defines which dynamics model is used to steer the ship.
    :param simulation_speed: how often per second the game simulation is updated.
    :param max_speed_movement: This is the upper limit the game allows for an object to move.
    :param max_speed_rotation: This is the upper limit the game allows for an object to spin.
    :param min_drift_strength: The minimum absolute stick strength required to register. In the interval [0, 1). Values
        smaller are set to 0 and basically ignored. Useful for combating stick drifts.
    """
    player_dynamic: str = "inertia"
    simulation_speed: float = 60
    max_speed_movement: float = 10
    max_speed_rotation: float = 10
    min_drift_strength: float = 0.4