"""A simple GUI for testing using Arcade for rendering and Pygame for input."""
import pyglet
from pymunk import Vec2d

pyglet.options.dpi_scaling = "real"  # this disables display scaling


from dataclasses import dataclass, field, asdict
from typing import Optional

import arcade
from arcade import Sprite, LRBT, Rect
from arcade.types import Color
import pygame
import numpy as np
from pygame.joystick import JoystickType

from control.math_utils import get_point_angle
from gui.controller import ControllerMapping, ControllerInput, InputType
from model.entities import Combatant, RailgunProjectile, BlasterProjectile
from model.worlds import World
from control.main import GameControl
from settings import GameSettings


@dataclass(kw_only=True)
class WindowSettings:
    """Settings passed to the Window directly. Uses the parameter names expected by Arcade.

    Note: width and height are subject to the systems display scaling.
    """
    width: int = 1600
    height: int = 1200
    fullscreen: bool = False
    vsync: bool = True


@dataclass(kw_only=True)
class Settings:
    """Has the GUI settings."""
    window_settings: WindowSettings = field(default_factory=lambda: WindowSettings())
    zoom: float = 1.
    draw_hitbox: bool = False


class GUI(arcade.Window):
    """A simple GUI to represent the game state."""
    def __init__(self, world: World, control: GameControl):
        self.world = world
        self.control = control
        self.settings = Settings()
        self.controller = ControllerMapping()
        super().__init__(title="Arcade GUI", **asdict(self.settings.window_settings))

        self._load_shaders()

        self.camera = arcade.Camera2D()
        self.camera_view: Rect = self._get_camera_view()
        self.sprite_list = self.world.entities
        self.joystick = self.setup_joystick()
        self.keys = pyglet.window.key.KeyStateHandler()
        self.push_handlers(self.keys)

        arcade.enable_timings()

    def _enable_transparency(self):
        """ Activates transparency for shaders.

        Note: Rendering the arcade SpriteLists resets these settings."""
        self.ctx.disable(self.ctx.DEPTH_TEST)
        self.ctx.blend_func = (self.ctx.SRC_ALPHA, self.ctx.ONE_MINUS_SRC_ALPHA)
        self.ctx.enable(self.ctx.BLEND)

    def _load_shaders(self):
        """Load the shader files."""
        file_name = "gui/shader/star_nest.glsl"
        with open(file_name) as file:
            shader_source = file.read()
            self.background_shader = arcade.experimental.Shadertoy(size=self.get_size(), main_source=shader_source)

        file_name = "gui/shader/shield.glsl"
        with open(file_name) as file:
            shader_source = file.read()
            self.shield_shader = arcade.experimental.Shadertoy(size=self.get_size(), main_source=shader_source)
            self.shield_shader.program['color'] = arcade.color.ALLOY_ORANGE.normalized

        file_name = "gui/shader/glow_ball.glsl"
        with open(file_name) as file:
            shader_source = file.read()
            self.railgun_shader = arcade.experimental.Shadertoy(size=self.get_size(), main_source=shader_source)
            self.railgun_shader.program['color'] = arcade.color.GOLD_FUSION.normalized[0:3]

        file_name = "gui/shader/blaster.glsl"
        with open(file_name) as file:
            shader_source = file.read()
            self.blaster_shader = arcade.experimental.Shadertoy(size=self.get_size(), main_source=shader_source)
            self.blaster_shader.program['color'] = arcade.color.LIGHT_PINK.normalized[0:3]

    def _get_camera_view(self) -> Rect:
        """Return a rectangle that includes the area of the world currently in view."""
        return self.camera.projection.at_position(self.camera.position)

    def _sprite_in_view(self, sprite: Sprite) -> bool:
        """Return True if the sprite center is visible in the current camera view."""
        sprite_rect = LRBT(sprite.left, sprite.right, sprite.bottom, sprite.top)
        return self.camera_view.overlaps(sprite_rect)

    def m_to_pixels(self, size: float) -> float:
        """Converts meter to the corresponding number of pixels on the screen.

        1m = 1 pixel of a sprite at zoom = 1.
        """
        return self.camera.zoom * size

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

    def _handle_mouse_keyboard_inputs(self):
        """Use keyboard and mouse inputs.

        Note: Arcade prefers it if mouse/ keyboard inputs are handled via event handlers. See e.g.
            - on_mouse_motion
            - on_key_press
            ...
            However, this can be circumvented with pyglet.
        """
        if self.keys[pyglet.window.key.Q]:
            self.settings.zoom = max(0.2, min(2.0, self.settings.zoom * 1.03))
        if self.keys[pyglet.window.key.E]:
            self.settings.zoom = max(0.2, min(2.0, self.settings.zoom * 0.96))

        user_input = self.control.user_input
        user_input.stabilize = True if self.keys[pyglet.window.key.LCTRL] else False
        user_input.burst = 1 if self.keys[pyglet.window.key.LSHIFT] else 0

    def on_mouse_press(self, x, y, button, key_modifiers):
        """Called when the user presses a mouse button."""
        if button == arcade.MOUSE_BUTTON_LEFT:
            self.control.user_input.fire_rail_guns = True
        if button == arcade.MOUSE_BUTTON_RIGHT:
            self.control.user_input.fire_blasters = True

    def on_mouse_motion(self, x, y, dx, dy):
        """Event handler for mouse movements. Is called when the mouse moves over the window."""
        relative_position = Vec2d(x=x, y=y) - self.camera.project(self.control.world.player.position)
        orientation = get_point_angle(*relative_position)
        self.control.user_input.orientation = orientation
        self.control.user_input.orientation_strength = 1

    def on_update(self, delta_time: Optional[float] = None):
        """Notes:

        The sprites are automatically synced with the model by arcades Pymunk wrapper for the physics engine.
        """
        self._handle_player_inputs()

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
        self.camera_view: Rect = self._get_camera_view()

    def _handle_player_inputs(self):
        """Handle the players inputs."""
        if self.joystick:
            self._handle_joystick_inputs()
        else:
            self._handle_mouse_keyboard_inputs()

    def _handle_joystick_inputs(self):
        """Handle the Joystick inputs.

        There is no event method like for the mouse or keyboard for joysticks. Which is why this method is called during
        on_update().
        """
        if self.joystick:
            pygame.event.pump()

            # Move player (left stick)
            self.control.user_input.movement_width = self._get_axis_value(self.controller.left_stick_horizontal)
            self.control.user_input.movement_height = self._get_axis_value(self.controller.left_stick_vertical)

            # weapons
            self.control.user_input.fire_blasters = bool(self.joystick.get_button(self.controller.button_up.number))

            # Rotation (right stick)
            right_joystick_width = self._get_axis_value(self.controller.right_stick_horizontal)
            right_joystick_height = self._get_axis_value(self.controller.right_stick_vertical)
            self.control.user_input.orientation = get_point_angle(right_joystick_width, right_joystick_height)
            self.control.user_input.orientation_strength = np.sqrt(right_joystick_width ** 2 + right_joystick_height ** 2)

            # R/L buttons
            self.control.user_input.fire_rail_guns = bool(self.joystick.get_button(self.controller.l1.number))
            self.control.user_input.stabilize = bool(self.joystick.get_button(self.controller.r1.number))

            if self.controller.r2.type == InputType.button:
                self.control.user_input.burst = bool(self.joystick.get_button(self.controller.r2.number))
            elif self.controller.r2.type == InputType.axis:
                self.control.user_input.burst = self._get_axis_value(self.controller.r2)

            if self.control.user_input.burst > 0.1:  # todo: move this somewhere more appropriate
                self.joystick.rumble(1, 0, 1000)
            else:
                self.joystick.stop_rumble()

            # Zoom
            if self.joystick.get_button(self.controller.left_stick_button.number):  # down
                self.settings.zoom = max(0.2, min(2.0, self.settings.zoom * 0.95))
            if self.joystick.get_button(self.controller.right_stick_button.number):  # up
                self.settings.zoom = max(0.2, min(2.0, self.settings.zoom * 1.05))

    def _get_axis_value(self, controller_input: ControllerInput) -> float:
        """Get a value for an axis input."""
        value = self.joystick.get_axis(controller_input.number)
        if controller_input.is_inverted:
            value *= -1
        return self.suppress_activation(value, controller_input.default_value, GameSettings.min_drift_strength)

    @staticmethod
    def suppress_activation(value: float, default_value: float, thresh: float):
        """Check if the value differs more than the thresh from the default value. I not, it returns the default value.

        This is intended to be used to counter stick drifts.
        """
        if abs(value - default_value) >= thresh:
            return value
        else:
            return default_value

    def on_draw(self):
        self.clear()
        self.camera.use()

        # Draw world background
        mouse_pos = (0, 0)  # self.mouse["x"], self.mouse["y"]
        self.background_shader.render(time=self.time, mouse_position=mouse_pos)

        # draw shields
        self._enable_transparency()
        for sprite in self.sprite_list:
            if isinstance(sprite, Combatant) and sprite.shields.activity_level:
                if Settings.draw_hitbox:
                    color = np.array(self.shield_shader.program['color']) * 255
                    color[-1] = sprite.shields.activity_level * 255
                    arcade.draw_circle_outline(sprite.center_x, sprite.center_y, sprite.shields.shield_radius,
                                               color=tuple(color))
                    self._enable_transparency()
                self.shield_shader.program['pos_uv'] = self.camera_view.position_to_uv(sprite.position)
                self.shield_shader.program['radius'] = self.m_to_pixels(sprite.shields.shield_radius)
                self.shield_shader.program['time'] = self.time
                self.shield_shader.program['activity_level'] = sprite.shields.activity_level
                self.shield_shader.render()

        # draw bullets
        self._enable_transparency()
        for sprite in self.sprite_list:
            if isinstance(sprite, RailgunProjectile) and self._sprite_in_view(sprite):
                self.railgun_shader.program['pos_uv'] = self.camera_view.position_to_uv(sprite.position)
                self.railgun_shader.program['size'] = self.camera.zoom * sprite.radius
                self.railgun_shader.render()

        # draw blasters
        self._enable_transparency()
        for sprite in self.sprite_list:
            if isinstance(sprite, BlasterProjectile) and self._sprite_in_view(sprite):
                self.blaster_shader.program['pos_uv'] = self.camera_view.position_to_uv(sprite.position)
                self.blaster_shader.program['size'] = self.camera.zoom * sprite.radius
                self.blaster_shader.render()

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
    def draw_bar(left: float, bottom: float, bar_width: float, max_bar_height: float, color: Color,
                 fraction: float = 1.):
        """Adds a simple depleted bar to the GUI."""
        current_height = max_bar_height * fraction
        arcade.draw_lbwh_rectangle_outline(left, bottom, bar_width, max_bar_height, arcade.color.BLACK, 2)
        arcade.draw_lbwh_rectangle_filled(left, bottom, bar_width, current_height, color.rgb)

    def print_game_over(self):
        """Print the Game Over overlay."""
        x, y = self.camera.position
        # todo add like a grey transparent image all over the camera area
        # arcade.draw_text(f"Game Over!", x, y, arcade.color.WHITE, 200, anchor_x="center")
        arcade.draw_text(f"Press 'r' to respawn", x, y, arcade.color.WHITE, 60, anchor_x="center")
