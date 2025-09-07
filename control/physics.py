from abc import ABC, abstractmethod
from typing import Iterable

import numpy as np
from control.math_utils import rotate_vector_2d, limit_vector, smallest_angle_difference, vector_from_angle_magnitude

from settings import GameSettings


class Pose:
    """Represents the spatial position and orientation of PhysicalEntities.

    :params position: 2D position of the object in the world. (width x height)
    :params orientation: 1D orientation of the object in clockwise degrees within the interval [0, 360).
    """
    def __init__(self, position: Iterable = None, orientation: float = 0):
        self.position: np.ndarray = np.array(position, dtype=float) if position else np.zeros((2,))
        assert self.position.size == 2, "position has to be 2D"
        self.orientation: float = orientation

    def __repr__(self) -> str:
        return f"Pose(width={self.position[0]}, height={self.position[1]}, orientation={self.orientation})"

class Dynamics(ABC):
    """Holds all movement relevant properties of an entity. Handles the effect of external effects on the entity, such
    as the engines or collisions. Also is used to update the entity pose when time passes.
    """
    def __init__(self, initial_pose: Pose = None, translation_speed_max: float = None,
                 rotation_speed_max: float = None, initial_translation: Iterable = None,
                 initial_rotation: float = 0):
        """
        :param initial_pose: The Pose that holds the initial position and orientation of the entity.
        :param translation_speed_max: The maximum speed the entity is allowed to move.
        :param rotation_speed_max: The maximum angle speed in degrees the entity is allowed to rotate.
        :param initial_translation: The initial direction and speed the entity moves.
        :param initial_rotation: The initial speed and direction the entity rotates. (positive values mean clock-wise)
        """
        self.pose = initial_pose or Pose()
        self.translation_speed_max = translation_speed_max or GameSettings.translation_speed_max
        self.rotation_speed_max = rotation_speed_max or GameSettings.rotation_speed_max
        self.translation_momentum = np.array(initial_translation, dtype=float) if initial_translation else np.zeros((2,))
        self.rotation_momentum = initial_rotation

    @abstractmethod
    def update(self):
        """Used to simulates the effect of self.translation and self.rotation on the object over time."""
        raise NotImplemented("abstract method")

    @abstractmethod
    def relative_move(self, angle: float, magnitude: float):
        """Gets an impulse to move in a direction relative to the current position.

        :param angle: Angle to move towards in [0, 360) clockwise with 0 is up.
        :param magnitude: The strength of the impulse.
        """
        raise NotImplemented("abstract method")

    def move_forward(self, magnitude: float):
        """Impulse to move the entity in the direction of the current orientation by an impulse with the magnitude."""
        self.relative_move(angle=self.pose.orientation, magnitude=magnitude)

    @abstractmethod
    def relative_rotation(self, magnitude: float):
        """Impulse to rotate the entity.

        :param magnitude: The strength of the impulse. Positive numbers will rotate clockwise.
        """
        raise NotImplemented("abstract method")

    def absolute_rotation(self, angle: float):
        """Rotate the entity towards the angle.

        Note this will not necessarily set the orientation to the angle, because the movement is still effected by the
        rules of the simulation, e.g. the rotation_speed_max.

        :param angle: Angle to move towards in [0, 360) clockwise with 0 is up.
        """
        relative_angle = smallest_angle_difference(self.pose.orientation, angle)
        self.relative_rotation(relative_angle)

    def set_translation_speed_max(self, max_speed: float, max_change: float = None):
        """Set a new maximum speed.

        :param max_speed: The new maximum allowed limit for the object
        :param max_change: Optionally, limits how much the current max speed can change. This smoothes the movements.
        """
        if max_change and max_speed < self.translation_speed_max:
            max_speed = max(self.translation_speed_max - max_change, max_speed)
        self.translation_speed_max = min(max_speed, GameSettings.translation_speed_max)

    def set_rotation_speed_max(self, max_speed: float):
        self.rotation_speed_max = min(max_speed, GameSettings.rotation_speed_max)

class StaticDynamics(Dynamics):
    """Defines an inertia free system. Meaning the object moves exactly as the inputs indicates."""
    def update(self):
        """Apply the current momentum and reset it to 0."""
        self.pose.position += limit_vector(self.translation_momentum, self.translation_speed_max)
        self.translation_momentum[:] = 0

        if abs(self.rotation_momentum ) > self.rotation_speed_max:
            self.rotation_momentum = np.sign(self.rotation_momentum) * self.rotation_speed_max
        self.pose.orientation += self.rotation_momentum
        self.pose.orientation = self.pose.orientation % 360
        self.rotation_momentum = 0

    def relative_move(self, angle: float, magnitude: float):
        """Gets a change in position and updates the position."""
        self.translation_momentum += vector_from_angle_magnitude(angle, magnitude)

    def move_forward(self, magnitude: float):
        """Moves the position in the direction of the current orientation."""
        self.translation_momentum = rotate_vector_2d(np.array([0, magnitude]), self.pose.orientation)

    def relative_rotation(self, angle: float):
        """Rotates the orientation by angle degrees. Positive numbers will rotate clockwise."""
        self.rotation_momentum = angle

    @staticmethod
    def get_relative_rotation_magnitude(angle: float, max_rotation_acceleration: float):
        """Returns the maximum angle to rotate to get to the target angle."""
        if angle == 0:
            return 0
        else:
            return np.sign(angle) * min(abs(angle), max_rotation_acceleration)

    def absolute_rotation(self, angle: float):
        """Turns towards the angle."""
        self.rotation_momentum = angle


class InertiaDynamics(Dynamics):
    """Simulates inertia and momentum. This means that the entity keeps the current momentum and all forces applied
    to the entity change the momentum resisted by the inertia.

    Note, this is not intended to be physically correct. The goal is a satisfying user experience and that includes
    for me a somewhat realistic physics. Fun and user experience will take priority.

    :param initial_translation_inertia: The value represents the objects resistance to changes in its positional movements.
    :param initial_rotation_inertia: The value represents the objects resistance to changes in its rotational movements.
    """
    def __init__(self, *, initial_translation_inertia: float = 0.05, initial_rotation_inertia: float = 0.033, **kwargs):
        super().__init__(**kwargs)
        self.translation_inertia = initial_translation_inertia
        self.rotation_inertia = initial_rotation_inertia

    def update(self):
        """Called to simulate dynamics for 1 tick."""
        self._apply_translation_momentum()
        self._apply_rotation_momentum()

    def _apply_translation_momentum(self):
        """Apply the translation momentum to the pose.

        Note: This implementation is not physically correct. We assume that an object has maximum momentum. E.g. that a
            pilot would not accelerate over a certain speed to avoid loosing control of the ship. The thrusters would
            turn off automatically in this case. However, this comes with the side effect, that the current
            implementation cancels the momentum over time when accelerating in another direction. E.g. when moving top
            speed up and then accelerating to the right will also decrease the speed in the up direction, to keep within
            the max speed limit. This is intentional, because it felt better.
        """
        self.translation_momentum = limit_vector(self.translation_momentum, self.translation_speed_max)
        self.pose.position += self.translation_momentum

    def _apply_rotation_momentum(self):
        """Apply the rotation momentum to the pose.

        Note: This implementation is not physically correct. We assume that an object has maximum momentum. E.g. that a
            pilot would not turn faster than this threshold.
        """
        if abs(self.rotation_momentum) > self.rotation_speed_max:
            self.rotation_momentum = np.sign(self.rotation_momentum) * self.rotation_speed_max
        self.pose.orientation += self.rotation_momentum
        self.pose.orientation = self.pose.orientation % 360
        if np.isclose(self.rotation_momentum, 0, atol=0.0001):
            self.rotation_momentum = 0

    def relative_move(self, angle: float, magnitude: float):
        impulse = vector_from_angle_magnitude(angle, magnitude)
        self.translation_momentum += impulse * self.translation_inertia
        if np.allclose(self.translation_momentum, (0, 0), atol=0.01):
            # this handles the problem, that it is nearly impossible to completely stop the ship. Which is realistic,
            # but feels bad during play.
            self.translation_momentum[:] = 0

        # todo add relative_move_vector, because that is what I got before, so I just convert twice here

    def relative_rotation(self, magnitude: float):
        """Impulse to rotate the entity.

        :param magnitude: The strength of the impulse. Positive numbers will rotate clockwise.
        """
        self.rotation_momentum += magnitude * self.rotation_inertia

    def get_relative_rotation_magnitude(self, angle: float, max_rotation_acceleration: float) -> float:
        """Compute the optimal magnitude parameter needed for relative_rotation to turn by angle degrees in a
        way to perfectly stopping at the correct angle with 0 momentum left.y

        :param angle: Relative orientation change in degrees to move towards in [0, 360) clockwise with 0 is up.
        :param max_rotation_acceleration: The strongest possible rotational impulse.
        """
        if angle == 0 and self.rotation_momentum == 0:
            return 0  # nothing to do

        highest_possible_momentum_change = max_rotation_acceleration * self.rotation_inertia
        target_direction = self._get_best_rotation_direction(angle, highest_possible_momentum_change)
        new_rotation_momentum = self.rotation_momentum + highest_possible_momentum_change * target_direction
        new_time_to_stop_in_ticks = abs(new_rotation_momentum) / highest_possible_momentum_change
        new_breaking_distance_in_degrees = self.stopping_distance(new_rotation_momentum, new_time_to_stop_in_ticks, highest_possible_momentum_change)

        if np.isclose(angle, 0, atol=0.001) and abs(self.rotation_momentum) <= highest_possible_momentum_change:
            # when very close to the target, perfectly stop momentum and orientation
            magnitude = -self.rotation_momentum / self.rotation_inertia
            if angle != 0:  # todo test if that is still the case or if it is precise enough now
                self.pose.orientation += angle
                print("needed to correct angle")
        elif abs(angle) <= new_breaking_distance_in_degrees:  # time to de-accelerate?
            if abs(self.rotation_momentum) >= 1 * highest_possible_momentum_change:
                magnitude = -1 * target_direction * max_rotation_acceleration
            else:
                if abs(angle) < highest_possible_momentum_change:
                    # reduce the magnitude for the final tick to land on the target angle
                    magnitude = (-1 * target_direction * max_rotation_acceleration * (
                        (highest_possible_momentum_change - abs(angle)) / highest_possible_momentum_change))
                else:
                    magnitude = 0

        else:  # accelerate momentum
            magnitude = target_direction * max_rotation_acceleration

        return magnitude

    def _get_best_rotation_direction(self, target_angle: float, highest_possible_momentum_change: float) -> int:
        """Compute the fastest direction to rotate. Naively, this is the direction with the smallest angular distance.
         However, if there is already lots of momentum in the opposite direction, it might take more time to reverse
         the momentum than to simply keep going.

         :return: -1 for counterclockwise and 1 for clockwise. If target_angle is 0, returns the direction of the
            current momentum.
         """
        if target_angle == 0:
            return np.sign(self.rotation_momentum)

        return np.sign(target_angle)  # todo implement the improved logic.

    @staticmethod
    def stopping_distance(starting_moment: float, num_ticks: float, highest_possible_momentum_change: float):
        """The distance that is rotated before the rotation can be stopped when decelerating with
         highest_possible_momentum_change.
        """
        starting_moment = abs(starting_moment)
        return sum(starting_moment - highest_possible_momentum_change * t for t in
                   range(int(num_ticks))) + (
                num_ticks // 1) * highest_possible_momentum_change

    def absolute_rotation(self, angle: float, max_rotation_acceleration: float = 1):
        """Change the momentum to turn the entity towards the angle in a way to perfectly stopping at the angle with 0
         momentum left.

        :param angle: Relative orientation change in degrees to move towards in [0, 360) clockwise with 0 is up.
        :param max_rotation_acceleration: The strongest possible rotational impulse.
        """
        relative_angle = smallest_angle_difference(self.pose.orientation, angle)
        magnitude = self.get_relative_rotation_magnitude(relative_angle, max_rotation_acceleration)
        self.relative_rotation(magnitude)
        return magnitude
