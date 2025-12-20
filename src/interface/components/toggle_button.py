from __future__ import annotations
import pygame as pg

from src.sprites import Sprite
from src.core.services import input_manager
from src.utils import Logger
from typing import Callable, override
from .component import UIComponent
from src.core.services import resource_manager

class ToggleButton(UIComponent):
    img_button: Sprite
    img_button_default: Sprite
    img_button_clicked: Sprite
    hitbox: pg.Rect
    on_click: Callable[[bool], None] | None
    state: bool

    def __init__(
        self,
        img_path: str, img_clicked_path:str,
        x: int, y: int, width: int, height: int, clicked: Callable[[bool], None] | None = None
    ):
        self.img_button_default = Sprite(img_path, (width, height))
        self.hitbox = pg.Rect(x, y, width, height)

        image = resource_manager.get_image(img_path)
        self.image = pg.transform.scale(image, (width, height))
        img_button_clicked = resource_manager.get_image(img_clicked_path)
        self.img_button_clicked = pg.transform.scale(img_button_clicked, (width, height))
        self.img_button = img_path
        self.clicked = clicked
        self.hitbox = pg.Rect(x, y, width, height)
        self.current_image = self.image
        self.state = False

    @override
    def update(self, dt: float) -> None:

        if self.hitbox.collidepoint(input_manager.mouse_pos) and input_manager.mouse_pressed(1):
            if self.state == True:
                self.state = False
                
            else:
                self.state = True

        if self.state:
            self.current_image = self.img_button_clicked
        
        else:
            self.current_image = self.image
            
        if self.clicked:
            self.clicked(self.state)

    @override
    def draw(self, screen: pg.Surface) -> None:
        screen.blit(self.current_image, self.hitbox)