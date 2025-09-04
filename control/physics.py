from abc import ABC, abstractmethod

import numpy as np
from numpy import iterable

from control.math_utils import rotate_vector_2d, limit_vector, smallest_angle_difference

from settings import GameSettings


class Pose(ABC):
    """Represents the spatial position and orientation of PhysicalEntities.

    :params position: 2D position of the object in the world. (width x height)
    :params orientation: 1D orientation of the object in clockwise degrees within the interval [0, 360).
    """
    def __init__(self, position: iterable = None, orientation: float = 0):
        self.position: np.array = np.array(position, dtype=float) if position else np.zeros((2,))
        assert self.position.size == 2, "position has to be 2D"
        self.orientation: float = orientation


class Dynamics(ABC):
    """Updates the pose over time and according to external influences."""
    def __init__(self, pose: Pose = None, max_speed_movement: float = GameSettings.max_speed_movement,
                 max_speed_rotation: float = GameSettings.max_speed_rotation, momentum_translation: iterable = None,
                 momentum_rotation: float = 0):
        """
        :param pose: The Pose that defines the initial position and orientation of the entity.
        :param max_speed_movement: The maximum speed the entity is allowed to move.
        :param max_speed_rotation: The maximum angle speed in degrees the entity is allowed to rotate.
        :param momentum_translation: The initial relative movement the entity will perform during the next update.
        :param momentum_rotation: The initial rotation momentum the entity will perform during the next update.
        """
        self.pose = pose or Pose()
        self.max_speed_movement = max_speed_movement  # todo rename to max_momentum_translation; also in the settings?
        self.max_speed_rotation = max_speed_rotation  # todo rename to max_momentum_rotation
        self.momentum_translation = np.array(momentum_translation, dtype=float) if momentum_translation else np.zeros((2,))
        self.momentum_rotation = momentum_rotation

    @abstractmethod
    def update(self):
        """Updates the pose over time using self.momentum."""
        raise NotImplemented("abstract method")

    @abstractmethod
    def relative_move(self, width: float, height: float):
        """Gets a change in position and updates the position."""
        raise NotImplemented("abstract method")

    @abstractmethod
    def move_forward(self, magnitude: float):
        """Moves the position in the direction of the current orientation."""
        raise NotImplemented("abstract method")

    @abstractmethod
    def relative_rotation(self, angle: float):
        """Rotates the orientation by angle degrees. Positive numbers will rotate clockwise."""
        raise NotImplemented("abstract method")

    @abstractmethod
    def absolute_rotation(self, angle: float):
        """Turns towards the angle."""
        raise NotImplemented("abstract method")


    def set_max_speed_movement(self, max_speed: float, step_decrease: float = None):
        """Set a new maximum speed. Optionally, if the new value is smaller than the old one, decrease only by the
        step amount. This smoothes the movements."""
        if step_decrease and max_speed < self.max_speed_movement:
            max_speed = max(self.max_speed_movement - step_decrease, max_speed)
        self.max_speed_movement = min(max_speed, GameSettings.max_speed_movement)

    def set_max_speed_rotation(self, max_speed: float):
        self.max_speed_rotation = min(max_speed, GameSettings.max_speed_rotation)


class StaticDynamics(Dynamics):
    """Defines an inertia free system. Meaning the object moves exactly as the inputs indicates."""
    def update(self):
        """Apply the current momentum and reset it to 0."""
        self.pose.position += limit_vector(self.momentum_translation, self.max_speed_movement)
        self.momentum_translation[:] = 0

        if abs(self.momentum_rotation ) > self.max_speed_rotation:
            self.momentum_rotation = np.sign(self.momentum_rotation) * self.max_speed_rotation
        self.pose.orientation += self.momentum_rotation
        self.pose.orientation = self.pose.orientation % 360
        self.momentum_rotation = 0

    def relative_move(self, width: float, height: float):
        """Gets a change in position and updates the position."""
        self.momentum_translation[0] += width
        self.momentum_translation[1] += height

    def move_forward(self, magnitude: float):
        """Moves the position in the direction of the current orientation."""
        self.momentum_translation = rotate_vector_2d(np.array([0, magnitude]), self.pose.orientation)

    def relative_rotation(self, angle: float):
        """Rotates the orientation by angle degrees. Positive numbers will rotate clockwise."""
        self.momentum_rotation = self.pose.orientation + angle

    def absolute_rotation(self, angle: float):
        """Turns towards the angle."""
        self.momentum_rotation = angle


class InertiaDynamics(Dynamics):
    """Simulates inertia and momentum. This means that the entity keeps the current momentum and all forces applied
    to the entity change the momentum resisted by the inertia.

    Note: The inertia for translation and rotation is handled separately for now, because that made finetuning
        the parameters for having a nice steering experience easier. But this should be fixed in the future.

    TODO: Is there a reason why I am not directly use the real equations? Instead of using this inertia variable, I
        could use the mass, right?

    :param inertia_translation: The value represents the objects resistance to changes in its positional movements.
    :param inertia_rotation: The value represents the objects resistance to changes in its rotational movements.
    """
    def __init__(self, inertia_translation: float = 0.05, inertia_rotation: float = 0.033, **kwargs):
        super().__init__(**kwargs)
        self.inertia_translation = inertia_translation
        self.inertia_rotation = inertia_rotation

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
        self.momentum_translation = limit_vector(self.momentum_translation, self.max_speed_movement)
        self.pose.position += self.momentum_translation

    def _apply_rotation_momentum(self):
        """Apply the rotation momentum to the pose.

        Note: This implementation is not physically correct. We assume that an object has maximum momentum. E.g. that a
            pilot would not turn faster than this threshold.
        """
        if abs(self.momentum_rotation) > self.max_speed_rotation:
            self.momentum_rotation = np.sign(self.momentum_rotation) * self.max_speed_rotation
        self.pose.orientation += self.momentum_rotation
        self.pose.orientation = self.pose.orientation % 360

    def relative_move(self, width: float, height: float):  # todo make a vector
        """Gets a force vector as position relative to this object and updates the momentum."""
        self.momentum_translation += np.array([width, height]) * self.inertia_translation
        if np.allclose(self.momentum_translation, (0, 0), atol=0.01):
            # this handles the problem, that it is nearly impossible to completely stop the ship. Which is realistic,
            # but feels bad during play.
            self.momentum_translation[:] = 0

    def move_forward(self, magnitude: float):
        """Increases momentum in the direction of the current orientation."""
        self.momentum_translation += rotate_vector_2d(np.array([0, magnitude]), self.pose.orientation) * self.inertia_translation

    def relative_rotation(self, angle: float):
        """Rotates the orientation by angle degrees. Positive numbers will rotate clockwise."""
        if np.allclose([angle, self.momentum_rotation], 0.01):
            # Make it easier to completely stop. Not physically correct, but feels better.
            self.momentum_rotation = 0
            return

        max_rotation_acceleration = 1  # todo how to pass the true value?
        if self.momentum_rotation == 0:
            distance_to_angle_in_ticks = np.inf
        elif np.sign(angle) == np.sign(self.momentum_rotation):
            distance_to_angle_in_ticks = abs(angle / self.momentum_rotation)
        else:  # currently accelerating in the wrong direction
            # todo it actually might be better to rotate the long way, if there is already lots of momentum in that direction
            distance_to_angle_in_ticks = np.inf

        breaking_time_in_ticks = np.sign(angle) * self.momentum_rotation / (max_rotation_acceleration * self.inertia_rotation)
        new_momentum = np.sign(angle) * max_rotation_acceleration * self.inertia_rotation
        if breaking_time_in_ticks >= distance_to_angle_in_ticks:  # time to de-accelerate?
            new_momentum *= -1

        self.momentum_rotation += new_momentum

    def absolute_rotation(self, angle: float):
        """Turns towards the angle."""
        relative_angle = smallest_angle_difference(self.pose.orientation, angle)
        self.relative_rotation(relative_angle)

    def set_max_speed_movement(self, max_speed: float, step_decrease: float = None):
        """Set a new maximum speed. Optionally, if the new value is smaller than the old one, decrease only by the
        step amount. This smoothes the movements."""
        step_decrease = step_decrease * self.inertia_translation if step_decrease else None
        super().set_max_speed_movement(max_speed, step_decrease)

    def set_max_speed_rotation(self, max_speed: float):
        """Set new maximum speed for rotation."""
        self.max_speed_rotation = min(max_speed, GameSettings.max_speed_rotation)
