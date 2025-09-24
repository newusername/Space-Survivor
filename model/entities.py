"""Contains the objects."""
from typing import Self, Callable

import numpy as np
import arcade
from arcade import Sprite, SpriteList, PymunkPhysicsEngine

from control import math_utils
from control.physics import PhysicsEngine
from model.common import MATERIAL_WEIGHT, AsteroidSizes, Materials
from model.systems.common import System
from model.systems.engines import Engine
from model.systems.reactors import Reactor
from model.systems.sensors import Sensor
from model.systems.shields import Shields
from model.systems.structures import Structure, AsteroidStructure
from model.systems.weapons import Railgun
from settings import GameSettings


class WorldBorder(arcade.SpriteSolidColor):
    """Helps to create Sprite at the edge of the map that nothing can pass and signals to the player that there is
    nothing more to explore in this direction."""
    name: str = "World Border"
    collision_type_name: str = "world_border"

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
            WorldBorder(width + thickness, thickness, width / 2, -thickness / 2, wall_color),  # bottom
            WorldBorder(width + thickness, thickness, width / 2, height + thickness / 2, wall_color),  # top
            WorldBorder(thickness, height, -thickness / 2, height / 2, wall_color),  # left
            WorldBorder(thickness, height, width + thickness / 2, height / 2, wall_color),  # right
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
            "collision_type": WorldBorder.collision_type_name
        }


class PhysicalEntity(Sprite):
    """Base class for all interactive objects that should be rendered."""
    collision_type_name: str = "physical_entity"

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

        self.structure = Structure(entity=self)

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
            "collision_type": self.collision_type_name
        }

    @property
    def physics_engine(self) -> PhysicsEngine:
        """Return the physics engine associated with the entity the system belongs to."""
        return self.physics_engines[0]

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

    def destroy(self, add_entity_func: Callable):
        """Is called when the object is destroyed. Can spawn debris Sprites."""
        self.remove_from_sprite_lists()


class Asteroid(PhysicalEntity):
    """A simple peace of rock floating through space."""
    size_to_default_mass = {
        AsteroidSizes.tiny: 0.1,
        AsteroidSizes.small: 1.,
        AsteroidSizes.med: 3.,
        AsteroidSizes.big: 10.0
    }
    def __init__(self, size: AsteroidSizes = None, scale: float = None, *args, **kwargs):
        """Create a random sized asteroid if no sprite is given."""
        if size is None:
            size = np.random.choice(AsteroidSizes)
        self.size_class = size

        image_number = np.random.randint(1, (4 if size == AsteroidSizes.big else 2) + 1)
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

        mass = kwargs.pop("mass", None) or self.size_to_default_mass[size] * scale**2

        super().__init__(path_or_texture=texture, scale=scale, mass=mass, *args, **kwargs)
        self.structure = AsteroidStructure(entity=self, size=size, mass=mass, material=Materials.rock)

    def destroy(self, add_entity_func: Callable):
        """When asteroids are destroyed they break apart and spawn new smaller asteroids."""
        if self.size_class == AsteroidSizes.get_smallest_size():
            # cannot split in anything smaller
            return

        with self.physics_engine.set_current_entity(self):
            mass = self.mass  * 0.9
            velocity = self.physics_engine.get_translational_speed()
            rotational_speed = self.physics_engine.get_rotational_speed()
        self.remove_from_sprite_lists()

        # todo add some particle cloud effect to cover the split
        while mass >= self.size_to_default_mass[AsteroidSizes.tiny]:
            size = np.random.choice(AsteroidSizes.get_smaller_sizes(self.structure.size))
            new_asteroid = add_entity_func(
                Asteroid, {"size": size, "center_x": self.center_x, "center_y": self.center_y,
                           "translational_speed": velocity, "rotational_speed": rotational_speed,
                           "time_left_invulnerable": 1})
            mass -= new_asteroid.mass


class Combatant(PhysicalEntity):
    """Represents all objects that partake in battle."""
    def __init__(self, *args, **kwargs):
        """Create the most basic combatant. Use the upgrade() function to customize it.

        :param add_entity_func: A function that adds PhysicalEntities to a world.
        """
        super().__init__(*args, **kwargs)

        self.add_entity_func: Callable
        self.reactor = Reactor(entity=self)
        self.engine = Engine(entity=self)
        self.railgun = Railgun(entity=self)
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
        elif issubclass(system, Railgun):
            self.railgun = system_object
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

    def destroy(self, add_entity_func: Callable):
        """Players are currently not allowed to die, because the GUI needs a player at all times at the moment."""
        self.shields.activity_level = 0
        print("You died.")


class Projectile(PhysicalEntity):
    """Usually small objects accelerate with great speeds at other things with the intent to poke holes into them."""
    def __init__(self, damage_multiplier: float = 1, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.damage_multiplier = damage_multiplier
        self.structure.max_hp = 10_000


class RailgunProjectile(Projectile):
    pass