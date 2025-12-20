from __future__ import annotations
import pygame as pg
from typing import Optional, Callable, List, Dict
from .component import UIComponent
from src.core.services import input_manager
from src.utils import Logger


class ChatOverlay(UIComponent):
    """Lightweight chat UI similar to Minecraft: toggle with a key, type, press Enter to send."""
    is_open: bool
    _input_text: str
    _cursor_timer: float
    _cursor_visible: bool
    _just_opened: bool
    _send_callback: Callable[[str], bool] | None
    _get_messages: Callable[[int], list[dict]] | None
    _font_msg: pg.font.Font
    _font_input: pg.font.Font

    def __init__(
        self,
        send_callback: Callable[[str], bool] | None = None,
        get_messages: Callable[[int], list[dict]] | None = None,
        *,
        font_path: str = "assets/fonts/Minecraft.ttf"
    ) -> None:
        self.is_open = False
        self._input_text = ""
        self._cursor_timer = 0.0
        self._cursor_visible = True
        self._just_opened = False
        self._send_callback = send_callback
        self._get_messages = get_messages

        # Initialize fonts
        try:
            self._font_msg = pg.font.Font(font_path, 16)
            self._font_input = pg.font.Font(font_path, 18)
        except Exception:
            self._font_msg = pg.font.SysFont("arial", 16)
            self._font_input = pg.font.SysFont("arial", 18)

    def open(self) -> None:
        if not self.is_open:
            self.is_open = True
            self._cursor_timer = 0.0
            self._cursor_visible = True
            self._just_opened = True

    def close(self) -> None:
        self.is_open = False
        self._input_text = ""

    def _handle_typing(self) -> None:
        """Handle keyboard input for chat."""
        shift = input_manager.key_down(pg.K_LSHIFT) or input_manager.key_down(pg.K_RSHIFT)
        
        # Letters A-Z
        for k in range(pg.K_a, pg.K_z + 1):
            if input_manager.key_pressed(k):
                ch = chr(ord('a') + (k - pg.K_a))
                self._input_text += (ch.upper() if shift else ch)

        # Numbers 0-9
        number_chars = "0123456789"
        shift_number_chars = ")!@#$%^&*("
        for i, k in enumerate(range(pg.K_0, pg.K_9 + 1)):
            if input_manager.key_pressed(k):
                if shift:
                    self._input_text += shift_number_chars[i]
                else:
                    self._input_text += number_chars[i]

        # Space
        if input_manager.key_pressed(pg.K_SPACE):
            self._input_text += " "

        # Common punctuation
        if input_manager.key_pressed(pg.K_PERIOD):
            self._input_text += ">" if shift else "."
        if input_manager.key_pressed(pg.K_COMMA):
            self._input_text += "<" if shift else ","
        if input_manager.key_pressed(pg.K_SLASH):
            self._input_text += "?" if shift else "/"
        if input_manager.key_pressed(pg.K_SEMICOLON):
            self._input_text += ":" if shift else ";"
        if input_manager.key_pressed(pg.K_QUOTE):
            self._input_text += '"' if shift else "'"
        if input_manager.key_pressed(pg.K_MINUS):
            self._input_text += "_" if shift else "-"
        if input_manager.key_pressed(pg.K_EQUALS):
            self._input_text += "+" if shift else "="
        if input_manager.key_pressed(pg.K_EXCLAIM):
            self._input_text += "!"

        # Backspace
        if input_manager.key_pressed(pg.K_BACKSPACE):
            self._input_text = self._input_text[:-1]

        # Enter to send
        if input_manager.key_pressed(pg.K_RETURN) or input_manager.key_pressed(pg.K_KP_ENTER):
            txt = self._input_text.strip()
            if txt and self._send_callback:
                ok = False
                try:
                    ok = self._send_callback(txt)
                except Exception as e:
                    Logger.warning(f"Chat send error: {e}")
                    ok = False
                if ok:
                    self._input_text = ""

    def update(self, dt: float) -> None:
        if not self.is_open:
            return
        
        # Close on Escape
        if input_manager.key_pressed(pg.K_ESCAPE):
            self.close()
            return
        
        # Typing
        if self._just_opened:
            self._just_opened = False
        else:
            self._handle_typing()
        
        # Cursor blink
        self._cursor_timer += dt
        if self._cursor_timer >= 0.5:
            self._cursor_timer = 0.0
            self._cursor_visible = not self._cursor_visible

    def draw(self, screen: pg.Surface) -> None:
        # Always draw recent messages faintly, even when closed
        msgs = self._get_messages(8) if self._get_messages else []
        sw, sh = screen.get_size()
        x = 10
        y = sh - 140
        
        # Draw background for messages
        if msgs:
            container_w = max(300, int((sw - 20) * 0.5))
            msg_height = len(msgs) * 22 + 16
            bg = pg.Surface((container_w, msg_height), pg.SRCALPHA)
            bg.fill((0, 0, 0, 120 if self.is_open else 80))
            screen.blit(bg, (x, y))
            
            # Render last messages
            lines = list(msgs)[-8:]
            draw_y = y + 8
            for m in lines:
                sender = str(m.get("from", "???"))
                text = str(m.get("text", ""))
                # Render sender in different color
                sender_surf = self._font_msg.render(f"{sender}: ", True, (100, 200, 255))
                text_surf = self._font_msg.render(text, True, (255, 255, 255))
                screen.blit(sender_surf, (x + 10, draw_y))
                screen.blit(text_surf, (x + 10 + sender_surf.get_width(), draw_y))
                draw_y += 22
        
        # If not open, skip input field
        if not self.is_open:
            return
        
        # Input box
        box_h = 32
        box_w = max(300, int((sw - 20) * 0.5))
        box_y = sh - box_h - 10
        
        # Background box
        bg2 = pg.Surface((box_w, box_h), pg.SRCALPHA)
        bg2.fill((0, 0, 0, 180))
        screen.blit(bg2, (x, box_y))
        
        # Border
        pg.draw.rect(screen, (100, 100, 100), (x, box_y, box_w, box_h), 2)
        
        # Text
        txt = self._input_text
        text_surf = self._font_input.render(txt, True, (255, 255, 255))
        screen.blit(text_surf, (x + 8, box_y + 6))
        
        # Caret
        if self._cursor_visible:
            cx = x + 8 + text_surf.get_width() + 2
            cy = box_y + 6
            pg.draw.rect(screen, (255, 255, 255), pg.Rect(cx, cy, 2, box_h - 12))