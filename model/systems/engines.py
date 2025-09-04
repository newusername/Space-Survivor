from dataclasses import dataclass

import numpy as np

from control.user_input import UserInput
from control.math_utils import limit_vector
from control.physics import Dynamics
from settings import GameSettings


@dataclass
class Engine:
    """Defines how an entity can move. By default, it has no output and cannot maneuver at all or control its momentum.

    :param max_maneuver_speed: The maximum speed the object can move with maneuvering thrusters.
    :param max_maneuver_acceleration: The maximum acceleration the maneuvering thrusters can output.
    :param max_burst_speed: The maximum speed the object can move with the main thrusters.
    :param max_burst_acceleration: The maximum acceleration the main thrusters can output.
    :param max_speed_rotation: The angle in degrees that can be rotated per update step
    :param time_to_max_speed_translation: The time in seconds to reach maximum speed going straight.
    :param time_to_max_speed_rotation: The time in seconds to reach maximum speed while rotating.
    :param is_burst_mode_active: Indicates if the main thruster is currently active
    :param is_stabilize_mode_active: If True, the ship will use the autopilot to kill the momentum with the maneuvering
        thrusters. Ignores all movement commands except for rotation while active.
    """
    max_maneuver_speed: float = GameSettings.max_speed_movement
    max_maneuver_acceleration: float = 0.
    max_burst_speed: float = GameSettings.max_speed_movement
    max_burst_acceleration: float = 0.
    max_speed_rotation: float = GameSettings.max_speed_rotation
    max_rotation_acceleration: float = 0
    time_to_max_speed_translation = 0
    time_to_max_speed_rotation = 0
    is_burst_mode_active: bool = False
    is_stabilize_mode_active: bool = False

    def update_dynamic(self, dynamic: Dynamics, user_input: UserInput):
        """Updates the Dynamic's attributes in accordance with the engine."""
        # Movement
        if user_input.stabilize:
            self.is_burst_mode_active = False
            dynamic.set_max_speed_movement(self.max_maneuver_speed, step_decrease=self.max_maneuver_acceleration)
            dynamic.relative_move(*limit_vector(-dynamic.momentum_translation, self.max_maneuver_acceleration))
            dynamic.absolute_rotation(dynamic.pose.orientation*1.000001)
        elif user_input.burst > 0:
            self.is_burst_mode_active = True
            dynamic.set_max_speed_movement(self.max_burst_speed)
            dynamic.move_forward(user_input.burst * self.max_burst_acceleration)
        else:  # you can't use thrusting and main thrusters at the same time. Felt better during gameplay.
            self.is_burst_mode_active = False
            dynamic.set_max_speed_movement(self.max_maneuver_speed, step_decrease=self.max_maneuver_acceleration)
            user_input_direction = np.array((user_input.movement_width, user_input.movement_height))
            dynamic.relative_move(*limit_vector(user_input_direction, 1) * self.max_maneuver_acceleration)

        # Rotation
        if not user_input.stabilize and user_input.orientation_strength > GameSettings.min_drift_strength:
            dynamic.max_speed_rotation = self.max_speed_rotation * GameSettings.min_drift_strength
            dynamic.absolute_rotation(user_input.orientation)


@dataclass
class TestShipEngine(Engine):
    """For testing in debug mode."""
    max_maneuver_speed: float = 2.
    max_maneuver_acceleration: float = 1.
    max_burst_speed: float = 6
    max_burst_acceleration: float = 2.
    max_speed_rotation: float = None # is set depending on time_for_one_rotation. was previously 4
    max_rotation_acceleration: float = 1
    time_to_max_speed_translation = 2 / 3
    time_to_max_speed_rotation = 1

    def __post_init__(self):
        time_for_one_rotation = 0.75  # at max speed
        # todo the value is currently not correct, because of rotation inertia experiment. The true
        #  time_for_one_rotation is linear to this value though.
        self.max_speed_rotation = 360 / (time_for_one_rotation * GameSettings.simulation_speed)

    def update_dynamic(self, dynamic: Dynamics, user_input: UserInput):
        """Experimenting with inertia to make the steerability of the ship more consistent. Not physically correct but
        it feels nice. In the long term I probably want ships to start feeling different. But that probably should be
        done by ship class instead of changing everytime the ship upgrades.

        max_maneuver_acceleration * inertia * time_to_max_speed_in_ticks  = max_maneuver_speed
        with time_to_max_speed_in_ticks = time_to_max_speed * 60

        360 = max_speed_rotation * time
        """
        dynamic.inertia_translation = (
                self.max_maneuver_speed /
                (self.max_maneuver_acceleration * self.time_to_max_speed_translation * GameSettings.simulation_speed)
        )
        dynamic.inertia_rotation = (
                self.max_speed_rotation /
                (self.max_rotation_acceleration * self.time_to_max_speed_rotation * GameSettings.simulation_speed)
        )

        super().update_dynamic(dynamic, user_input)

