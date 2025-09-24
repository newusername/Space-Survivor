"""Updates the Model with passing time and user inputs."""
# todo for now the control is called by the GUI. Simply because I am too lazy to set up proper multithreading. Later it should use the run method.
import time

from control.user_input import UserInput
from model.entities import Combatant, RailgunProjectile, PhysicalEntity
from model.worlds import World
from settings import GameSettings


class GUIInfo:
    """Contains states that should be represented by the GUI.

    :param player_damage: signals the GUI that the player was damaged.
    """
    player_damage: bool = False


class GameControl:
    def __init__(self, world: World):
        """
        :param world: The world to control.
        """
        self.world = world
        self.simulation_speed = GameSettings.simulation_speed

        self.user_input = UserInput()
        self.gui_info = GUIInfo()
        self.is_running: bool = True
        self.last_update: float = 0

    def run(self):
        """Start running the simulation."""
        while self.is_running:
            seconds_since_last_tick = time.perf_counter() - self.last_update
            if seconds_since_last_tick < 1 / self.simulation_speed:
                time.sleep(1 / self.simulation_speed - seconds_since_last_tick)

            self.simulation_tick()
            self.last_update = time.perf_counter()

    def simulation_tick(self):
        """Update the world."""
        self._handle_non_game_user_input()
        self.world.world_update()
        for entity in self.world.entities:
            if isinstance(entity, PhysicalEntity):
                if entity.structure.hp == 0:
                    entity.destroy(self.world.add_entity)
                    continue
                entity.structure.activate()

            if isinstance(entity, Combatant):
                entity.reactor.activate()
                if entity is self.world.player:
                    entity.engine.activate(self.user_input)  # noqa does not recognice the check for Combatant
                else:
                    pass  # todo implement logic to move NPCs
                entity.shields.activate()
                if shot_params := entity.railgun.activate(user_input=self.user_input):
                    self.world.add_entity(RailgunProjectile, shot_params)

    def _handle_non_game_user_input(self):
        """React to non-game related user input such as opening menus."""
        if self.user_input.respawn:
            self.user_input.respawn = False
            self.world.player.structure.hp = self.world.player.structure.max_hp
