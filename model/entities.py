"""Contains the objects."""
from typing import Self, Iterable, Iterator

import numpy as np
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
    :param dynamics: Defines how the pose is updated.
    :param sprite: The sprite representing the entity in the GUI. But is also used for collision detection.
    """
    def __init__(self, *, initial_pose: Pose = None, dynamics: Dynamics = None, sprite: Sprite = None):
        self.pose = initial_pose or Pose()
        if dynamics is None:
            dynamics = InertiaDynamics if GameSettings.player_dynamic == "inertia" else StaticDynamics
            dynamics = dynamics(initial_pose=initial_pose)
        self.dynamics = dynamics
        if sprite:
            self.sprite = sprite
        else:
            sprite = Sprite()
            sprite.properties["is_placeholder"] = True
            self.sprite = sprite
        self.sprite.properties["entity"] = self

    def collision(self):
        """Is called when the entity is involved in a collision."""

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


class Border(PhysicalEntity):
    """World border."""


class Asteroid(PhysicalEntity):
    """A simple peace of rock floating through space."""
    def __init__(self, initial_pose: Pose = None, size: str = None, sprite: Sprite=None, *args, **kwargs):
        """Create a random sized asteroid if no sprite is given."""
        if sprite is None:
            if size is None:
                size = np.random.choice(["tiny", "small", "med", "big"])
            number = np.random.randint(1, (4 if size == "large" else 2) + 1)
            x, y = initial_pose.position
            angle = initial_pose.orientation
            texture = arcade.load_texture(f":resources:images/space_shooter/meteorGrey_{size}{number}.png",
                                          hit_box_algorithm=arcade.hitbox.algo_detailed)
            sprite = Sprite(texture, center_x=x, center_y=y, angle=angle, scale=(np.random.random((2,)) + 0.5),
                            hit_box_algorithm=arcade.hitbox.algo_detailed)
        super().__init__(initial_pose=initial_pose, sprite=sprite, *args, **kwargs)


class Combatant(PhysicalEntity):
    """Represents all objects that partake in battle."""
    def __init__(self, initial_pose: Pose = None, dynamics: Dynamics = None, *args, **kwargs):
        """Create the most basic combatant. Use the upgrade() function to customize it."""
        super().__init__(initial_pose=initial_pose, dynamics=dynamics, *args, **kwargs)
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
    def __init__(self, sprite: Sprite = None, name: str = "Player", *args, **kwargs):
        texture = arcade.load_texture(":resources:images/space_shooter/playerShip1_blue.png",
                                      hit_box_algorithm=arcade.hitbox.algo_detailed)
        sprite = sprite or Sprite(texture)
        super().__init__(sprite=sprite, *args, **kwargs)
        sprite.center_x, sprite.center_y = self.pose.position[0], self.pose.position[1]
        self.name = name

    def collision(self):
        """Is called when the entity is involved in a collision."""
        print("Player Collision detected!")