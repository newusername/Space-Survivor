from dataclasses import dataclass

from model.systems.common import System


@dataclass(kw_only=True)
class Shields(System):
    """Defines the shields protecting the entity"""
