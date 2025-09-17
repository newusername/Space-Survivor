from dataclasses import dataclass

from model.systems.common import System


@dataclass(kw_only=True)
class Shields(System):
    """Defines the shields protecting the entity.

    Ideas:
    - use the physics radius to make the shield extend the ship for collisions (this would be an easy start, but having
     it more like force field that applies force to incoming projectiles to deflect them would much cooler. Classical
     shields are easier from game balancing stand point though. Maybe both?)
    """
