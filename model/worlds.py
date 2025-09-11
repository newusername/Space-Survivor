"""Defines the game world."""
import time

import numpy as np
from numpy.random import random
import arcade

from model.entities import PhysicalEntity, Player, EntityList, Asteroid, Border
from control.physics import Pose, InertiaDynamics, ImmovableDynamics
from model.systems.engines import TestShipEngine
from model.systems.reactors import TestShipReactor


class World:
    """Represents everything within the game world."""

    def __init__(self, size: tuple[int, int], entities: list[PhysicalEntity]=()):
        """
        :params size: the size of the game world (width, height)
        :param entities: a list of all entities. Has to at least contain a Player.
        """
        self.size: tuple[int, int] = size
        walls = self.create_world_border()
        self.entities: EntityList = EntityList(list(entities) + walls)

    def world_update(self):
        """Is called during the simulation update. Is intended to handle world specific events."""

    def create_world_border(self, wall_color = arcade.color.GRAY) -> list[PhysicalEntity]:
        """Due to how my physics works, I need a lot of small walls."""
        wall_part_length = 10
        walls = [
            *[arcade.SpriteSolidColor(wall_part_length, 10, x, 5, wall_color) for x  in range(0, self.size[0], wall_part_length)],  # bottom
            *[arcade.SpriteSolidColor(wall_part_length, 10, x, self.size[1] - 5, wall_color) for x  in range(0, self.size[0], wall_part_length)],  # top
            *[arcade.SpriteSolidColor(10, wall_part_length, 5, y, wall_color) for y  in range(0, self.size[0], wall_part_length)],  # left
            *[arcade.SpriteSolidColor(10, wall_part_length, self.size[0] - 5, y, wall_color) for y  in range(0, self.size[0], wall_part_length)],  # right
        ]
        entities = []
        for sprite in walls:
            pose = Pose(position=(sprite.center_x, sprite.center_y))
            entities.append(Border(initial_pose=pose, sprite=sprite, dynamics=ImmovableDynamics(initial_pose=pose)))
        return entities


class AstroidShowerWorld(World):
    """A small map that spawns random asteroids the player has to dodge."""
    def __init__(self, num_asteroids: int = 10, time_till_increase: float = None, size=(800, 800), *args, **kwargs):
        """
        :param num_asteroids: The number of asteroids in the beginning.
        :param time_till_increase: The number of seconds until the number of asteroids is increased by 1.
        :param args: arguments for the base class
        :param kwargs: arguments for the base class
        """
        super().__init__(size=size, *args, **kwargs)
        self.num_asteroids = num_asteroids
        self.asteroids = []
        self.time_till_increase = time_till_increase
        self.last_time_asteroids_increased = time.perf_counter()

    def world_update(self):
        """Remove asteroids that left the world bounds and spawn new ones."""
        # remove out of bounds asteroids
        for entity in self.asteroids:
            x, y = entity.pose.position
            if x + entity.sprite.size[0] < 0 or x - entity.sprite.size[0] > self.size[0]:
                self.entities.remove_entity(entity)
                self.asteroids.remove(entity)
            if y + entity.sprite.size[1] < 0 or x - entity.sprite.size[1] > self.size[1]:
                self.entities.remove_entity(entity)
                self.asteroids.remove(entity)

        # increase number of asteroids
        if self.time_till_increase:
            if time.perf_counter() - self.last_time_asteroids_increased >= self.time_till_increase:
                self.num_asteroids += 1
                self.last_time_asteroids_increased = time.perf_counter()

        # spawn new asteroids
        while len(self.asteroids) < self.num_asteroids:
            # for now asteroids spawn on the right side and fly to the left.
            pose = Pose(position=(self.size[0] - 50, random() * self.size[1]),
                        orientation=random() * 360)
            dynamics = InertiaDynamics(initial_pose=pose,
                                       initial_translation=np.array((-3 * random() - 1, 0.2 * (random() - 0.5))),
                                       initial_rotation=random() * 0.5)
            asteroid = Asteroid(initial_pose=pose, dynamics=dynamics)
            self.entities.add_entity(asteroid)
            self.asteroids.append(asteroid)

class Multiverse:
    """Library of existing worlds and tools to generate them."""
    @staticmethod
    def create_debug_world() -> World:
        """Tiny world with some test dummies."""
        world_width = 800
        world_height = 600

        start_entities = (
            Player(name="The Player", initial_pose=Pose((world_width // 2, world_height // 2)))
                .upgrade(TestShipEngine).upgrade(TestShipReactor),
            # PhysicalEntity(initial_pose=Pose((world_width // 2, world_height * 0.8)))
        )

        # world = World(size=(world_width, world_height))
        world = AstroidShowerWorld(num_asteroids=10)
        world.entities.add_entities(start_entities)
        return world