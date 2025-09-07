"""Defines the game world."""
from model.entities import PhysicalEntity, Player
from control.physics import Pose
from model.systems.engines import TestShipEngine
from model.systems.reactors import TestShipReactor


class World:
    """Represents everything within the game world."""

    def __init__(self, size: tuple[int, int], entities: list[PhysicalEntity]):
        """
        :params size: the size of the game world (width, height)
        :param entities: a list of all entities. Has to at least contain a Player.
        """
        self.size: tuple[int, int] = size
        self.entities: entities = entities or []
        self.player_entity = self._get_player()


    def _get_player(self):
        """Return the Entity representing the player."""
        for entity in self.entities:
            if isinstance(entity, Player):
                return entity
        raise ValueError("No player entity found in the world.")


class Multiverse:
    """Library of existing worlds and tools to generate them."""
    @staticmethod
    def create_debug_world() -> World:
        """Tiny world with some test dummies."""
        world_width = 800
        world_height = 600
        return World(
            size=(world_width, world_height),
            entities=[
                Player(name="The Player", pose=Pose((world_width // 2, world_height // 2))) \
                    .upgrade(TestShipEngine).upgrade(TestShipReactor),
                PhysicalEntity(initial_pose=Pose((world_width // 2, world_height * 0.8)))
            ]
        )
