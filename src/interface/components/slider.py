from __future__ import annotations
import pygame as pg

from src.sprites import Sprite
from src.core.services import input_manager, resource_manager
from typing import Callable, override
from .component import UIComponent

class Slider(UIComponent):
    def __init__(
        self,
        img_bottom_path: str,
        img_top_path: str,
        img_slider_path: str,
        x: int, y: int, width: int, height: int,
        initial_value: float = 0.5,
        on_value_changed: Callable[[float], None] | None = None
    ):
        self.x, self.y = x, y
        self.width = width
        self.height = height

        # Load images
        self.bottom_img = pg.transform.scale(
            resource_manager.get_image(img_bottom_path), (width, height)
        )
        self.top_img = pg.transform.scale(
            resource_manager.get_image(img_top_path), (width, height)
        )
        self.slider_img = pg.transform.scale(
            resource_manager.get_image(img_slider_path), (height, height)
        )  # knob is square

        # Slider value in range [0.0, 1.0]
        self.value = max(0.0, min(1.0, initial_value))

        # Hitboxes
        self.track_rect = pg.Rect(x, y, width, height)
        self.knob_rect = pg.Rect(0, 0, height, height)
        self.update_knob_position()

        # Drag control
        self.dragging = False

        self.on_value_changed = on_value_changed

    # ----------------------------------------------------------

    def update_knob_position(self):
        """Position knob based on value."""
        knob_x = self.x + self.value * (self.width - self.height)
        self.knob_rect.topleft = (knob_x, self.y)

    # ----------------------------------------------------------

    @override
    def update(self, dt: float) -> None:
        mouse_pos = input_manager.mouse_pos

        # Start dragging
        if input_manager.mouse_pressed(1) and self.knob_rect.collidepoint(mouse_pos):
            self.dragging = True

        # Stop dragging
        if input_manager.mouse_released(1):
            self.dragging = False

        # While dragging → update slider value
        if self.dragging:
            rel_x = mouse_pos[0] - self.x
            rel_x = max(0, min(self.width - self.height, rel_x))
            new_value = rel_x / (self.width - self.height)

            if new_value != self.value:
                self.value = new_value
                self.update_knob_position()

                if self.on_value_changed:
                    self.on_value_changed(self.value)

    # ----------------------------------------------------------

    @override
    def draw(self, screen: pg.Surface) -> None:
        # Draw bottom bar
        screen.blit(self.bottom_img, self.track_rect)

        # Draw filled portion
        filled_width = int(self.value * self.width)
        if filled_width > 0:
            screen.blit(
                self.top_img.subsurface((0, 0, filled_width, self.height)),
                (self.x, self.y)
            )

        # Draw slider knob
        screen.blit(self.slider_img, self.knob_rect)
