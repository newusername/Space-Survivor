"""Defines the game world."""
import time

from numpy.random import random
from arcade import SpriteList, Sprite
from pymunk import Arbiter, Space

from control.physics import PhysicsEngine
from model.common import AsteroidSizes
from model.entities import Player, Asteroid, WorldBorder, PhysicalEntity, Projectile
from model.systems.engines import TestShipEngine
from model.systems.reactors import TestShipReactor
from model.systems.shields import TestShipPhysicalDeflectionShields
from model.systems.structures import TestShipChassis
from model.systems.weapons import Railgun, TestShipRailgun


class World:
    """Represents everything within the game world."""

    def __init__(self, size: tuple[int, int], player: Player, entities: SpriteList = None):
        """
        :params size: the size of the game world (width, height)
        """
        self.size: tuple[int, int] = size
        self.player: Player = player
        self.entities: SpriteList = entities or SpriteList()
        self.entities.append(player)
        self.physics_engine = PhysicsEngine(damping=1, gravity=(0, 0))
        for entity in self.entities:
            self.physics_engine.add_sprite(entity, **entity.get_physics())
        self.set_default_collision_handlers()

        self.walls = WorldBorder.create_world_border(size)
        for wall in self.walls:
            self.physics_engine.add_sprite(wall, **WorldBorder.get_physics()) # todo check if the border cause collisions. (They touch, but dont overlap.)

    def world_update(self):
        """Is called during the simulation update. Is intended to handle world specific events."""
        self.physics_engine.step()

    def add_entity(self, entity_class: type[PhysicalEntity], entity_parameters: dict) -> PhysicalEntity:
        """Create and add the entity to the world."""
        entity = entity_class(physics_engine=self.physics_engine, **entity_parameters)
        self.entities.append(entity)
        self.physics_engine.add_sprite(entity, **entity.get_physics())
        with self.physics_engine.set_current_entity(entity):
            if "translational_speed" in entity_parameters:
                self.physics_engine.set_translational_speed(entity_parameters["translational_speed"])
            if "rotational_speed" in entity_parameters:
                self.physics_engine.set_rotational_speed(entity_parameters["rotational_speed"])
            if "time_left_invulnerable" in entity_parameters:
                entity.structure.time_left_invulnerable = entity_parameters["time_left_invulnerable"]
        return entity

    def set_default_collision_handlers(self):
        self.physics_engine.add_collision_handler(
            PhysicalEntity.collision_type_name, PhysicalEntity.collision_type_name,
            pre_handler=self._pre_handler_collision_handler_physical_entities,
            post_handler=self._post_handler_collision_handler_physical_entities)
        self.physics_engine.add_collision_handler(
            WorldBorder.collision_type_name, PhysicalEntity.collision_type_name,
            begin_handler=self._collision_handler_border)

    @staticmethod
    def _pre_handler_collision_handler_physical_entities(sprite_1: PhysicalEntity, sprite_2: PhysicalEntity,
                                                         arbiter: Arbiter, _space: Space, _data: dict):
        """Called when 2 physical entities collide and decides if the collision should be happening or not."""
        return True

    @classmethod
    def _post_handler_collision_handler_physical_entities(cls, sprite_1: PhysicalEntity, sprite_2: PhysicalEntity,
                                                          arbiter: Arbiter, _space: Space, _data: dict):
        """Called when 2 physical entities collide."""
        cls._handle_damage(sprite_1, sprite_2, arbiter)

    @staticmethod
    def _handle_damage(sprite_1: PhysicalEntity, sprite_2: PhysicalEntity, arbiter: Arbiter):
        """Deal damage to the involved entities."""
        for damage_recipient, damage_dealer in ((sprite_1, sprite_2), (sprite_2, sprite_1)):
            if isinstance(damage_recipient, PhysicalEntity) and not damage_recipient.structure.is_invulnerable:
                multiplier = damage_dealer.damage_multiplier if hasattr(damage_dealer, "damage_multiplier") else 1.
                damage_recipient.structure.impact(arbiter.total_ke * multiplier)

    @staticmethod
    def _collision_handler_border(_border_sprite: Sprite, other_sprite: Sprite, _arbiter, _space, _data):
        """Called when Entities collide with the world border."""
        if not isinstance(other_sprite, Player):
            other_sprite.remove_from_sprite_lists()
        return True


class AstroidShowerWorld(World):
    """A small map that spawns random asteroids the player has to dodge."""
    def __init__(self, num_initial_asteroids: int = 10, asteroid_spawn_interval: float = 1,
                 size=(800, 800), *args, **kwargs):
        """
        :param num_initial_asteroids: The number of asteroids spawned at game start.
        :param asteroid_spawn_interval: The time in seconds till the next asteroid spawns.
        :param args: arguments for the base class
        :param kwargs: arguments for the base class
        """
        super().__init__(size=size, *args, **kwargs)  # noqa
        self.num_initial_asteroids: int = num_initial_asteroids
        self.asteroid_spawn_interval: float = asteroid_spawn_interval
        self.last_time_asteroids_increased: float = time.perf_counter()
        self._time_last_asteroid_spawned: float = time.perf_counter()

        # spawn initial asteroids
        for _ in range(num_initial_asteroids):
            self.spawn_asteroid()

    def world_update(self):
        """Remove asteroids that left the world bounds and spawn new ones."""
        super().world_update()

        if time.perf_counter() - self._time_last_asteroid_spawned >= self.asteroid_spawn_interval:
            self.spawn_asteroid()
            self._time_last_asteroid_spawned = time.perf_counter()

    def spawn_asteroid(self):
        # for now asteroids spawn on the right side and fly to the left.
        x, y, angle = self.size[0] - 100, random() * self.size[1], random() * 360
        initial_speed = (-random() * 90, 0)

        asteroid = Asteroid(center_x=x, center_y=y)
        asteroid.structure.time_left_invulnerable = 1
        self.entities.append(asteroid)
        self.physics_engine.add_sprite(asteroid, **asteroid.get_physics())
        with self.physics_engine.set_current_entity(asteroid):
            self.physics_engine.set_translational_speed(initial_speed)
            self.physics_engine.set_rotational_speed(random() * 0.5)


class Multiverse:
    """Library of existing worlds and tools to generate them."""
    @staticmethod
    def create_debug_world() -> World:
        """Tiny world with some test dummies."""
        world_width = 800
        world_height = 800

        player = (Player(name="The Player", center_x=world_width // 2, center_y=world_height // 2)
                  .upgrade(TestShipEngine).upgrade(TestShipReactor).upgrade(TestShipChassis)
                  .upgrade(TestShipPhysicalDeflectionShields).upgrade(TestShipRailgun))
        world = World(size=(world_width, world_height), player=player)
        world.add_entity(Asteroid, dict(center_x=world_width // 2, center_y=world_height - 250, size=AsteroidSizes.big))
        return world

    @staticmethod
    def asteroid_shower() -> World:
        """Set up the AstroidShowerWorld world."""
        world_width = 800
        world_height = 600

        player = (Player(name="The Player", center_x=world_width // 2, center_y=world_height // 2)
                  .upgrade(TestShipEngine).upgrade(TestShipReactor).upgrade(TestShipChassis)
                  .upgrade(TestShipPhysicalDeflectionShields).upgrade(Railgun).upgrade(TestShipRailgun))
        world = AstroidShowerWorld(size=(world_width, world_height), player=player, num_initial_asteroids=10,
                                   asteroid_spawn_interval=1)
        return world