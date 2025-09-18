"""Used to define and communicate the user's inputs from the GUI to control and model."""

from dataclasses import dataclass


@dataclass
class UserInput:
    """Contains the current user inputs that effect the world. The user's inputs will be read periodically during the
     update loop.

    :param movement_width: Value in [-1, 1] indicating the width direction and power the ship should move
    :param movement_width: Value in [-1, 1] indicating the height direction and power the ship should move
    :param burst: Value in [0, 1] indicating if the main thruster should be activated and its power level.
    :param stabilize: Signals the autopilot to fire the maneuvering thrusters to kill the momentum.
    :param orientation: The direction the players wants to move in degrees with 0 is up in [0, 360)
    :param orientation_strength: Value in [0, 1] How strong the rotation is pressed.
    :param respawn: If True, the player respawns with full health.
    """
    movement_width: float = 0
    movement_height: float = 0
    burst: float = 0
    stabilize: bool = False
    orientation: float = 0
    orientation_strength: float = 0
    respawn: bool = False

