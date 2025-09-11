"""Updates the Model with passing time and user inputs."""
# todo for now the control is called by the GUI. Simply because I am too lazy to set up proper multithreading. Later it should use the run method.

import time

from control.physics import InertiaDynamics
from control.user_input import UserInput
from model.entities import Combatant, Player, Asteroid
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
        self.world_dynamics = InertiaDynamics()

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
        self.world.world_update()
        for entity in self.world.entities:
            if isinstance(entity, Combatant):
                entity.reactor.activate()
                if entity is self.world.entities.player:
                    entity.engine.activate(self.user_input)  # noqa does not recognice the check for Combatant
                else:
                    pass  # todo implement logic to move NPCs

            entity.dynamics.update()  # update at the end, so that all effects during the tick are added to the dynamics

        for sprite1, sprite2 in self.world.entities.get_collisions():
            entity1 = sprite1.properties["entity"]
            entity2 = sprite2.properties["entity"]

            # we currently only care about collisions involving the player or asteroids with each other
            if ((isinstance(entity1, Player) or isinstance(entity2, Player)) or
                    (isinstance(entity1, Asteroid) and isinstance(entity2, Asteroid))):
                self.world_dynamics.collision(entity1.dynamics, 1, entity2.dynamics, 1, e=0.25)
                entity1.collision()
                entity2.collision()
                if isinstance(entity1, Player) or isinstance(entity2, Player):
                    self.gui_info.player_damage = True
