from dataclasses import dataclass

import numpy as np
import pymunk

from model.systems.common import System
from settings import GameSettings


@dataclass(kw_only=True)
class Shields(System):
    """Defines the shields protecting the entity.

    Ideas:
    - use the physics radius to make the shield extend the ship for collisions (this would be an easy start, but having
     it more like force field that applies force to incoming projectiles to deflect them would much cooler. Classical
     shields are easier from game balancing standpoint though. Maybe both?)
    """
    name: str = "Shields"
    activity_level: float = 0  # the shield "powers" down after use. This does not use additional energy and is only for show.
    deflection_power: float = 0  # how strong the force is that the shield applies to incoming objects to deflect them away from the entity
    power_consumption: float = 0 # how much power is consumed when an object is deflected
    radius: float = 0

    def activate(self, *args, **kwargs):
        pass


@dataclass(kw_only=True)
class DeflectionShields(Shields):
    # very early version
    name: str = "Deflection Shield"
    collision_type_name: str = "deflection_shield"
    deflection_power: float = 0  # how strong the force is that the shield applies to incoming objects to deflect them away from the entity
    power_consumption: float = 0 # how much power is consumed when an object is deflected
    radius: float = 1  # the distance from the ship the shield start to apply force. This is in addition to the entites size

    is_initialised = False


@dataclass(kw_only=True)
class TestShipPhysicalDeflectionShields(DeflectionShields):
    # very early version
    name: str = "Deflection Shield of the Testship"
    deflection_power: float = 1000  # how strong the force is that the shield applies to incoming objects to deflect them away from the entity
    power_consumption: float = 50 # how much power is consumed when an object is deflected
    radius: float = 20  # the distance from the ship the shield start to apply force. This is in addition to the entities size

    is_initialised = False

    def _shield_collision(self, arbiter, _space, _data):
        """Deflect other entities away from the shielded entity."""
        # todo just saw there is sprite1, sprite2 = self.physics_engine.get_sprites_from_arbiter(arbiter). Use my physics engine interface instead of using Pymunk directly.
        own_body = arbiter.shapes[0].body
        other_body = arbiter.shapes[1].body
        if not np.allclose(own_body.position, self.entity.position, rtol=5):
            # we cannot rely on the correct order for the shapes
            own_body, other_body = other_body, own_body
        distance = min(self.radius, abs(arbiter.contact_point_set.points[0].distance))

        if distance != 0:
            # Calculate repelling force
            force_magnitude = self.deflection_power / distance  # stronger when closer  # todo make it distance**2?
            if self.entity.reactor.power(self.power_consumption, self):
                self.activity_level = 1
                force = (other_body.position - own_body.position).normalized() * force_magnitude # todo would it be smarter to deflect at at perpendicular instead?
                force = force.rotated(-other_body.angle)
                other_body.apply_force_at_local_point(force, (0, 0))  # todo would be more correct to apply the force at the contact point

        return False  # don't let sensor block movement

    @property
    def shield_radius(self):
        """The maximum distance the shield affects other objects from the center of the entity."""
        return max(self.entity.size) / 2 + self.radius

    def activate(self, *args, **kwargs):
        """Apply forces on all other objects within range of the shield to deflect them away from the ship."""
        self.activity_level = max(0., self.activity_level - 1 / GameSettings.simulation_speed)
        if not self.is_initialised:
            """Add a sensor to the engine that detects the collisions."""
            self.is_initialised = True

            shield_shape = pymunk.Circle(self.physics_engine.sprites[self.entity].body, self.shield_radius)
            shield_shape.sensor = True  # doesn't block but detects collisions
            class_name = TestShipPhysicalDeflectionShields.collision_type_name
            space = self.physics_engine.space
            if class_name not in self.physics_engine.collision_types:
                self.physics_engine.collision_types.append(TestShipPhysicalDeflectionShields.collision_type_name)
            class_id = self.physics_engine.collision_types.index(class_name)
            shield_shape.collision_type = class_id
            space.add(shield_shape)
            handler = space.add_wildcard_collision_handler(class_id)
            handler.pre_solve = self._shield_collision
