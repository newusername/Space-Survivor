"""Contains the objects."""
from typing import Any, Self, Iterable, Iterator

import arcade
from arcade import SpriteList, Sprite

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
    :param sprite: The sprite representing the entity in the GUI. But is also used for collision detection.
    """
    def __init__(self, initial_pose: Pose = None, dynamic: Dynamics = None, sprite: Sprite = None):
        self.pose = initial_pose or Pose()
        if dynamic is None:
            dynamic = InertiaDynamics if GameSettings.player_dynamic == "inertia" else StaticDynamics
        self.dynamics = dynamic(initial_pose=initial_pose)
        if sprite:
            self.sprite = sprite
        else:
            sprite = Sprite()
            sprite.properties["is_placeholder"] = True
            self.sprite = sprite

class EntityList:
    """Holds all Entities and provides functionality for their interactions."""
    def __init__(self, entities: list[PhysicalEntity]=None):
        self.entities: list = []
        self.sprites = SpriteList(use_spatial_hash=True)

        self.add_entities(entities or [])
        self._player = None

    def __iter__(self) -> Iterator[PhysicalEntity]:
        """Iter over all entities."""
        return iter(self.entities)

    def iter_values(self) -> Iterator[tuple[PhysicalEntity, Sprite]]:
        """Iter over all pairs of entity and the corresponding sprite."""
        return iter(zip(self.entities, self.sprites))

    @property
    def player(self) -> "Combatant | None":
        """Return the Entity representing the player."""
        if self._player:
            return self._player
        else:
            for entity in self.entities:
                if isinstance(entity, Player):
                    self._player = entity
                    return entity
        return None

    def add_entity(self, entity: PhysicalEntity):
        """Adds a new entity to the world."""
        self.add_entities([entity])

    def add_entities(self, entities: Iterable[PhysicalEntity]):
        """Add multiple entities."""
        self.entities.extend(entities)
        sprites = [entity.sprite for entity in entities]
        self.sprites.extend(sprites)

    def remove_entity(self, entity: PhysicalEntity):
        """Removes the entity the sprite belongs to."""
        index = self.entities.index(entity)
        self.entities.pop(index)
        self.sprites.pop(index)

    def get_collisions(self) -> list[tuple[Sprite, Sprite]]:
        """Returns all entity collisions.

        Internally this uses a 2-step approach. It first tests for sprites with overlapping hitboxes and for those it
        checks the polygonal hit boxes.
        """
        collision_pairs = []
        for sprite in self.sprites:
            collided = arcade.check_for_collision_with_list(sprite, self.sprites)
            for other in collided:
                if sprite is not other:
                    # Store as sorted tuple to avoid duplicates (A,B) == (B,A)
                    pair = tuple(sorted((sprite, other), key=id))
                    collision_pairs.append(pair)

        # Remove duplicates
        collision_pairs = list(set(collision_pairs))
        return collision_pairs


class Combatant(PhysicalEntity):
    """Represents all objects that partake in battle."""
    def __init__(self, *, pose: Pose = None, dynamic: Dynamics = None, gui: Any = None):
        """Create the most basic combatant. Use the upgrade() function to customize it."""
        super().__init__(initial_pose=pose, dynamic=dynamic)
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




