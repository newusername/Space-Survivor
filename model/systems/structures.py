from dataclasses import dataclass

from model.systems.common import System


@dataclass(kw_only=True)
class Structure(System):
    """Defines the structure of an entity."""
    name: str = "Structure"

    def activate(self, *args, **kwargs):
        raise NotImplemented
