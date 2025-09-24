from enum import StrEnum, auto
from typing import Final, Any


def get_object_class_name(obj: Any) -> str:
    """Return the name of the class."""
    return type(obj).__name__


class Materials(StrEnum):
    rock = auto()
    steel = auto()


MATERIAL_WEIGHT: Final[dict] = {  # average weight of 1m³ of material in kg
    "rock": 2700.,
    "steel": 7800.
}


class AsteroidSizes(StrEnum):
    """
    Note 1: that the string values match the sprite assets.
    Note 2: the sizes are ordered from small to large.
    """
    tiny = "tiny"
    small = "small"
    med = "med"
    big = "big"

    @staticmethod
    def get_smallest_size() -> "AsteroidSizes":
        return [size for size in AsteroidSizes][0]

    @staticmethod
    def get_smaller_sizes(size: "AsteroidSizes") -> list["AsteroidSizes"]:
        """Returns a list of all Asteroid sizes smaller than the given size."""
        all_sizes = [size for size in AsteroidSizes]
        cutoff_index = all_sizes.index(size)
        return all_sizes[0:cutoff_index]
