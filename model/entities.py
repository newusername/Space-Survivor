"""Contains the objects."""
from typing import Self, Final

import numpy as np
import arcade
from arcade import Sprite, SpriteList, PymunkPhysicsEngine

from control import math_utils
from model.systems.common import System
from model.systems.engines import Engine
from model.systems.reactors import Reactor
from model.systems.sensors import Sensor
from model.systems.shields import Shields
from model.systems.structures import Structure
from model.systems.weapons import WeaponSystems
from settings import GameSettings


MATERIAL_WEIGHT: Final[dict] = {  # average weight of 1m³ of material in kg
    "rock": 2700.,
    "steel": 7800.
}


class PhysicalEntity(Sprite):
    """Base class for all interactive objects that should be rendered."""
    def __init__(self, mass: float | str = 1., rotation_inertia: float = None,
                 max_velocity: float = GameSettings.translation_speed_max,
                 elasticity: float = None, *args, **kwargs):
        """
        :param mass: The mass of the object in kg/m³
        :param rotation_inertia: If None, it is computed by the Physics Engine
        :param elasticity: todo Not quite sure what the default is set to when left None, lets test it out!
        """
        super().__init__(*args, **kwargs)
        self.mass = mass if isinstance(mass, float | int) else self.estimate_mass(mass, 1.)
        self.rotation_inertia = rotation_inertia
        self.friction: float = 0.2
        self.elasticity = elasticity
        self.body_type: int = PymunkPhysicsEngine.DYNAMIC
        self.damping: float | None = None
        self.gravity: tuple[float, float] | None = None
        self.max_velocity = max_velocity
        self.max_horizontal_velocity: int | None = None
        self.max_vertical_velocity: int | None = None
        self.radius: float = 0
        self.collision_type: str | None = type(self).__name__

    def estimate_mass(self, material: str | float, solidity_fraction: float) -> float:
        """ Very roughly estimates the weight of an object based on its size, material and density.

        :param material: one of the materials listed in the MATERIAL_WEIGHT dict or weight for the material in kg/m³
        :param solidity_fraction: float in [0, 1] indicating how solid the object is, aka if it is hollow. 1. means it
            is completely solid with no empty spaces within.
        """
        weight = MATERIAL_WEIGHT[material] if isinstance(material, str) else material
        area = math_utils.polygon_area(self.texture.hit_box_points)  # noqa
        volume = math_utils.sphere_volume_from_circle_area(area)
        return volume * weight * solidity_fraction


    def get_physics(self) -> dict:
        """Returns all parameters needed by the physics engine in a neat dictionary."""
        return {
            "mass": self.mass,
            "moment_of_inertia": self.rotation_inertia,
            "friction": self.friction,
            "elasticity": self.elasticity,
            "body_type": self.body_type,
            "damping": self.damping,
            "gravity": self.gravity,
            "max_velocity": self.max_velocity,
            "max_horizontal_velocity": self.max_horizontal_velocity,
            "max_vertical_velocity": self.max_vertical_velocity,
            "radius": self.radius,
            "collision_type": self.collision_type
        }

    @property
    def angle(self) -> float:
        """Get or set the rotation or the sprite.

        The value is in degrees and is clockwise.
        """
        return self._angle

    @angle.setter
    def angle(self, new_value: float) -> None:
        """Added functionality of limiting the nagle to [0, 360)"""
        new_value = new_value % 360
        if new_value == self._angle:
            return

        self._angle = new_value
        self._hit_box.angle = new_value

        for sprite_list in self.sprite_lists:
            sprite_list._update_angle(self)

        self.update_spatial_hash()

    def destroy(self):
        """Is called when the object is destroyed."""
        self.remove_from_sprite_lists()


class WorldBorder:
    """Helps to create Sprite at the edge of the map that nothing can pass and signals to the player that there is
    nothing more to explore in this direction."""
    name: str = "WorldBorder"
    @classmethod
    def create_world_border(cls, world_size: tuple[int, int], wall_color = arcade.color.GRAY) -> SpriteList:
        """Create boxes that frame the entire simulated world. Currently, this is just 4 colored boxes.

        :param world_size: The size of the entire simulated world.
        :param wall_color: The color of the border.
        """
        width, height = world_size
        thickness = 10
        walls = arcade.SpriteList()
        walls.extend([
            arcade.SpriteSolidColor(width + thickness, thickness, width / 2, -thickness / 2, wall_color),  # bottom
            arcade.SpriteSolidColor(width + thickness, thickness, width / 2, height + thickness / 2, wall_color),  # top
            arcade.SpriteSolidColor(thickness, height, -thickness / 2, height / 2, wall_color),  # left
            arcade.SpriteSolidColor(thickness, height, width + thickness / 2, height / 2, wall_color),  # right
        ])
        return walls

    @staticmethod
    def get_physics() -> dict:
        """Returns all parameters needed by the physics engine in a neat dictionary."""
        return {
            "mass": 1,
            "moment_of_inertia": PymunkPhysicsEngine.MOMENT_INF,
            "friction": 0,
            "elasticity": 0,
            "body_type": PymunkPhysicsEngine.STATIC,
            "damping": None,
            "gravity": None,
            "max_velocity": None,
            "max_horizontal_velocity": None,
            "max_vertical_velocity": None,
            "radius": 0,
            "collision_type": "WorldBorder"
        }


class Asteroid(PhysicalEntity):
    """A simple peace of rock floating through space."""
    size_to_default_mass = {
        "tiny": 0.1,
        "small": 1.,
        "med": 3.,
        "big": 10.0
    }
    def __init__(self, size: str = "random", scale: float = None, *args, **kwargs):
        """Create a random sized asteroid if no sprite is given."""
        if size == "random":
            size = np.random.choice(["tiny", "small", "med", "big"])
        image_number = np.random.randint(1, (4 if size == "large" else 2) + 1)
        texture = arcade.load_texture(f":resources:images/space_shooter/meteorGrey_{size}{image_number}.png",
                                      hit_box_algorithm=arcade.hitbox.algo_detailed)
        scale = scale or np.random.random() + 0.5 # todo scale width and height independently. But that somehow messes up Pymunk collision detection
        if np.random.random() < 0.5:
            texture = texture.flip_diagonally()
        if np.random.random() < 0.5:
            texture = texture.flip_vertically()
        if np.random.random() < 0.5:
            texture = texture.flip_left_right()
        if np.random.random() < 0.5:
            texture = texture.flip_horizontally()
        if np.random.random() < 0.5:
            texture = texture.flip_top_bottom()

        mass = self.size_to_default_mass[size] * scale**2

        super().__init__(path_or_texture=texture, scale=scale, mass=mass, *args, **kwargs)


class Combatant(PhysicalEntity):
    """Represents all objects that partake in battle."""
    def __init__(self, *args, **kwargs):
        """Create the most basic combatant. Use the upgrade() function to customize it."""
        super().__init__(*args, **kwargs)
        self.reactor = Reactor(entity=self)
        self.engine = Engine(entity=self)
        self.structure = Structure(entity=self)
        self.weapons = WeaponSystems(entity=self)
        self.sensor = Sensor(entity=self)
        self.shields = Shields(entity=self)

    def upgrade(self, system: type[System], system_parameter: dict = None) -> Self:
        """Replaces an old system with a new one."""
        system_parameter = system_parameter or {}
        system_object = system(entity=self, **system_parameter)
        if issubclass(system, Reactor):
            self.reactor = system_object
        elif issubclass(system, Engine):
            self.engine = system_object
        elif issubclass(system, Structure):
            self.structure = system_object
        elif issubclass(system, WeaponSystems):
            self.weapons = system_object
        elif issubclass(system, Sensor):
            self.sensor = system_object
        elif issubclass(system, Shields):
            self.shields = system_object
        else:
            raise ValueError(f"Unknown System class {type(system)}.")

        return self


class Player(Combatant):
    """Represents the player's avatar in the world."""
    def __init__(self, name: str = "Player", *args, **kwargs):
        texture = arcade.load_texture(":resources:images/space_shooter/playerShip1_blue.png",
                                      hit_box_algorithm=arcade.hitbox.algo_detailed)
        super().__init__(path_or_texture=texture, *args, **kwargs)
        self.player_name = name

    def destroy(self):
        """Players are currently not allowed to die, because the GUI needs a player at all times at the moment."""
        print("You died.")
