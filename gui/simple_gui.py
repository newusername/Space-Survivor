"""A simple GUI for testing using Arcade for rendering and Pygame for input."""
from dataclasses import dataclass
from typing import Optional

import arcade
import pygame
import numpy as np
from pygame.joystick import JoystickType

from control.math_utils import get_point_angle
from model.entities import Combatant
from model.worlds import World
from control.main import GameControl
from settings import GameSettings


@dataclass(kw_only=True)
class Settings:
    """Has the GUI settings."""
    screen_width: int = 800
    screen_height: int = 600
    zoom: float = 0.8
    draw_hitbox: bool = False


class GUI(arcade.Window):
    """A simple GUI to represent the game state."""
    def __init__(self, world: World, control: GameControl):
        self.world = world
        self.control = control
        self.settings = Settings()
        super().__init__(self.settings.screen_width, self.settings.screen_height, "Arcade GUI")

        self._load_shaders()

        self.camera = arcade.Camera2D()
        self.sprite_list = self.world.entities
        self.joystick = self.setup_joystick()

        arcade.enable_timings()

    def _load_shaders(self):
        """Load the shader files."""
        file_name = "gui/shader/star_nest.glsl"
        with open(file_name) as file:
            shader_source = file.read()
            self.background_shader = arcade.experimental.Shadertoy(size=self.get_size(), main_source=shader_source)

        # file_name = "gui/shader/shield.glsl"  # todo the alpha is not mixed correctly, so can't use this right now
        # with open(file_name) as file:
        #     shader_source = file.read()
        #     self.shield_shader = arcade.experimental.Shadertoy(size=self.get_size(), main_source=shader_source)
        #     self.shield_shader.program['color'] = arcade.color.ALLOY_ORANGE.normalized

    @staticmethod
    def setup_joystick() -> Optional[JoystickType]:
        """Init pygame joystick."""
        pygame.init()
        pygame.joystick.init()
        if pygame.joystick.get_count() > 0:
            joystick = pygame.joystick.Joystick(0)
            joystick.init()
            return joystick
        return None

    def on_key_press(self, key, modifiers):
        """ Called whenever the user presses a key.

        Note: steering only works when no joystick is active, as that will override the keyboard input.
        """
        match key:
            case arcade.key.LEFT | arcade.key.A:
                self.control.user_input.movement_width = -1
            case arcade.key.RIGHT | arcade.key.D:
                self.control.user_input.movement_width = 1
            case arcade.key.UP | arcade.key.W:
                self.control.user_input.movement_height = 1
            case arcade.key.DOWN | arcade.key.S:
                self.control.user_input.movement_height = -1
            case arcade.key.Q:
                self.control.user_input.orientation = (self.world.player.angle - 179) % 360
                self.control.user_input.orientation_strength = 1
            case arcade.key.E:
                self.control.user_input.orientation = (self.world.player.angle + 179) % 360
                self.control.user_input.orientation_strength = 1
            case arcade.key.ESCAPE:
                self.close()
            case arcade.key.R:
                self.control.user_input.respawn = True
            case arcade.key.H:
                Settings.draw_hitbox = not Settings.draw_hitbox

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
            case arcade.key.Q:
                self.control.user_input.orientation = 0
                self.control.user_input.orientation_strength = 0
            case arcade.key.E:
                self.control.user_input.orientation = 0
                self.control.user_input.orientation_strength = 0

    def on_update(self, delta_time: float = None):
        """Notes:

        The sprites are automatically synced with the model by arcades Pymunk wrapper for the physics engine.
        """
        self._handle_joystick_inputs()

        # Update the world (this is only temporary, because it is much easier to implement this way.)
        num_ticks_to_execute = 1
        for _ in range(num_ticks_to_execute):
            self.control.simulation_tick()

        # handle other events
        if self.control.gui_info.player_damage:
            self.joystick.rumble(1, 0, 1000)
            self.control.gui_info.player_damage = False

        # Update camera
        player_sprite: arcade.Sprite = self.world.player
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
        mouse_pos = (0, 0)  # self.mouse["x"], self.mouse["y"]
        self.background_shader.render(time=self.time, mouse_position=mouse_pos)

        # draw shields
        for sprite in self.sprite_list:
            if isinstance(sprite, Combatant) and sprite.shields.activity_level:
                color = arcade.color.LIGHT_BLUE
                # alpha = (abs(np.sin(self.time * 0.8)) * 127) + 127
                alpha = sprite.shields.activity_level * 255
                arcade.draw_circle_filled(sprite.center_x, sprite.center_y, sprite.shields.shield_radius,
                                          color=(*color.rgb, alpha))
                # self.shield_shader.program['center_uv'] = (0.5, 0.5)
                # self.shield_shader.program['radius'] = 0.1  # sprite.shields.shield_radius # todo how do I normalize this? It depends on the zoom
                # self.shield_shader.program['time'] = self.time
                # self.shield_shader.render()

        # Draw sprites
        self.sprite_list.draw()
        if Settings.draw_hitbox:
            for sprite in self.sprite_list:
                sprite.draw_hit_box(color=arcade.color.LIME_GREEN, line_thickness=2)

        # Draw world borders
        self.world.walls.draw()

        # Draw UI
        self.draw_energy_bar()
        self.draw_hp_bar()
        if self.world.player.structure.hp == 0:
            self.print_game_over()

        # Draw temporary infos at the bottom
        pos = self.camera.bottom_left
        player = self.world.player
        arcade.draw_text(f"fps: {arcade.get_fps(60):.2f}, #entities: {len(self.sprite_list)}, "
                         f"Pose(x={player.center_x:.1f}, y={player.center_y:.1f}, orientation={player.angle:.1f}°)",
                         pos[0] + 10, pos[1] + 10, arcade.color.WHITE, 14)

    def draw_energy_bar(self):
        """Show the current power level."""
        energy_fraction = self.world.player.reactor.capacitors_storage / self.world.player.reactor.capacitors_limit
        bar_width = 30
        max_bar_height = 200
        x, y = self.camera.center_right
        x -= bar_width
        self.draw_bar(x, y, bar_width, max_bar_height, arcade.color.YELLOW, energy_fraction)

    def draw_hp_bar(self):
        """Show the current hp level."""
        energy_fraction = self.world.player.structure.hp / self.world.player.structure.max_hp
        bar_width = 30
        max_bar_height = 200
        x, y = self.camera.center_right
        x -= bar_width * 2
        self.draw_bar(x, y, bar_width, max_bar_height, arcade.color.GREEN, energy_fraction)

    @staticmethod
    def draw_bar(left: float, bottom: float, bar_width: float, max_bar_height: float, color: tuple[int, int, int],
                 fraction: float = 1.):
        """Adds a simple depleted bar to the GUI."""
        current_height = max_bar_height * fraction
        arcade.draw_lbwh_rectangle_outline(left, bottom, bar_width, max_bar_height, arcade.color.BLACK, 2)
        arcade.draw_lbwh_rectangle_filled(left, bottom, bar_width, current_height, color)

    def print_game_over(self):
        """Print the Game Over overlay."""
        x, y = self.camera.position
        # todo add like a grey transparent image all over the camera area
        # arcade.draw_text(f"Game Over!", x, y, arcade.color.WHITE, 200, anchor_x="center")
        arcade.draw_text(f"Press 'r' to respawn", x, y, arcade.color.WHITE, 60, anchor_x="center")