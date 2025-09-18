from dataclasses import dataclass

from model.systems.common import System
from settings import GameSettings


@dataclass(kw_only=True)
class Structure(System):
    """Defines the structure of an entity."""
    name: str = "Structure"
    max_hp: float = 1
    hp_regen: float = 0  # hp regeneration per second
    shock_absorber: float = 0  # all impact damage is reduced by this number

    def __post_init__(self):
        self._hp: float = self.max_hp

    @property
    def hp(self):
        return self._hp

    @hp.setter
    def hp(self, value: float):
        self._hp = min(max(0., value), self.max_hp)

    def activate(self, *args, **kwargs):
        """Activate structure abilities like self-healing."""
        self.hp += self.hp_regen / GameSettings.simulation_speed

    def impact(self, kinetic_energy: float):
        """Called when kinetic energy is applied to the entity. E.g. when colliding with an asteroid."""
        kinetic_energy = max(0., kinetic_energy - self.shock_absorber)
        self.hp -= kinetic_energy


@dataclass(kw_only=True)
class TestShipChassis(Structure):
    """Defines the structure of the test ship."""
    name: str = "Structure"
    max_hp: float = 1000
    hp_regen: float = 10
    shock_absorber: float = 500

