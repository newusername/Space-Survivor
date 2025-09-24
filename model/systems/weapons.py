import time
from dataclasses import dataclass

from pymunk import Vec2d

from control.user_input import UserInput
from model.systems.common import System


@dataclass(kw_only=True)
class Railgun(System):
    name: str = "Railgun"
    power_consumption: float = 500.  # todo that should be the consequence of mass and speed.
    projectile_mass: float = 2.
    projectile_speed: float = 500.
    damage_multiplier: float = 1.
    cool_down: float = 1.  # time in seconds between shoots
    _time_of_last_shot: float = 0.

    def activate(self, user_input: UserInput):
        """Create a new railgun bullet shooting straight ahead."""
        if not user_input.fire_rail_guns or self._time_of_last_shot + self.cool_down > time.perf_counter():
            user_input.fire_rail_guns = False
            return None

        if self.entity.reactor.power(self.power_consumption, self):
            user_input.fire_rail_guns = False
            self._time_of_last_shot = time.perf_counter()
            translational_speed = Vec2d(x=0, y=1).rotated_degrees(-self.entity.angle) * self.projectile_speed
            origin = self.entity.position + Vec2d(0, self.entity.size[0] / 2).rotated_degrees(-self.entity.angle)
            return dict(
                damage_multiplier=self.damage_multiplier,
                center_x=origin.x, center_y=origin.y, angle=self.entity.angle,
                scale=0.1,
                mass=self.projectile_mass, translational_speed=translational_speed,
                path_or_texture=":resources:/images/pinball/pool_cue_ball.png")

        user_input.fire_rail_guns = False
        return None


@dataclass(kw_only=True)
class TestShipRailgun(Railgun):
    """Insta kill weapon."""
    damage_multiplier: float = 9999.


@dataclass(kw_only=True)
class Lasers(System):
    name: str = "Lasers"

    def activate(self, *args, **kwargs):
        raise NotImplemented
