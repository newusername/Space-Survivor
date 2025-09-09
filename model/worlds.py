"""Defines the game world."""
from model.entities import PhysicalEntity, Player, EntityList
from control.physics import Pose
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
        self.entities: EntityList = EntityList(entities)


class Multiverse:
    """Library of existing worlds and tools to generate them."""
    @staticmethod
    def create_debug_world() -> World:
        """Tiny world with some test dummies."""
        world_width = 800
        world_height = 600

        start_entities = (
            Player(name="The Player", pose=Pose((world_width // 2, world_height // 2)))
                .upgrade(TestShipEngine).upgrade(TestShipReactor),
            PhysicalEntity(initial_pose=Pose((world_width // 2, world_height * 0.8))))

        world = World(size=(world_width, world_height))
        world.entities.add_entities(start_entities)
        return world