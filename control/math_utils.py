import math

import numpy as np


def rotate_vector_2d(vector: np.ndarray, angle_deg: float):
    """Rotate a 2D vector by a given angle.

    vector: numpy array-like of shape (2,), e.g. width x height
    angle_deg: angle in degrees, clockwise
    """
    angle_rad = -np.deg2rad(angle_deg)
    rot = np.array([
        [np.cos(angle_rad), -np.sin(angle_rad)],
        [np.sin(angle_rad),  np.cos(angle_rad)]
    ])
    return rot @ np.asarray(vector)


def vector_from_angle_magnitude(angle: float, magnitude: float) -> np.ndarray:
    """Create a vector from an angle and magnitude.

    :param angle: Angle to move towards in [0, 360) clockwise with 0 is up.
    :param magnitude: The strength of the impulse.
    """
    return rotate_vector_2d(np.array([0, magnitude]), angle)

def angle_magnitude_from_vector(vector: np.ndarray) -> tuple[float, float]:
    """Returns the angle and magnitude of a vector.

    :return angle: Angle to move towards in [0, 360) clockwise with 0 is up.
    :return magnitude: The strength of the impulse.
    """
    angle = get_point_angle(*vector)
    magnitude = float(np.linalg.norm(vector))
    return angle, magnitude

def get_point_angle(relative_x: float, relative_y: float) -> float:
    """Get the clockwise angle between the point [0, 1] (up) and the given point.

    :returns: a value in degrees [0, 360) clockwise with 0 is up.
    """
    return np.rad2deg(np.arctan2(relative_x, relative_y)) % 360

def limit_vector(vector: np.ndarray, max_magnitude: float) -> np.ndarray:
    """Shortens the magnitude of the vector to the max_magnitude if it is longer."""
    magnitude = np.linalg.norm(vector)
    if magnitude > max_magnitude:
        vector = vector / np.linalg.norm(vector) * max_magnitude
    return vector


def smallest_angle_difference(angle_1: float, angle_2: float) -> float:
    """Return the angular distance between two angles.

    :param angle_1: value in [0, 360] representing an angle in degrees
    :param angle_2: value in [0, 360] representing an angle in degrees
    :return: a value in [-180, 180) representing the angle in degrees to get from angle_1 to angle_2.
    """
    return (angle_2 - angle_1 + 180) % 360 - 180


def polygon_area(points: tuple[float, float]):
    """Compute area of polygon using the shoelace formula.
       Points must be in order (clockwise or counterclockwise)."""
    n = len(points)
    area = 0.0
    for i in range(n):
        x1, y1 = points[i]
        x2, y2 = points[(i + 1) % n]
        area += x1 * y2 - x2 * y1
    return abs(area) / 2


def sphere_volume_from_circle_area(area):
    """
    Compute the volume of a sphere given the area of a circle
    with the same diameter.

    Parameters:
        area (float): Area of the circle

    Returns:
        float: Volume of the sphere
    """
    return (4 / 3) * (area ** 1.5) / math.sqrt(math.pi)
