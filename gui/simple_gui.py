"""A simple GUI for testing using Arcade for rendering and Pygame for input."""
from dataclasses import dataclass

import arcade
import pygame
import numpy as np
from pyglet.event import EVENT_HANDLE_STATE

from data.model import World
from data.control import GameControl
from data.entities import PhysicalEntity, Player


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
        self.joystick = self.setup_joystick()  # todo currently requires a Joystick.

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
        if isinstance(entity, Player):
            return arcade.SpriteSolidColor(60, 30, color=arcade.color.WHITE)  # todo placeholder
        else:
            return arcade.SpriteSolidColor(40, 40, color=arcade.color.RED)  # todo placeholder

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
            rotation = self._relative_position_to_angle(relative_x, relative_y)
            self.control.user_input.orientation = rotation

    @staticmethod
    def _relative_position_to_angle(relative_x: float, relative_y: float) -> float:
        """Get a point relative to another and return the angle to it.

        :returns: a value in degrees [0, 360) clockwise with 0 is up.
        """
        if relative_y == 0:  # either looking perfectly left or right
            rotation = 270 if relative_x < 0 else 90
        else:
            rotation = np.rad2deg(np.arctan2(relative_x, relative_y))
        return rotation

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

        # Update the world (this is only temporary, because it is much easier to implement this way.)
        num_ticks_to_execute = 1  # todo make it dependant on the passed time and self.control.simulation_speed
        for _ in range(num_ticks_to_execute):
            self.control.simulation_tick()

        # Poll pygame events
        pygame.event.pump()
        if self.joystick:
            # Move player
            self.control.user_input.movement_width = self.joystick.get_axis(0)  # left stick X
            self.control.user_input.movement_height = -self.joystick.get_axis(1)  # left stick Y (invert)
            right_joystick_x = self.joystick.get_axis(2)
            right_joystick_y = -self.joystick.get_axis(3)  # inverted
            if abs(right_joystick_x) > 0.3 or abs(right_joystick_y) > 0.3:  # todo might be a bit high, but my test controller has a drift XD
                # don't update if there is no input or only a small stick drift
                self.control.user_input.orientation = self._relative_position_to_angle(right_joystick_x, right_joystick_y)

            # Zoom with triggers
            # zoom_change = (self.joystick.get_axis(5)) * 0.01
            # print(self.joystick.get_axis(5), self.joystick.get_axis(4))
            # self.settings.zoom = max(0.2, min(2.0, self.settings.zoom + zoom_change))

        # update the position and orientation of sprites
        self.sprite_list = self.get_sprites()
        for entity, sprite in zip(self.world.entities, self.sprite_list):
            sprite.center_x, sprite.center_y = entity.pose.position
            sprite.angle = entity.pose.orientation

        # Update camera
        player_sprite: arcade.Sprite = self.world.player_entity.gui.sprite
        self.camera.position = (player_sprite.center_x, player_sprite.center_y)
        self.camera.zoom = self.settings.zoom

    def on_draw(self):
        self.clear()
        self.camera.use()

        # Draw world background
        # todo load/ create some nice stars background + a bit of twinkle. Maybe even a bit of parallex effect?
        # arcade.draw_lbwh_rectangle_filled(0, 0, *self.world.size, arcade.color.DARK_BLUE_GRAY)

        # Draw sprites
        self.sprite_list.draw()

        # Draw UI
        arcade.draw_text(f"fps: {1 / np.mean(self.update_times):.2f}", 10, 10, arcade.color.WHITE, 14)
