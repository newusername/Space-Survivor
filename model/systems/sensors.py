from dataclasses import dataclass

from model.systems.common import System


@dataclass(kw_only=True)
class Sensor(System):
    """Defines an entities capabilities to detect other entities."""
    name: str = "Sensor"

    def activate(self, *args, **kwargs):
        raise NotImplemented
