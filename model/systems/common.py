from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum, auto


@dataclass
class SystemEvent:
    """
    :param time: the tick number the event occurred."""
    time: int

@dataclass(kw_only=True)
class System(ABC):
    """Baseclass for all systems.

    :param name: Name of the system
    :param entity: The Combatant entity the system belongs to.
    """
    name: str
    entity: "Combatant"
    events: list[SystemEvent] = field(default_factory=list)

    @abstractmethod
    def activate(self, *args, **kwargs):
        """Activates the systems function. This is called every tick. The effects depend on the system."""
        raise NotImplemented("abstract method")


class Status(StrEnum):
    """Lists all possible status of a system.

     The concrete effects of the status depends on the system. But roughly follows this pattern:
     nominal: everything working as intended
     slightly_damaged: system still works as intended, but minor downsides like increased energy consumption
     heavy_damage: system performance notably degraded, continued usage may cause fatal damage to the system.
     destroyed: system offline
     """
    nominal = auto()
    light_damaged = auto()
    heavy_damage = auto()
    destroyed = auto()