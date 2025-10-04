"""This class handles the mapping of the controller inputs."""
from dataclasses import dataclass, field
from enum import StrEnum, auto


class InputType(StrEnum):
    """Defines if the input is analogue or digital"""
    button = auto()
    axis = auto()


@dataclass
class ControllerInput:
    """Defines the properties of a single input channel like a button or one direction if a stick."""
    type: InputType
    number: int
    is_inverted: bool = False
    default_value: float = 0


@dataclass
class ControllerMapping:
    """Defines the input the controller submits for every button."""
    l1: ControllerInput = field(default_factory=lambda: ControllerInput(type=InputType.button, number=4))
    l2: ControllerInput = field(default_factory=lambda: ControllerInput(type=InputType.axis, number=2,
                                                                        default_value=-1.))
    r1: ControllerInput = field(default_factory=lambda: ControllerInput(type=InputType.button, number=5))
    r2: ControllerInput = field(default_factory=lambda: ControllerInput(type=InputType.axis, number=5,
                                                                        default_value=-1.))

    left_stick_vertical: ControllerInput = field(
        default_factory=lambda: ControllerInput(type=InputType.axis, number=1, is_inverted=True))
    left_stick_horizontal: ControllerInput = field(
        default_factory=lambda: ControllerInput(type=InputType.axis, number=0))
    left_stick_button: ControllerInput = field(
        default_factory=lambda: ControllerInput(type=InputType.button, number=9))

    right_stick_vertical: ControllerInput = field(
        default_factory=lambda: ControllerInput(type=InputType.axis, number=4, is_inverted=True))
    right_stick_horizontal: ControllerInput = field(
        default_factory=lambda: ControllerInput(type=InputType.axis, number=3))
    right_stick_button: ControllerInput = field(
        default_factory=lambda: ControllerInput(type=InputType.button, number=10))

    button_up: ControllerInput = field(default_factory=lambda: ControllerInput(type=InputType.button, number=3))
    button_left: ControllerInput = field(default_factory=lambda: ControllerInput(type=InputType.button, number=2))
    button_right: ControllerInput = field(default_factory=lambda: ControllerInput(type=InputType.button, number=1))
    button_down: ControllerInput = field(default_factory=lambda: ControllerInput(type=InputType.button, number=0))

    button_start: ControllerInput = field(default_factory=lambda: ControllerInput(type=InputType.button, number=7))
