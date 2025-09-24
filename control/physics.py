from contextlib import contextmanager
from typing import Callable

import numpy as np
from arcade import PymunkPhysicsEngine
from pymunk import Vec2d

from control.math_utils import smallest_angle_difference, vector_from_angle_magnitude, rotate_vector_2d

import model


class PhysicsEngine(PymunkPhysicsEngine):
    """Holds all movement relevant properties of an entity. Handles the effect of external effects on the entity, such
    as the engines or collisions. Also is used to update the entity pose when time passes.
    """
    def __init__(self, gravity=(0, 0), damping: float = 1.0):
        super().__init__(gravity=gravity, damping=damping)
        self.entity = None
        self.physics_object = None

    @contextmanager
    def set_current_entity(self, entity: "model.entities.PhysicalEntity"):
        """Set a specific entity to be manipulated."""  # todo make this a context manager.
        self.entity = entity
        self.physics_object = self.get_physics_object(entity)
        yield
        self.entity = None
        self.physics_object = None

    def get_translational_speed(self) -> Vec2d:
        """Return the translational speed vector of the entity."""
        return self.physics_object.body.velocity

    def get_velocity(self) -> float:
        """Return the translational speed of the entity."""
        return self.get_translational_speed().length

    def set_translational_speed(self, velocity: tuple[float, float]):
        """Set the translational speed of the entity."""
        self.physics_object.body.velocity = velocity

    def get_rotational_speed(self) -> float:
        """Return the rotational speed of the entity. Positive numbers will rotate clockwise.

        Note that Pymunk uses the opposite orientation. Hence, the - in the code below.
        """
        return -self.physics_object.body.angular_velocity

    def set_rotational_speed(self, velocity: float):
        """Set the rotational speed of the entity. Positive numbers will rotate clockwise.

        Note that Pymunk uses the opposite orientation. Hence, the - in the code below.
        """
        self.physics_object.body.angular_velocity = -velocity

    def relative_move(self, angle: float, magnitude: float):
        """Move in a direction relative to the current position with.

         :param angle: Angle to move towards in [0, 360) clockwise with 0 is up.
         :param magnitude: The strength of the impulse.
         """
        impulse = vector_from_angle_magnitude(angle, magnitude)
        self.relative_move_impulse(impulse)

    def relative_move_impulse(self, impulse: np.ndarray):
        """Gets an impulse to move in a direction relative to the current position, but global orientation.

        Pymunk's apply_impulse() also applies the impuls based on the entities orientation, which is why we rotate it
        before.
        """
        pymunk_impulse = rotate_vector_2d(impulse, -self.entity.angle)
        self.apply_impulse(self.entity, tuple(pymunk_impulse))  # noqa
        if np.allclose(self.get_translational_speed(), (0, 0), atol=0.01):
            # this handles the problem, that it is nearly impossible to completely stop the ship. Which is realistic,
            # but feels bad during play.
            self.set_translational_speed((0, 0))

    def move_forward(self, magnitude: float):
        """Impulse to move the entity in the direction of the current orientation by an impulse with the magnitude."""
        self.relative_move(angle=self.entity.angle, magnitude=magnitude)

    def relative_rotation(self, magnitude: float):
        """Impulse to rotate the entity.

        :param magnitude: The strength of the impulse. Positive numbers will rotate clockwise.
        """
        self.set_rotational_speed(self.get_rotational_speed() + magnitude * self.entity.rotation_inertia)

    def get_relative_rotation_magnitude(self, angle: float, max_rotation_acceleration: float) -> float:
        """Compute the optimal magnitude parameter needed for relative_rotation to turn by angle degrees in a
        way to perfectly stopping at the correct angle with 0 momentum left.y

        :param angle: Relative orientation change in degrees to move towards in [-180, 180) with 0 meaning no change,
            positive values clockwise rotation and negative counterclockwise rotation.
        :param max_rotation_acceleration: The strongest possible rotational impulse.
        """
        assert -180 <= angle < 180, "angle has to be in the interval [-180, 180)"
        if angle == 0 and self.get_rotational_speed() == 0:
            return 0  # nothing to do

        highest_possible_momentum_change = max_rotation_acceleration * self.entity.rotation_inertia
        new_rotation_momentum = self.get_rotational_speed() + highest_possible_momentum_change * np.sign(self.get_rotational_speed())
        new_time_to_stop_in_ticks = abs(new_rotation_momentum) / highest_possible_momentum_change
        new_breaking_distance_in_degrees = self.stopping_distance(new_rotation_momentum, new_time_to_stop_in_ticks, highest_possible_momentum_change)

        if np.isclose(angle, 0, atol=0.001) and abs(self.get_rotational_speed()) <= highest_possible_momentum_change:
            # when very close to the target, perfectly stop momentum and orientation
            magnitude = -self.get_rotational_speed() / self.entity.rotation_inertia  # todo is that still correct with Pymunk?
            if angle != 0:
                self.entity.angle += angle
        elif abs(angle) <= new_breaking_distance_in_degrees:  # time to de-accelerate?
            if abs(self.get_rotational_speed()) >= 1 * highest_possible_momentum_change:
                magnitude = -1 * np.sign(self.get_rotational_speed()) * max_rotation_acceleration
            else:
                if abs(angle) < highest_possible_momentum_change:
                    # reduce the magnitude for the final tick to land on the target angle
                    magnitude = (-1 * np.sign(self.get_rotational_speed()) * max_rotation_acceleration * (
                        (highest_possible_momentum_change - abs(angle)) / highest_possible_momentum_change))
                else:
                    magnitude = 0

        else:  # accelerate momentum
            magnitude = self._get_best_rotation_direction(angle) * max_rotation_acceleration

        return magnitude

    def _get_best_rotation_direction(self, target_angle: float) -> int:
        """Compute the fastest direction to rotate. Naively, this is the direction with the smallest angular distance.
         However, if there is already lots of momentum in the opposite direction, it might take more time to reverse
         the momentum than to simply keep going.

         :return: -1 for counterclockwise and 1 for clockwise. If target_angle is 0, returns the direction of the
            current rotation speed.
         """
        if target_angle == 0:
            return np.sign(self.get_rotational_speed())

        return np.sign(target_angle)

    @staticmethod
    def stopping_distance(starting_moment: float, num_ticks: float, highest_possible_momentum_change: float):
        """The distance that is rotated before the rotation can be stopped when decelerating with
         highest_possible_momentum_change.
        """
        starting_moment = abs(starting_moment)
        return sum(starting_moment - highest_possible_momentum_change * t for t in
                   range(int(num_ticks))) + (
                num_ticks % 1) * highest_possible_momentum_change

    def absolute_rotation(self, angle: float, max_rotation_acceleration: float = 1):
        """Change the momentum to turn the entity towards the angle in a way to perfectly stopping at the angle with 0
         momentum left.

        :param angle: Relative orientation change in degrees to move towards in [0, 360) clockwise with 0 is up.
        :param max_rotation_acceleration: The strongest possible rotational impulse.
        """
        relative_angle = smallest_angle_difference(self.entity.angle, angle)
        magnitude = self.get_relative_rotation_magnitude(relative_angle, max_rotation_acceleration)
        self.relative_rotation(magnitude)
        return magnitude

    def set_rotational_inertia(self, value: float):  # todo I am a bit confused. Pymunk makes it sound like this is only inertia, but going deeper it looks like both
        # self.physics_object.body._set_moment(value)
        self.physics_object.body.moment = value

    def get_rotational_inertia(self) -> float:  # todo I am a bit confused. Pymunk makes it sound like this is only inertia, but going deeper it looks like both
        return self.physics_object.body.moment

    def add_wildcard_collision_handler(self, collision_type: str, begin_handler: Callable | None = None,
                                       pre_handler: Callable | None = None, post_handler: Callable | None = None,
                                       separate_handler: Callable | None = None):
        """Adds a collision handler that handles all collisions for entities with the given collision_type.

        :param collision_type: unique identifier for entities. Usually stored in Entity.collision_type
        :param begin_handler: Function to call when a collision begins.
        :param pre_handler: Function to call before a collision is resolved.
        :param post_handler: Function to call after a collision is resolved.
        :param separate_handler: Function to call when two objects
        """
        if collision_type not in self.collision_types:
            self.collision_types.append(collision_type)
        collision_type_index = self.collision_types.index(collision_type)

        handler = self.space.add_wildcard_collision_handler(collision_type_index)
        def _f1(arbiter, space, data):
            sprite_a, sprite_b = self.get_sprites_from_arbiter(arbiter)
            should_process_collision = False
            if sprite_a is not None and sprite_b is not None and begin_handler is not None:
                should_process_collision = begin_handler(sprite_a, sprite_b, arbiter, space, data)
            return should_process_collision

        def _f2(arbiter, space, data):
            sprite_a, sprite_b = self.get_sprites_from_arbiter(arbiter)
            if sprite_a is not None and sprite_b is not None and post_handler is not None:
                post_handler(sprite_a, sprite_b, arbiter, space, data)

        def _f3(arbiter, space, data):
            sprite_a, sprite_b = self.get_sprites_from_arbiter(arbiter)
            if pre_handler is not None:
                return pre_handler(sprite_a, sprite_b, arbiter, space, data)

        def _f4(arbiter, space, data):
            sprite_a, sprite_b = self.get_sprites_from_arbiter(arbiter)
            if separate_handler:
                separate_handler(sprite_a, sprite_b, arbiter, space, data)

        if begin_handler:
            handler.begin = _f1
        if post_handler:
            handler.post_solve = _f2
        if pre_handler:
            handler.pre_solve = _f3
        if separate_handler:
            handler.separate = _f4
