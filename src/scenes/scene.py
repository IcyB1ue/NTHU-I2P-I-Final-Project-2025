from __future__ import annotations
import pygame as pg
from typing import Any

class Scene:
    def __init__(self) -> None:
        ...

    def enter(self, data: Any = None) -> None:
        """
        Called when entering the scene.
        
        Args:
            data: Optional data passed from the previous scene
        """
        ...

    def exit(self) -> None:
        ...

    def update(self, dt: float) -> None:
        ...

    def draw(self, screen: pg.Surface) -> None:
        ...