from dataclasses import dataclass
from typing import Optional

import numpy as np

from control.physics import PhysicsEngine
from control.user_input import UserInput
from control.math_utils import limit_vector, smallest_angle_difference
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
    :param status_maneuvering_thrusters: The operational status of the maneuvering thrusters.
    :param max_maneuver_speed: The maximum speed the object can move with maneuvering thrusters. If None, no limits
        are applied.
    :param max_maneuver_acceleration: The maximum acceleration the maneuvering thrusters can output.
    :param max_burst_acceleration: The maximum acceleration the main thrusters can output.
    :param time_to_turn: The time in seconds it takes the ship to turn 180 degrees starting with 0 speed and
        ending with 0 speed. (This means accelerating for half the time and decelerating the other half.)
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
    max_maneuver_speed: Optional[float] = None  # todo currently not implemented!
    max_maneuver_acceleration: float = 0.
    time_to_turn: float = 0
    max_rotation_acceleration: float = 0  # is set automatically in __post_init__ based on time_for_one_rotation
    energy_maneuver: float = 0
    is_maneuvering_thruster_active = False

    status_main_thrusters: Status = Status.nominal
    max_burst_acceleration: float = 0.
    energy_burst = 0
    is_burst_mode_active: bool = False

    _synced_with_physics_engine: bool = False  # were the values from the engine pushed to push the engine?

    @property
    def physics_engine(self) -> PhysicsEngine:
        return self.entity.physics_engines[0]

    def _sync_with_physics_engine(self):
        """Sync parameters between the engine and the physics object.

        Position and rotational angle are automatically updated, but other parameters are not.
        """
        self.entity.rotation_inertia = self.physics_engine.get_rotational_inertia()
        if self.time_to_turn:
            num_ticks = GameSettings.simulation_speed * self.time_to_turn / 2
            self.max_rotation_acceleration = 180 / (num_ticks * (num_ticks - 1))  # this is actually the max momentum change
            self.max_rotation_acceleration /= self.entity.rotation_inertia
        self._synced_with_physics_engine = True

    def activate(self, user_input: UserInput):
        """Steers the objects by updates the Dynamic's attributes in accordance with the engine."""
        self.physics_engine.set_current_entity(self.entity)
        if not self._synced_with_physics_engine:
            self._sync_with_physics_engine()

        self.is_maneuvering_thruster_active = False
        self.is_burst_mode_active = False

        # steer the ship according to user input
        if user_input.stabilize and self.status_maneuvering_thrusters != Status.destroyed:
            self._stop_translation()
            self._stop_rotation()
        else:  # no using the thrusters otherwise while the autopilot is at work!
            if user_input.burst > 0 and self.status_main_thrusters != Status.destroyed:
                self._burst_mode(user_input)
            if self.status_maneuvering_thrusters != Status.destroyed:
                if self.relative_movement_strength(user_input) > GameSettings.min_drift_strength:
                    self._maneuver(user_input)
                if user_input.orientation_strength > GameSettings.min_drift_strength:
                    self._rotate(user_input)

    def _stop_translation(self):
        """Fire maneuvering thrusters to cancel translation speed."""
        if any(self.physics_engine.get_translational_speed()):
            if self.entity.reactor.power(self.energy_maneuver, self):
                self.is_maneuvering_thruster_active = True
                counter_impulse = limit_vector(-np.array(self.physics_engine.get_translational_speed()),
                                               self.max_maneuver_acceleration)
                self.physics_engine.relative_move_impulse(counter_impulse)

    def _stop_rotation(self):
        """Fire maneuvering thrusters to cancel rotation speed."""
        if self.physics_engine.get_rotational_speed():
            if self.entity.reactor.power(self.energy_maneuver, self):
                self.physics_engine.absolute_rotation(self.entity.angle, self.max_rotation_acceleration)

    def _burst_mode(self, user_input: UserInput):
        """Fire the main thrusters for maximum acceleration!"""
        if self.entity.reactor.power(self.energy_burst * user_input.burst, self):
            self.is_burst_mode_active = True
            self.physics_engine.move_forward(user_input.burst * self.max_burst_acceleration)

    def _maneuver(self, user_input: UserInput):
        """Use the maneuvering thruster to change position."""
        # todo make it so, that if self.max_maneuver_speed is set, we cannot increase the speed above this limit
        input_strength = self.relative_movement_strength(user_input)
        if self.entity.reactor.power(self.energy_maneuver * input_strength, self):
            self.is_maneuvering_thruster_active = True
            user_input_direction = np.array((user_input.movement_width, user_input.movement_height))
            impulse = limit_vector(user_input_direction, self.max_maneuver_acceleration * input_strength)
            self.physics_engine.relative_move_impulse(impulse)

    def _rotate(self, user_input: UserInput):
        """Uses the maneuvering thrusters to rotate the entity. The speed depends on how strong the input is."""
        relative_angle = smallest_angle_difference(self.entity.angle, user_input.orientation)
        max_rotation_acceleration = self.max_rotation_acceleration * user_input.orientation_strength
        magnitude = self.physics_engine.get_relative_rotation_magnitude(relative_angle, max_rotation_acceleration)
        required_energy = abs(self.energy_maneuver * magnitude / self.max_rotation_acceleration)
        if self.entity.reactor.power(required_energy, self):
            self.physics_engine.relative_rotation(magnitude)

    @staticmethod
    def relative_movement_strength(user_input: UserInput) -> float:
        """Converts the relative movement command to the strength (vector length)."""
        return np.sqrt(user_input.movement_width**2 + user_input.movement_height**2)

@dataclass
class TestShipEngine(Engine):
    """For testing in debug mode."""
    max_maneuver_speed: Optional[float] = None
    max_maneuver_acceleration: float = 1.
    time_to_turn: float = 1.5
    max_rotation_acceleration: float = 0
    energy_maneuver: float = 10
    is_maneuvering_thruster_active = False

    max_burst_acceleration: float = 20.
    energy_burst = 110
    is_burst_mode_active: bool = False
