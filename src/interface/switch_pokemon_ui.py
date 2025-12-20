import pygame as pg
from typing import Callable, Any

from src.utils import GameSettings, Logger
from src.utils.definition import Monster
from src.core.services import input_manager
from src.sprites import Sprite


# Element type colors for display
ELEMENT_COLORS = {
    "Normal": (168, 168, 120),
    "Fire": (240, 128, 48),
    "Water": (104, 144, 240),
    "Electric": (248, 208, 48),
    "Grass": (120, 200, 80),
    "Ice": (152, 216, 216),
    "Fighting": (192, 48, 40),
    "Poison": (160, 64, 160),
    "Ground": (224, 192, 104),
    "Flying": (168, 144, 240),
    "Psychic": (248, 88, 136),
    "Bug": (168, 184, 32),
    "Rock": (184, 160, 56),
    "Ghost": (112, 88, 152),
    "Dragon": (112, 56, 248),
}


class PokemonSlot:
    """A slot displaying a Pokemon that can be selected."""
    
    def __init__(self, x: int, y: int, width: int, height: int, monster: Monster | None, 
                 is_current: bool, callback: Callable[[Monster], None]):
        self.rect = pg.Rect(x, y, width, height)
        self.monster = monster
        self.is_current = is_current
        self.callback = callback
        self.hovered = False
        self.sprite = None
        self.sprite_darkened = None
        
        # Load sprite if monster exists
        if monster:
            self._load_sprite()
    
    def _load_sprite(self):
        """Load the Pokemon sprite."""
        if not self.monster:
            return
            
        sprite_path = self.monster.get("sprite") or self.monster.get("sprite_path")
        if sprite_path:
            try:
                # Use the game's Sprite class which handles paths correctly
                sprite_obj = Sprite(sprite_path, (64, 64))
                self.sprite = sprite_obj.image
                
                # Create darkened version for fainted Pokemon
                self.sprite_darkened = self.sprite.copy()
                dark_surface = pg.Surface(self.sprite_darkened.get_size(), pg.SRCALPHA)
                dark_surface.fill((0, 0, 0, 150))
                self.sprite_darkened.blit(dark_surface, (0, 0), special_flags=pg.BLEND_RGBA_MULT)
                # Add a dark overlay
                dark_overlay = pg.Surface(self.sprite_darkened.get_size(), pg.SRCALPHA)
                dark_overlay.fill((50, 50, 50, 200))
                self.sprite_darkened.blit(dark_overlay, (0, 0), special_flags=pg.BLEND_RGBA_MIN)
            except Exception as e:
                Logger.error(f"Failed to load Pokemon sprite: {e}")
                self.sprite = None
                self.sprite_darkened = None
    
    def is_alive(self) -> bool:
        """Check if this Pokemon is alive."""
        if not self.monster:
            return False
        return self.monster.get("hp", 0) > 0
    
    def is_selectable(self) -> bool:
        """Check if this slot can be selected."""
        return self.monster is not None and self.is_alive() and not self.is_current
    
    def update(self, dt: float):
        """Update slot state."""
        try:
            mouse_pos = input_manager.mouse_pos
            self.hovered = self.rect.collidepoint(mouse_pos) and self.is_selectable()
            
            if self.hovered and input_manager.mouse_pressed(1):
                if self.monster and self.is_selectable():
                    self.callback(self.monster)
        except Exception as e:
            Logger.error(f"Error updating PokemonSlot: {e}")
    
    def draw(self, screen: pg.Surface):
        """Draw the Pokemon slot."""
        if not self.monster:
            return
        
        is_alive = self.is_alive()
        is_selectable = self.is_selectable()
        
        # Background color
        if self.is_current:
            bg_color = (100, 100, 180)  # Blue for current
        elif not is_alive:
            bg_color = (60, 60, 60)  # Dark gray for fainted
        elif self.hovered:
            bg_color = (100, 150, 100)  # Light green for hover
        else:
            bg_color = (80, 80, 80)  # Normal gray
        
        # Draw background
        pg.draw.rect(screen, bg_color, self.rect, border_radius=10)
        pg.draw.rect(screen, (40, 40, 40), self.rect, 3, border_radius=10)
        
        # Draw sprite
        sprite_x = self.rect.x + 10
        sprite_y = self.rect.y + (self.rect.height - 64) // 2
        
        if is_alive and self.sprite:
            screen.blit(self.sprite, (sprite_x, sprite_y))
        elif not is_alive and self.sprite_darkened:
            screen.blit(self.sprite_darkened, (sprite_x, sprite_y))
        elif self.sprite:
            screen.blit(self.sprite, (sprite_x, sprite_y))
        
        # Draw Pokemon info
        info_x = sprite_x + 74
        
        # Name
        font = pg.font.Font(None, 24)
        name_color = (255, 255, 255) if is_alive else (150, 150, 150)
        name_text = font.render(self.monster.get("name", "???"), True, name_color)
        screen.blit(name_text, (info_x, self.rect.y + 10))
        
        # Level
        level_font = pg.font.Font(None, 20)
        level_color = (200, 200, 200) if is_alive else (120, 120, 120)
        level_text = level_font.render(f"Lv. {self.monster.get('level', 1)}", True, level_color)
        screen.blit(level_text, (info_x, self.rect.y + 32))
        
        # Element type
        element = self.monster.get("element", "Normal")
        element_color = ELEMENT_COLORS.get(element, (128, 128, 128))
        if not is_alive:
            element_color = tuple(c // 2 for c in element_color)
        element_text = level_font.render(element, True, element_color)
        screen.blit(element_text, (info_x + 60, self.rect.y + 32))
        
        # HP Bar
        hp = self.monster.get("hp", 0)
        max_hp = self.monster.get("max_hp", 1)
        hp_bar_x = info_x
        hp_bar_y = self.rect.y + 52
        hp_bar_width = 120
        hp_bar_height = 12
        
        # HP bar background
        pg.draw.rect(screen, (40, 40, 40), (hp_bar_x, hp_bar_y, hp_bar_width, hp_bar_height))
        
        # HP bar fill
        if max_hp > 0:
            hp_percentage = hp / max_hp
            fill_width = int(hp_bar_width * hp_percentage)
            
            if hp_percentage > 0.5:
                hp_color = (0, 200, 0)
            elif hp_percentage > 0.25:
                hp_color = (200, 200, 0)
            else:
                hp_color = (200, 0, 0)
            
            if not is_alive:
                hp_color = (100, 0, 0)
            
            if fill_width > 0:
                pg.draw.rect(screen, hp_color, (hp_bar_x, hp_bar_y, fill_width, hp_bar_height))
        
        # HP text
        hp_text_font = pg.font.Font(None, 16)
        hp_text_color = (255, 255, 255) if is_alive else (150, 150, 150)
        hp_text = hp_text_font.render(f"{hp}/{max_hp}", True, hp_text_color)
        hp_text_rect = hp_text.get_rect(center=(hp_bar_x + hp_bar_width // 2, hp_bar_y + hp_bar_height // 2))
        screen.blit(hp_text, hp_text_rect)
        
        # Draw "FAINTED" label for dead Pokemon (takes priority over IN BATTLE)
        if not is_alive:
            fainted_font = pg.font.Font(None, 20)
            fainted_text = fainted_font.render("FAINTED", True, (255, 80, 80))
            fainted_rect = fainted_text.get_rect(center=(self.rect.x + self.rect.width - 50, self.rect.y + 20))
            screen.blit(fainted_text, fainted_rect)
        # Draw "CURRENT" label for current Pokemon (only if alive)
        elif self.is_current:
            current_font = pg.font.Font(None, 20)
            current_text = current_font.render("IN BATTLE", True, (100, 200, 255))
            current_rect = current_text.get_rect(center=(self.rect.x + self.rect.width - 50, self.rect.y + 20))
            screen.blit(current_text, current_rect)


class SwitchPokemonUI:
    """Overlay UI for switching Pokemon during battle."""
    
    def __init__(self, on_switch: Callable[[Monster], None] | None = None,
                 on_cancel: Callable[[], None] | None = None):
        self.overlay_show = False
        self.on_switch = on_switch
        self.on_cancel = on_cancel
        self.force_switch = False  # When True, cancel button is hidden (Pokemon fainted)
        
        self.monsters: list[Monster] = []
        self.current_monster: Monster | None = None
        self.slots: list[PokemonSlot] = []
        
        # UI dimensions
        self.panel_width = 450
        self.panel_height = 400
        self.panel_x = (GameSettings.SCREEN_WIDTH - self.panel_width) // 2
        self.panel_y = (GameSettings.SCREEN_HEIGHT - self.panel_height) // 2
        
        # Cancel button
        self.cancel_rect = pg.Rect(
            self.panel_x + self.panel_width - 100,
            self.panel_y + self.panel_height - 45,
            80, 35
        )
        self.cancel_hovered = False
    
    def open(self, monsters: list[Monster], current_monster: Monster | None = None, 
             force_switch: bool = False):
        """Open the switch Pokemon overlay."""
        if not monsters:
            Logger.warning("Switch UI opened with empty monster list!")
            return
            
        self.overlay_show = True
        self.monsters = monsters
        self.current_monster = current_monster
        self.force_switch = force_switch
        
        try:
            self._create_slots()
        except Exception as e:
            Logger.error(f"Error creating slots: {e}")
            self.overlay_show = False
            return
        
        # Reset input to prevent accidental clicks
        input_manager.reset()
        
        Logger.info(f"Switch UI opened with {len(monsters)} Pokemon, force_switch={force_switch}")
    
    def close(self):
        """Close the overlay."""
        self.overlay_show = False
        self.slots.clear()
        self.force_switch = False
    
    def _create_slots(self):
        """Create Pokemon slots for selection."""
        self.slots.clear()
        
        slot_width = self.panel_width - 40
        slot_height = 80
        slot_spacing = 10
        start_y = self.panel_y + 50
        
        for i, monster in enumerate(self.monsters):
            is_current = monster == self.current_monster
            slot = PokemonSlot(
                x=self.panel_x + 20,
                y=start_y + i * (slot_height + slot_spacing),
                width=slot_width,
                height=slot_height,
                monster=monster,
                is_current=is_current,
                callback=self._on_slot_selected
            )
            self.slots.append(slot)
    
    def _on_slot_selected(self, monster: Monster):
        """Called when a Pokemon slot is selected."""
        if self.on_switch:
            self.on_switch(monster)
        self.close()
    
    def has_alive_pokemon(self) -> bool:
        """Check if there are any alive Pokemon that can be switched to."""
        for monster in self.monsters:
            if monster != self.current_monster and monster.get("hp", 0) > 0:
                return True
        return False
    
    def update(self, dt: float):
        """Update the UI."""
        if not self.overlay_show:
            return
        
        try:
            # Update slots
            for slot in self.slots:
                slot.update(dt)
            
            # Update cancel button (only if not force switch)
            if not self.force_switch:
                mouse_pos = input_manager.mouse_pos
                self.cancel_hovered = self.cancel_rect.collidepoint(mouse_pos)
                
                if self.cancel_hovered and input_manager.mouse_pressed(1):
                    if self.on_cancel:
                        self.on_cancel()
                    self.close()
            
            # Also allow ESC to close (if not force switch)
            if not self.force_switch:
                keys = pg.key.get_pressed()
                if keys[pg.K_ESCAPE]:
                    if self.on_cancel:
                        self.on_cancel()
                    self.close()
        except Exception as e:
            Logger.error(f"Error in SwitchPokemonUI update: {e}")
            self.close()  # Close on error to prevent freeze
    
    def draw(self, screen: pg.Surface):
        """Draw the overlay."""
        if not self.overlay_show:
            return
        
        # Dark overlay
        overlay = pg.Surface((GameSettings.SCREEN_WIDTH, GameSettings.SCREEN_HEIGHT), pg.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))
        
        # Panel background
        panel_rect = pg.Rect(self.panel_x, self.panel_y, self.panel_width, self.panel_height)
        pg.draw.rect(screen, (50, 50, 70), panel_rect, border_radius=15)
        pg.draw.rect(screen, (100, 100, 120), panel_rect, 3, border_radius=15)
        
        # Title
        title_font = pg.font.Font(None, 32)
        if self.force_switch:
            title_text = title_font.render("Choose next Pokemon!", True, (255, 200, 100))
        else:
            title_text = title_font.render("Switch Pokemon", True, (255, 255, 255))
        title_rect = title_text.get_rect(centerx=self.panel_x + self.panel_width // 2, y=self.panel_y + 12)
        screen.blit(title_text, title_rect)
        
        # Draw slots
        for slot in self.slots:
            slot.draw(screen)
        
        # Cancel button (only if not force switch)
        if not self.force_switch:
            cancel_color = (150, 80, 80) if self.cancel_hovered else (100, 60, 60)
            pg.draw.rect(screen, cancel_color, self.cancel_rect, border_radius=8)
            pg.draw.rect(screen, (60, 40, 40), self.cancel_rect, 2, border_radius=8)
            
            cancel_font = pg.font.Font(None, 24)
            cancel_text = cancel_font.render("Cancel", True, (255, 255, 255))
            cancel_text_rect = cancel_text.get_rect(center=self.cancel_rect.center)
            screen.blit(cancel_text, cancel_text_rect)
        
        # Show message if no Pokemon available to switch
        if not self.has_alive_pokemon() and self.force_switch:
            no_pokemon_font = pg.font.Font(None, 28)
            no_pokemon_text = no_pokemon_font.render("No Pokemon available!", True, (255, 100, 100))
            no_pokemon_rect = no_pokemon_text.get_rect(
                centerx=self.panel_x + self.panel_width // 2,
                y=self.panel_y + self.panel_height - 45
            )
            screen.blit(no_pokemon_text, no_pokemon_rect)