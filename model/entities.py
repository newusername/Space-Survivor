"""Contains the objects."""
from typing import Any

from control.physics import Pose, Dynamics, InertiaDynamics, StaticDynamics
from model.systems.engines import Engine
from model.systems.reactors import Reactor
from model.systems.sensors import Sensor
from model.systems.structures import Structure
from model.systems.weapons import WeaponSystems
from settings import GameSettings


class PhysicalEntity:
    """Base class for all interactive objects that should be rendered.

    :param pose: Represents the position and orientation of the object.
    :param dynamic: Defines how the pose is updated.
    :param gui: Optional parameter that can be used by the GUI to store information with the object directly, such as
        the sprite. This parameter is not used by this class at all.  # todo Is there a better way to do this?
    """
    def __init__(self, pose: Pose = None, dynamic: Dynamics = None, gui: Any = None):
        self.pose = pose or Pose()
        if dynamic is None:
            dynamic = InertiaDynamics if GameSettings.player_dynamic == "inertia" else StaticDynamics
        self.dynamics = dynamic(pose=pose)
        self.gui: Any = gui


class Combatant(PhysicalEntity):
    """Represents all objects that partake in battle."""
    def __init__(self, *, pose: Pose = None, dynamic: Dynamics = None, gui: Any = None,
                 reactor: Reactor = None, engine: Engine = None, structure: Structure = None,
                 weapons: WeaponSystems = None, sensor: Sensor = None):
        super().__init__(pose=pose, dynamic=dynamic, gui=gui)
        self.reactor = reactor or Reactor()
        self.engine = engine or Engine()
        self.structure = structure or Structure()
        self.weapons = weapons or WeaponSystems()
        self.sensor = sensor or Sensor()


class Player(Combatant):
    """Represents the player's avatar in the world."""
    def __init__(self, *, name: str, **kwargs):
        super().__init__(**kwargs)
        self.name = name




