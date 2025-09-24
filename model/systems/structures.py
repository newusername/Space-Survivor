from dataclasses import dataclass

from model.common import AsteroidSizes, Materials
from model.systems.common import System
from settings import GameSettings


@dataclass(kw_only=True)
class Structure(System):
    """Defines the structure of an entity."""
    name: str = "Structure"
    max_hp: float = 1
    hp_regen: float = 0  # hp regeneration per second
    sturdiness: float = 0  # subtracts all kinetic damage by this value
    kinetic_factor: float = 1  # kinetic damage multiplier
    time_left_invulnerable: float = 0.

    def __post_init__(self):
        self._hp: float = self.max_hp

    @property
    def is_invulnerable(self):
        return self.time_left_invulnerable > 0

    @property
    def hp(self):
        return self._hp

    @hp.setter
    def hp(self, value: float):
        self._hp = min(max(0., value), self.max_hp)

    def activate(self, *args, **kwargs):
        """Activate structure abilities like self-healing."""
        self.time_left_invulnerable = max(0., self.time_left_invulnerable - 1 / GameSettings.simulation_speed)
        self.hp += self.hp_regen / GameSettings.simulation_speed

    def impact(self, kinetic_energy: float):
        """Called when kinetic energy is applied to the entity. E.g. when colliding with an asteroid."""
        if not self.is_invulnerable:
            kinetic_energy = max(0., kinetic_energy * self.kinetic_factor - self.sturdiness)
            self.hp -= kinetic_energy


@dataclass(kw_only=True)
class AsteroidStructure(Structure):
    """A huge piece of mostly solid rock floating through space. Comes in infinitely many sizes from tiny to moon.

    Usually only needs the size. The other structures stats are set depending on this size class.
    """
    name: str = "Asteroid"
    size: AsteroidSizes
    material: Materials
    mass: float

    def  __post_init__(self):
        """Sets the structures stats depending on the size class."""
        self.max_hp: float = self._asteroid_max_hp_for_size()
        super().__post_init__()
        self.sturdiness: float = self.max_hp * 0.1
        self.kinetic_factor: float = max(0., 1 - list(AsteroidSizes).index(self.size) / 10)

    def _asteroid_max_hp_for_size(self):
        """Returns the max hp for an asteroid based on the size, mass and material."""  # todo actually do that :D
        hp_map = {
            AsteroidSizes.tiny: 10_000,
            AsteroidSizes.small: 100_000,
            AsteroidSizes.med: 300_000,
            AsteroidSizes.big: 1_000_000
        }
        return hp_map[self.size]


@dataclass(kw_only=True)
class TestShipChassis(Structure):
    """Defines the structure of the test ship."""
    name: str = "Structure"
    max_hp: float = 1000
    hp_regen: float = 10
    sturdiness: float = 500

