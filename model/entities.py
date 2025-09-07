"""Contains the objects."""
from typing import Any, Self

from control.physics import Pose, Dynamics, InertiaDynamics, StaticDynamics
from model.systems.common import System
from model.systems.engines import Engine
from model.systems.reactors import Reactor
from model.systems.sensors import Sensor
from model.systems.structures import Structure
from model.systems.weapons import WeaponSystems
from settings import GameSettings


class PhysicalEntity:
    """Base class for all interactive objects that should be rendered.

    :param initial_pose: Represents the position and orientation of the object.
    :param dynamic: Defines how the pose is updated.
    :param gui: Optional parameter that can be used by the GUI to store information with the object directly, such as
        the sprite. This parameter is not used by this class at all.  # todo Is there a better way to do this?
    """
    def __init__(self, initial_pose: Pose = None, dynamic: Dynamics = None, gui: Any = None):
        self.pose = initial_pose or Pose()
        if dynamic is None:
            dynamic = InertiaDynamics if GameSettings.player_dynamic == "inertia" else StaticDynamics
        self.dynamics = dynamic(initial_pose=initial_pose)
        self.gui: Any = gui


class Combatant(PhysicalEntity):
    """Represents all objects that partake in battle."""
    def __init__(self, *, pose: Pose = None, dynamic: Dynamics = None, gui: Any = None):
        """Create the most basic combatant. Use the upgrade() function to customize it."""
        super().__init__(initial_pose=pose, dynamic=dynamic, gui=gui)
        self.reactor = Reactor(entity=self)
        self.engine = Engine(entity=self)
        self.structure = Structure(entity=self)
        self.weapons = WeaponSystems(entity=self)
        self.sensor = Sensor(entity=self)

    def upgrade(self, system: type[System], system_parameter: dict = None) -> Self:
        """Replaces an old system with a new one."""
        system_parameter = system_parameter or {}
        system_object = system(entity=self, **system_parameter)
        if issubclass(system, Reactor):
            self.reactor = system_object
        elif issubclass(system, Engine):
            self.engine = system_object
        elif issubclass(system, Structure):
            self.structure = system_object
        elif issubclass(system, WeaponSystems):
            self.weapons = system_object
        elif issubclass(system, Sensor):
            self.sensor = system_object
        else:
            raise ValueError(f"Unknown System class {type(system)}.")

        return self




class Player(Combatant):
    """Represents the player's avatar in the world."""
    def __init__(self, *, name: str, **kwargs):
        super().__init__(**kwargs)
        self.name = name




