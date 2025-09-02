"""Contains the objects."""
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from numpy import iterable


class Pose:
    """Represents the spatial position and orientation of PhysicalEntities.

    :params position: 2D position of the object in the world. (width x height)
    :params orientation: 1D orientation of the object in clockwise degrees within the interval [0, 360).
    """
    def __init__(self, position: iterable = None, orientation: float = 0):
        self.position: np.array = np.array(position, dtype=float) if position else np.zeros((2,))
        assert self.position.size == 2, "position ahs to be 2D"
        self.orientation: float = orientation

    def relative_move(self, width: float, height: float):
        """Gets a change in position and updates the position."""
        self.position[0] += width
        self.position[1] += height

    def relative_rotation(self, angle: float):
        """Gets a rotation angle and updates the orientation. Positive numbers will rotate clockwise."""
        self.orientation += angle
        self.orientation = self.orientation % 360


@dataclass(kw_only=True)
class PhysicalEntity:
    """Base class for all interactive objects that should be rendered."""
    pose: Pose = field(default_factory=Pose)
    gui: Any = None  # todo the idea is that the GUI can use this to store info for this entity like sprites. Is there a better way to do this?


class Structure:
    """Defines the structure of an entity."""


class WeaponSystems:
    """Defines the weapons of an entity"""


class Sensor:
    """Defines an entities capabilities to detect other entities."""


class Engine:
    """Defines how an entity can move."""


class Reactor:
    """Defines an entities ability to generate and store energy."""


@dataclass(kw_only=True)
class Combatant(PhysicalEntity):
    """Represents all objects that partake in battle."""
    structure: Structure = field(default_factory=lambda: Structure())
    weapon: WeaponSystems = field(default_factory=lambda: WeaponSystems())
    engine: Engine = field(default_factory=lambda: Engine())
    reactor: Reactor = field(default_factory=lambda: Reactor())
    sensor: Sensor = field(default_factory=lambda: Sensor())


@dataclass
class Player(Combatant):
    """Represents the player's avatar in the world."""
    name: str




