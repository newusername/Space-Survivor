"""Updates the Model with passing time and user inputs."""
# todo for now the control is called by the GUI. Simply because I am too lazy to set up proper multithreading. Later it should use the run method.

import time

from control.user_input import UserInput
from model.entities import Combatant
from model.worlds import World
from settings import GameSettings


class GameControl:
    def __init__(self, world: World):
        """
        :param world: The world to control.
        """
        self.world = world
        self.simulation_speed = GameSettings.simulation_speed

        self.user_input = UserInput()
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
        for entity in self.world.entities:
            if isinstance(entity, Combatant):
                entity.reactor.activate()
                if entity is self.world.player_entity:
                    entity.engine.activate(self.user_input)
                else:
                    pass  # todo implement logic to move NPCs

            entity.dynamics.update()  # update at the end, so that all effects during the tick are added to the dynamics
