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
