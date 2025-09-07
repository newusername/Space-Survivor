from dataclasses import dataclass

from model.systems.common import System


@dataclass(kw_only=True)
class WeaponSystems(System):
    """Defines the weapons of an entity"""
    name: str = "Weapons"

    def activate(self, *args, **kwargs):
        raise NotImplemented
