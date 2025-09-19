"""Defines the game world."""
import time

from numpy.random import random
from arcade import SpriteList, Sprite
from pymunk import Arbiter, Space

from control.physics import PhysicsEngine
from model.entities import Player, Asteroid, WorldBorder
from model.common import get_class_name
from model.systems.engines import TestShipEngine
from model.systems.reactors import TestShipReactor
from model.systems.shields import TestShipPhysicalDeflectionShields
from model.systems.structures import TestShipChassis


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

    def set_default_collision_handlers(self):
        self.physics_engine.add_collision_handler(get_class_name(WorldBorder), get_class_name(Asteroid),
                                                  begin_handler=self._collision_handler_border_asteroid)
        self.physics_engine.add_collision_handler(get_class_name(WorldBorder), get_class_name(Asteroid),
                                                  begin_handler=self._collision_handler_border_asteroid)

    @staticmethod
    def _collision_handler_border_asteroid(_border_sprite: Sprite, asteroid_sprite: Sprite, _arbiter, _space, _data):
        """Called when Asteroids collide with the world border."""
        asteroid_sprite.remove_from_sprite_lists()
        return False


class AstroidShowerWorld(World):
    """A small map that spawns random asteroids the player has to dodge."""
    def __init__(self, num_asteroids: int = 10, time_till_increase: float = None, size=(800, 800), *args, **kwargs):
        """
        :param num_asteroids: The number of asteroids in the beginning.
        :param time_till_increase: The number of seconds until the number of asteroids is increased by 1.
        :param args: arguments for the base class
        :param kwargs: arguments for the base class
        """
        super().__init__(size=size, *args, **kwargs)  # noqa
        self.num_asteroids = num_asteroids
        self.time_till_increase = time_till_increase
        self.last_time_asteroids_increased = time.perf_counter()

    def world_update(self):
        """Remove asteroids that left the world bounds and spawn new ones."""
        super().world_update()
        # increase number of asteroids if enough time has passed to increase the difficulty
        if self.time_till_increase:
            if time.perf_counter() - self.last_time_asteroids_increased >= self.time_till_increase:
                self.num_asteroids += 1
                self.last_time_asteroids_increased = time.perf_counter()

        # spawn new asteroids
        while len(self.entities) - 1 < self.num_asteroids:
            # for now asteroids spawn on the right side and fly to the left.
            x, y, angle = self.size[0] - 100, random() * self.size[1], random() * 360
            initial_speed = (-random() * 100, 0)

            asteroid = Asteroid(center_x=x, center_y=y, angle=angle)
            self.entities.append(asteroid)
            self.physics_engine.add_sprite(asteroid, **asteroid.get_physics())
            self.physics_engine.set_velocity(asteroid, initial_speed)
            self.physics_engine.set_rotation(asteroid, random() * 0.5)

    def set_default_collision_handlers(self):
        """Show impact for player collisions with asteroids."""
        super().set_default_collision_handlers()
        self.physics_engine.add_collision_handler(get_class_name(Player), get_class_name(Asteroid),
                                                  post_handler=self._collision_handler_player_asteroid)

    @staticmethod
    def _collision_handler_player_asteroid(player_sprite: Player, _asteroid_sprite: Sprite, arbiter: Arbiter,
                                           _space: Space, _data: dict):
        """Called when Players collides with the Asteroids."""
        player_sprite.structure.impact(arbiter.total_ke)


class Multiverse:
    """Library of existing worlds and tools to generate them."""
    @staticmethod
    def create_debug_world() -> World:
        """Tiny world with some test dummies."""
        world_width = 800
        world_height = 800

        player = (Player(name="The Player", center_x=world_width // 2, center_y=world_height // 2)
                  .upgrade(TestShipEngine).upgrade(TestShipReactor))
        start_entities = SpriteList()
        start_entities.extend((
            Asteroid(center_x=world_width // 2, center_y=world_height - 100),
        ))

        world = World(size=(world_width, world_height), player=player, entities=start_entities)
        return world

    @staticmethod
    def asteroid_shower() -> World:
        """Set up the AstroidShowerWorld world."""
        world_width = 800
        world_height = 600

        player = (Player(name="The Player", center_x=world_width // 2, center_y=world_height // 2)
                  .upgrade(TestShipEngine).upgrade(TestShipReactor).upgrade(TestShipChassis)
                  .upgrade(TestShipPhysicalDeflectionShields))
        world = AstroidShowerWorld(size=(world_width, world_height), player=player, num_asteroids=10)
        return world