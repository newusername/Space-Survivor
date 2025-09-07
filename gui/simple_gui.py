"""A simple GUI for testing using Arcade for rendering and Pygame for input."""
from dataclasses import dataclass

import arcade
import pygame
import numpy as np

from control.math_utils import get_point_angle
from model.worlds import World
from control.main import GameControl
from model.entities import PhysicalEntity, Player
from settings import GameSettings


@dataclass(kw_only=True)
class Settings:
    """Has the GUI settings."""
    screen_width: int = 800
    screen_height: int = 600
    zoom: float = 1.0


@dataclass(kw_only=True)
class EntityData:
    """GUI related additional information"""
    sprite: arcade.Sprite


class GUI(arcade.Window):
    """A simple GUI to represent the game state."""
    def __init__(self, world: World, control: GameControl):
        self.world = world
        self.control = control
        self.settings = Settings()
        super().__init__(self.settings.screen_width, self.settings.screen_height, "Arcade GUI")

        arcade.set_background_color(arcade.color.BLACK)
        self.camera = arcade.Camera2D()
        self.sprite_list = self.get_sprites()
        self.joystick = self.setup_joystick()

        self.update_times = list()  # stores the delta_time for the last 10 update cycles to compute fps

    def get_sprites(self) -> arcade.SpriteList:
        """Returns a list with all sprites and """
        sprite_list = arcade.SpriteList()
        for entity in self.world.entities:
            if entity.gui is None:
                sprite = self.get_sprite_for_entity(entity)
                entity.gui = EntityData(sprite=sprite)
            sprite_list.append(entity.gui.sprite)
        return sprite_list

    @staticmethod
    def get_sprite_for_entity(entity: PhysicalEntity) -> arcade.Sprite:
        """Loads/ creates the assets used for entities"""
        # todo using place holders right now
        if isinstance(entity, Player):
            return arcade.Sprite(":resources:images/space_shooter/playerLife1_orange.png", 0.5)
        else:
            return arcade.Sprite(":resources:images/space_shooter/meteorGrey_big1.png", 0.5)

    @staticmethod
    def setup_joystick():
        """Init pygame joystick."""
        pygame.init()
        pygame.joystick.init()
        if pygame.joystick.get_count() > 0:
            joystick = pygame.joystick.Joystick(0)
            joystick.init()
            return joystick

    def on_mouse_motion(self, mouse_x, mouse_y, dx, dy):
        """Happens approximately 60 times per second."""
        if self.joystick is None:
            player_x, player_y = self.world.player_entity.pose.position
            relative_x, relative_y = (mouse_x - player_x), (mouse_y - player_y)
            rotation = get_point_angle(relative_x, relative_y)
            self.control.user_input.orientation = rotation

    def on_key_press(self, key, modifiers):
        """ Called whenever the user presses a key. """
        match key:
            case arcade.key.LEFT | arcade.key.A:
                self.control.user_input.movement_width = -1
            case arcade.key.RIGHT | arcade.key.D:
                self.control.user_input.movement_width = 1
            case arcade.key.UP | arcade.key.W:
                self.control.user_input.movement_height = 1
            case arcade.key.DOWN | arcade.key.S:
                self.control.user_input.movement_height = -1
            case arcade.key.ESCAPE:
                self.close()

    def on_key_release(self, key, modifiers):
        """Called when the user releases a key. """
        match key:
            case arcade.key.LEFT | arcade.key.A:
                self.control.user_input.movement_width = 0
            case arcade.key.RIGHT | arcade.key.D:
                self.control.user_input.movement_width = 0
            case arcade.key.UP | arcade.key.W:
                self.control.user_input.movement_height = 0
            case arcade.key.DOWN | arcade.key.S:
                self.control.user_input.movement_height = 0

    def on_update(self, delta_time: float = None):
        if len(self.update_times) >= 10:
            self.update_times.pop(0)
        self.update_times.append(delta_time)

        self._handle_joystick_inputs()

        # Update the world (this is only temporary, because it is much easier to implement this way.)
        num_ticks_to_execute = 1  # todo make it dependant on the passed time and self.control.simulation_speed
        for _ in range(num_ticks_to_execute):
            self.control.simulation_tick()


        # update the position and orientation of sprites
        self.sprite_list = self.get_sprites()
        for entity, sprite in zip(self.world.entities, self.sprite_list):
            sprite.center_x, sprite.center_y = entity.pose.position
            sprite.angle = entity.pose.orientation

        # Update camera
        player_sprite: arcade.Sprite = self.world.player_entity.gui.sprite
        self.camera.position = (player_sprite.center_x, player_sprite.center_y)
        self.camera.zoom = self.settings.zoom

    def _handle_joystick_inputs(self):
        """Handle the Joystick inputs.

        There is no event method like for the mouse or keyboard for joysticks. Which is why this method is called during
        on_update().
        """
        if self.joystick:
            drift_thresh = GameSettings.min_drift_strength
            pygame.event.pump()
            # Move player (left stick)
            self.control.user_input.movement_width = self.suppress_activation(self.joystick.get_axis(0), drift_thresh)
            self.control.user_input.movement_height = -self.suppress_activation(self.joystick.get_axis(1), drift_thresh)
            r2 = self.joystick.get_axis(5) if self.joystick.get_numaxes() > 4 else self.joystick.get_button(8)
            self.control.user_input.burst = r2  # todo Check the axes version. Is it between -1 and 1? what is not pressed?
            if self.control.user_input.burst > 0.1:
                self.joystick.rumble(1, 0, 1000)  # todo the test controller seems to only support on and off and only uses one motor
            else:
                self.joystick.stop_rumble()
            self.control.user_input.stabilize = self.joystick.get_button(6)  # R1

            # Rotation (right stick)
            right_joystick_x = self.suppress_activation(self.joystick.get_axis(2), drift_thresh)
            right_joystick_y = -self.suppress_activation(self.joystick.get_axis(3), drift_thresh)  # inverted
            self.control.user_input.orientation = get_point_angle(right_joystick_x, right_joystick_y)
            self.control.user_input.orientation_strength = np.sqrt(right_joystick_x**2 + right_joystick_y**2)

            # Zoom
            if self.joystick.get_button(13):  # down
                self.settings.zoom = max(0.2, min(2.0, self.settings.zoom * 0.95))
            elif self.joystick.get_button(12):  # up
                self.settings.zoom = max(0.2, min(2.0, self.settings.zoom * 1.05))

    @staticmethod
    def suppress_activation(value: float, thresh: float):
        """Reduce the value to 0 if it is smaller than the thresh. Useful e.g. to handle stick drifts..."""
        if abs(value) >= thresh:
            return value
        else:
            return 0

    def on_draw(self):
        self.clear()
        self.camera.use()

        # Draw world background
        # todo load/ create some nice stars background + a bit of twinkle. Maybe even a bit of parallex effect?

        # Draw sprites
        self.sprite_list.draw()

        # Draw UI
        self.draw_energy_bar()

        # Draw temporary infos at the bottom
        pos = self.camera.bottom_left
        reactor = self.world.player_entity.reactor
        energy = f"{reactor.capacitors_storage / reactor.capacitors_limit:.2f}"
        arcade.draw_text(f"fps: {1 / np.mean(self.update_times):.2f} energy: {energy}",
                         pos[0] + 10, pos[1] + 10, arcade.color.WHITE, 14)

    def draw_energy_bar(self):
        # Calculate filled height
        energy_fraction = self.world.player_entity.reactor.capacitors_storage / self.world.player_entity.reactor.capacitors_limit

        # Interpolated color (green to red)
        red = int(255 * (1 - energy_fraction))
        green = int(255 * energy_fraction)
        color = (red, green, 0)

        # Draw the bar
        bar_width = 30
        max_bar_height = 200
        current_height = max_bar_height * energy_fraction
        x, y = self.camera.center_right
        x -= bar_width
        # Draw background (empty bar)
        arcade.draw_lbwh_rectangle_outline(x, y, bar_width, max_bar_height, arcade.color.BLACK, 2)

        # Draw filled bar (adjust y so it depletes from top to bottom)
        filled_y = y - (max_bar_height - current_height) / 2
        arcade.draw_lbwh_rectangle_filled(x, filled_y, bar_width, current_height, color)
