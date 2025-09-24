from dataclasses import dataclass

from model.systems.common import System, Status
from settings import GameSettings


@dataclass(kw_only=True)
class Reactor(System):
    """Defines an entities ability to generate and store energy.

    From an implementation point of view all energy is stored in the capacitors first and cannot be accessed directly.

    :param energy_production: The amount of energy produced per tick.
    :param capacitors_limit: The amount of energy that can be stored.
    :param capacitors_storage: How much energy the capacitors are storing right now.

    Effects of system damages:
        light_damage:
            - slightly decreased capacitors_limit
        heavy_damage:
            - further decreased capacitors_limit
            - reduced reactor energy production
    """
    name: str = "Reactor"
    energy_production: float = 0
    max_energy_production: float = energy_production
    capacitors_limit: float = 0
    max_capacitors_limit: float = capacitors_limit
    capacitors_storage: float = 0
    max_capacitors_storage: float = capacitors_storage
    status: Status = Status.nominal
    light_damage_multiplicator = 0.8
    heavy_damage_multiplicator = 0.5
    heavy_damage_energy_production_reduction = 0.7

    def activate(self):
        """Simulates a tick."""
        if self.status == Status.destroyed:
            return
        if self.status == Status.heavy_damage:
            energy_production = self.energy_production * self.heavy_damage_energy_production_reduction
        else:
            energy_production = self.energy_production

        self.capacitors_storage = min(self.capacitors_limit, max(0., self.capacitors_storage + energy_production))

    def power(self, cost: float, source: System = None) -> bool:
        """Used to power a device. Returns a bool if there was enough energy."""
        if self.status == Status.destroyed:
            return False

        cost *= GameSettings.energy_multiplier
        if cost > self.capacitors_storage:
            print("Not enough power" + (f" for {source.name}" if source else "") + "!")
            return False
        else:
            self.capacitors_storage -= cost
            return True

    def set_status(self, status: Status):
        """Set a new status and update the reactor accordingly."""
        match status:
            case Status.nominal:
                self.energy_production = self.max_energy_production
                self.capacitors_limit = self.max_capacitors_limit
            case Status.light_damaged:
                self.capacitors_limit = self.light_damage_multiplicator * self.max_capacitors_limit
                self.capacitors_storage = self.light_damage_multiplicator * self.max_capacitors_storage
            case Status.heavy_damage:
                self.capacitors_limit = self.heavy_damage_multiplicator * self.max_capacitors_limit
                self.capacitors_storage = self.heavy_damage_multiplicator * self.max_capacitors_storage

@dataclass
class TestShipReactor(Reactor):
    """For testing in debug mode."""
    energy_production: float = 10
    capacitors_limit: float = 3000
    capacitors_storage: float = 3000