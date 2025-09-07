from dataclasses import dataclass

import numpy as np

from control.user_input import UserInput
from control.math_utils import limit_vector, angle_magnitude_from_vector, smallest_angle_difference
from model.systems.common import Status, System
from settings import GameSettings

@dataclass(kw_only=True)
class Engine(System):
    # todo should this be 2 independent systems?
    """Moves an entity in space or rotates it.

    Most entities come with 2 types of thrusters. Maneuvering thrusters are omnidirectional and energy efficient. On the
    other hand the main thrusters are extremely powerful, but can only propel the ship forward, consuming huge amounts
    of energy.

    The maneuvering thrusters have a feature that allows to automatically cancel all momentum. However, you can't use
    the main thruster at the same time.

    The default Engine is not mobile by default, it has no output and cannot maneuver at all or control its momentum.

    :param name: Name of the System. Defaults to "Engine".
    :param status_main_thrusters: The operational status of the main thruster.
    :param status_main_thrusters: The operational status of the maneuvering thrusters.
    :param max_maneuver_speed: The maximum speed the object can move with maneuvering thrusters.
    :param max_maneuver_acceleration: The maximum acceleration the maneuvering thrusters can output.
    :param max_burst_speed: The maximum speed the object can move with the main thrusters.
    :param max_burst_acceleration: The maximum acceleration the main thrusters can output.
    :param max_speed_rotation: The angle in degrees that can be rotated per update step
    :param time_to_max_speed_translation: The time in seconds to reach maximum speed going straight.
    :param time_to_max_speed_rotation: The time in seconds to reach maximum speed while rotating.
    :param is_burst_mode_active: Indicates if the main thruster is currently active
    :param energy_maneuver: The energy needed per tick to use the maneuvering thrusters
    :param energy_burst: The energy needed per tick to use the main thrusters

    Effects of system damages:
    Main thrusters:
        light_damage:
            - increased energy consumptions  # todo
        heavy damage:
            - even further increased energy consumption  # todo
            - may sputter (turning on and off -> decreased max speed)  # todo
            - prolonged usage might cause explosion  # todo
    Maneuver thruster:
        light_damage:
            - decreased max_acceleration (both rotation and translation)  # todo
            - movements get some random noisy input representing the unknown output capabilities  # todo
                - maybe this gets reduced over time, as the system learns how well it thruster work?  # todo
        heavy_damage:
            - even further decreased max_acceleration  # todo
            - may sputter (turning on and off -> decreased max speed)  # todo
            - prolonged usage might cause the system to be destroyed  # todo
    """
    name: str = "Engines"
    status_maneuvering_thrusters: Status = Status.nominal
    max_maneuver_speed: float = GameSettings.translation_speed_max
    max_maneuver_acceleration: float = 0.
    max_speed_rotation: float = GameSettings.rotation_speed_max
    max_rotation_acceleration: float = 0
    energy_maneuver = 0
    time_to_max_speed_rotation = 0
    time_to_max_speed_translation = 0
    is_maneuvering_thruster_active = False  # todo make this an angle or None. This can be used for visualization

    status_main_thrusters: Status = Status.nominal
    max_burst_speed: float = GameSettings.translation_speed_max
    max_burst_acceleration: float = 0.
    energy_burst = 0
    is_burst_mode_active: bool = False

    def __post_init__(self):
        """Update the dynamics parameters with the limits defined by the engine.

        Note: This is not physically correct, but the idea is, that some engine depending limitations on the dynamics
            improve the user experience.
        """
        self.entity.dynamics.set_translation_speed_max(self.time_to_max_speed_translation)
        self.entity.dynamics.set_rotation_speed_max(self.max_speed_rotation)

    def activate(self, user_input: UserInput):
        """Steers the objects by updates the Dynamic's attributes in accordance with the engine."""
        self.is_maneuvering_thruster_active = False
        self.is_burst_mode_active = False

        # slowly reset the max speed after bursts
        if user_input.burst == 0:
            self.entity.dynamics.set_translation_speed_max(self.max_maneuver_speed, max_change=self.max_maneuver_acceleration)

        # steer the ship according to user input
        if user_input.stabilize and self.status_maneuvering_thrusters != Status.destroyed:
            self._stabilize()
        else:  # no using the thrusters otherwise while the autopilot is at work!
            if user_input.burst > 0 and self.status_main_thrusters != Status.destroyed:
                self._burst_mode(user_input)
            if self.status_maneuvering_thrusters != Status.destroyed:
                if self.relative_movement_strength(user_input) > GameSettings.min_drift_strength:
                    self._maneuver(user_input)
                if user_input.orientation_strength > GameSettings.min_drift_strength:
                    self._rotate(user_input)

    def _stabilize(self):
        """Fire maneuvering thrusters to cancel translation and rotation momentum."""
        if any(self.entity.dynamics.translation_momentum) or self.entity.dynamics.rotation_momentum:
            if self.entity.reactor.power(self.energy_maneuver, self):
                self.is_maneuvering_thruster_active = True
                counter_translation = limit_vector(-self.entity.dynamics.translation_momentum, self.max_maneuver_acceleration)
                angle, magnitude = angle_magnitude_from_vector(counter_translation)
                self.entity.dynamics.relative_move(angle, magnitude)
            if self.entity.reactor.power(self.energy_maneuver, self):
                self.entity.dynamics.absolute_rotation(self.entity.dynamics.pose.orientation, self.max_rotation_acceleration)

    def _burst_mode(self, user_input: UserInput):
        """Fire the main thrusters for maximum acceleration!"""
        if self.entity.reactor.power(self.energy_burst * user_input.burst, self):
            self.is_burst_mode_active = True
            self.entity.dynamics.set_translation_speed_max(self.max_burst_speed)
            self.entity.dynamics.move_forward(user_input.burst * self.max_burst_acceleration)

    def _maneuver(self, user_input: UserInput):
        """Use the maneuvering thruster to change position."""
        input_strength = self.relative_movement_strength(user_input)
        if self.entity.reactor.power(self.energy_maneuver * input_strength, self):
            self.is_maneuvering_thruster_active = True
            user_input_direction = np.array((user_input.movement_width, user_input.movement_height))

            translation = limit_vector(user_input_direction, self.max_maneuver_acceleration * input_strength)
            angle, magnitude = angle_magnitude_from_vector(translation)
            self.entity.dynamics.relative_move(angle, magnitude)

    def _rotate(self, user_input: UserInput):
        """Uses the maneuvering thrusters to rotate the entity. The speed depends on how strong the input is."""
        relative_angle = smallest_angle_difference(self.entity.dynamics.pose.orientation, user_input.orientation)
        max_rotation_acceleration = self.max_rotation_acceleration * user_input.orientation_strength
        magnitude = self.entity.dynamics.get_relative_rotation_magnitude(relative_angle, max_rotation_acceleration)
        required_energy = abs(self.energy_maneuver * magnitude / self.max_rotation_acceleration)
        if self.entity.reactor.power(required_energy, self):
            self.entity.dynamics.relative_rotation(magnitude)

    @staticmethod
    def relative_movement_strength(user_input: UserInput) -> float:
        """Converts the relative movement command to the strength (vector length)."""
        return np.sqrt(user_input.movement_width**2 + user_input.movement_height**2)

@dataclass
class TestShipEngine(Engine):
    """For testing in debug mode."""
    max_maneuver_speed: float = 2.
    max_maneuver_acceleration: float = 1.
    max_burst_speed: float = 8
    max_burst_acceleration: float = 2.
    max_speed_rotation: float = None # is set depending on time_for_one_rotation. was previously 4
    max_rotation_acceleration: float = None # is set depending on time_for_one_rotation. was previously 1
    time_to_max_speed_translation = 2 / 3
    time_to_max_speed_rotation = 1.2
    energy_maneuver = 30
    energy_burst = 101

    def __post_init__(self):
        time_for_one_rotation = 0.75  # at max speed
        self.max_speed_rotation = 360 / (time_for_one_rotation * GameSettings.simulation_speed)
        super().__post_init__()
        self.max_rotation_acceleration = self.max_speed_rotation / self.time_to_max_speed_rotation

        """Experimenting with inertia to make the steerability of the ship more consistent. Not physically correct but
        it feels nice. In the long term I probably want ships to start feeling different. But that probably should be
        done by ship class instead of changing everytime the ship upgrades.

        max_maneuver_acceleration * inertia * time_to_max_speed_in_ticks  = max_maneuver_speed
        with time_to_max_speed_in_ticks = time_to_max_speed * simulation_speed

        inertia = max_maneuver_speed / (max_maneuver_acceleration * time_to_max_speed_translation * simulation_speed)

        Fun fact: The inertia just depends on the simulation_speed and not the rotation parameters.
        """
        self.entity.dynamics.inertia_translation = 1 / GameSettings.simulation_speed
        self.entity.dynamics.inertia_rotation = 1 / GameSettings.simulation_speed
