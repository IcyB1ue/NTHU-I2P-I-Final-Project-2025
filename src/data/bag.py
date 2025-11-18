import pygame as pg
import json
from src.utils import GameSettings
from src.utils.definition import Monster, Item
from src.sprites import Sprite
from src.interface.components.button import Button
from src.core.services import input_manager


class Bag:
    _monsters_data: list[Monster]
    _items_data: list[Item]

    def __init__(self, monsters_data: list[Monster] | None = None, items_data: list[Item] | None = None):
        self._monsters_data = monsters_data if monsters_data else []
        self._items_data = items_data if items_data else []
        self.overlay = Sprite("UI/raw/UI_Flat_Frame03a.png", (750, 625))
        self.overlay.rect.center = (GameSettings.SCREEN_WIDTH // 2, GameSettings.SCREEN_HEIGHT // 2)
        self.show = False

        px, py = GameSettings.SCREEN_WIDTH // 2, GameSettings.SCREEN_HEIGHT * 3 // 4
        self.back_button = Button(
            "UI/button_back.png", "UI/button_back_hover.png",
            px + 400, py - 500, 75, 75,
            lambda: self.close()
        )

        self.darken = pg.Surface((GameSettings.SCREEN_WIDTH,GameSettings.SCREEN_HEIGHT))
        self.darken.fill("Black")
        self.darken.set_alpha(128)
        self.darken_rect = self.darken.get_rect()

    def open(self):
        input_manager.reset()
        self.show = True

    def close(self):
        input_manager.reset()
        self.show = False

    def update(self, dt: float):
        if self.show:
            self.back_button.update(dt)

    def draw(self, screen: pg.Surface):
        if self.show:
            screen.blit(self.darken, self.darken_rect)
            self.overlay.draw(screen)
        if self.show:
            self.back_button.draw(screen)

    def to_dict(self) -> dict[str, object]:
        return {
            "monsters": list(self._monsters_data),
            "items": list(self._items_data)
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "Bag":
        monsters = data.get("monsters") or []
        items = data.get("items") or []
        bag = cls(monsters, items)
        return bag