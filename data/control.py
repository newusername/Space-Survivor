"""Updates the Model with passing time and user inputs."""
# todo for now the control is called by the GUI. Simply because I am too lazy to set up proper multithreading. Later it should use the run method.

import time

from attr import dataclass

from data.model import World


@dataclass
class UserInput:
    """Contains the current user inputs. The user's inputs will be read periodically during the update loop."""
    movement_width: float = 0
    movement_height: float = 0
    orientation: float = 0


class GameControl:
    def __init__(self, world: World, *, simulation_speed: float = 60):
        """
        :param world: The world to control.
        :param simulation_speed: update ticks per second
        """
        self.world = world
        self.simulation_speed = simulation_speed

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
        self._handle_user_input()
        # todo: update objects


    def _handle_user_input(self):
        """Handles the user input that effects the world."""
        self.world.player_entity.pose.relative_move(self.user_input.movement_width, self.user_input.movement_height)
        self.world.player_entity.pose.orientation = self.user_input.orientation
