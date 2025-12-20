"""
PC UI - Interface for managing Pokemon storage.
"""
import pygame as pg
from typing import Callable

from src.utils import GameSettings, Logger
from src.utils.definition import Monster
from src.sprites import Sprite, Text
from src.interface.components.button import Button
from src.core.services import input_manager


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
    "Steel": (184, 184, 208),
}


class PokemonSlotPC:
    """A slot displaying a Pokemon in the PC interface."""
    
    def __init__(self, x: int, y: int, width: int, height: int, monster: Monster | None,
                 on_click: Callable[[], None] | None = None, is_selected: bool = False):
        self.rect = pg.Rect(x, y, width, height)
        self.monster = monster
        self.on_click = on_click
        self.is_selected = is_selected
        self.hovered = False
        self.sprite = None
        
        if monster:
            self._load_sprite()
    
    def _load_sprite(self):
        """Load the Pokemon sprite."""
        if not self.monster:
            return
        
        sprite_path = self.monster.get("sprite") or self.monster.get("sprite_path")
        if sprite_path:
            try:
                from src.sprites import Sprite as GameSprite
                sprite_obj = GameSprite(sprite_path, (48, 48))
                self.sprite = sprite_obj.image
            except Exception as e:
                Logger.error(f"Failed to load sprite: {e}")
                self.sprite = None
    
    def update(self, dt: float):
        """Update slot state."""
        if not self.monster:
            return
        
        mouse_pos = input_manager.mouse_pos
        self.hovered = self.rect.collidepoint(mouse_pos)
        
        if self.hovered and input_manager.mouse_pressed(1):
            if self.on_click:
                self.on_click()
    
    def draw(self, screen: pg.Surface):
        """Draw the Pokemon slot."""
        # Background color
        if self.is_selected:
            bg_color = (100, 180, 100)  # Green for selected
        elif not self.monster:
            bg_color = (50, 50, 50)  # Dark for empty
        elif self.hovered:
            bg_color = (100, 100, 150)  # Light blue for hover
        else:
            bg_color = (70, 70, 90)  # Normal
        
        # Draw background
        pg.draw.rect(screen, bg_color, self.rect, border_radius=8)
        pg.draw.rect(screen, (40, 40, 40), self.rect, 2, border_radius=8)
        
        if not self.monster:
            # Draw empty slot indicator
            font = pg.font.Font(None, 20)
            empty_text = font.render("Empty", True, (100, 100, 100))
            empty_rect = empty_text.get_rect(center=self.rect.center)
            screen.blit(empty_text, empty_rect)
            return
        
        # Draw sprite
        if self.sprite:
            sprite_x = self.rect.x + 5
            sprite_y = self.rect.y + (self.rect.height - 48) // 2
            screen.blit(self.sprite, (sprite_x, sprite_y))
        
        # Draw Pokemon info
        info_x = self.rect.x + 58
        
        # Name
        font = pg.font.Font(None, 18)
        name = self.monster.get("name", "???")
        if len(name) > 10:
            name = name[:9] + "."
        name_text = font.render(name, True, (255, 255, 255))
        screen.blit(name_text, (info_x, self.rect.y + 5))
        
        # Level
        level_font = pg.font.Font(None, 16)
        level_text = level_font.render(f"Lv.{self.monster.get('level', 1)}", True, (200, 200, 200))
        screen.blit(level_text, (info_x, self.rect.y + 22))
        
        # HP bar (small)
        hp = self.monster.get("hp", 0)
        max_hp = self.monster.get("max_hp", 1)
        hp_bar_width = 60
        hp_bar_height = 6
        hp_bar_x = info_x
        hp_bar_y = self.rect.y + 38
        
        # Background
        pg.draw.rect(screen, (40, 40, 40), (hp_bar_x, hp_bar_y, hp_bar_width, hp_bar_height))
        
        # Fill
        if max_hp > 0:
            hp_pct = hp / max_hp
            fill_width = int(hp_bar_width * hp_pct)
            if hp_pct > 0.5:
                color = (0, 200, 0)
            elif hp_pct > 0.25:
                color = (200, 200, 0)
            else:
                color = (200, 0, 0)
            if fill_width > 0:
                pg.draw.rect(screen, color, (hp_bar_x, hp_bar_y, fill_width, hp_bar_height))
        
        # Element badge
        element = self.monster.get("element", "Normal")
        elem_color = ELEMENT_COLORS.get(element, (128, 128, 128))
        elem_font = pg.font.Font(None, 14)
        elem_text = elem_font.render(element[:3], True, elem_color)
        screen.blit(elem_text, (info_x + 45, self.rect.y + 22))


class PCUI:
    """UI for the PC storage system."""
    
    def __init__(self):
        self.overlay_show = False
        
        # References set when opened
        self.party: list[Monster] = []
        self.pc_pokemon: list[Monster] = []
        self.on_deposit: Callable[[Monster], bool] | None = None
        self.on_withdraw: Callable[[int], Monster | None] | None = None
        
        # Selection state
        self.selected_party_index: int | None = None
        self.selected_pc_index: int | None = None
        
        # Pagination for PC
        self.pc_page = 0
        self.pc_slots_per_page = 12  # 3 rows x 4 columns
        
        # Slots
        self.party_slots: list[PokemonSlotPC] = []
        self.pc_slots: list[PokemonSlotPC] = []
        
        # UI dimensions
        self.panel_width = 900
        self.panel_height = 550
        self.panel_x = (GameSettings.SCREEN_WIDTH - self.panel_width) // 2
        self.panel_y = (GameSettings.SCREEN_HEIGHT - self.panel_height) // 2
        
        # Message
        self.message = ""
        self.message_timer = 0.0
        
        # Darken background
        self.darken = pg.Surface((GameSettings.SCREEN_WIDTH, GameSettings.SCREEN_HEIGHT))
        self.darken.fill("Black")
        self.darken.set_alpha(180)
    
    def open(self, party: list[Monster], pc_pokemon: list[Monster],
             on_deposit: Callable[[Monster], bool],
             on_withdraw: Callable[[int], Monster | None]):
        """Open the PC interface."""
        self.overlay_show = True
        self.party = party
        self.pc_pokemon = pc_pokemon
        self.on_deposit = on_deposit
        self.on_withdraw = on_withdraw
        self.selected_party_index = None
        self.selected_pc_index = None
        self.pc_page = 0
        self.message = ""
        self._create_slots()
        input_manager.reset()
        Logger.info(f"PC opened - Party: {len(party)}, PC: {len(pc_pokemon)}")
    
    def close(self):
        """Close the PC interface."""
        self.overlay_show = False
        self.party_slots.clear()
        self.pc_slots.clear()
        input_manager.reset()
    
    def _create_slots(self):
        """Create all Pokemon slots."""
        self.party_slots.clear()
        self.pc_slots.clear()
        
        # Party slots (left side) - 2 columns x 3 rows
        party_start_x = self.panel_x + 30
        party_start_y = self.panel_y + 80
        slot_width = 130
        slot_height = 55
        slot_spacing_x = 10
        slot_spacing_y = 10
        
        for i in range(6):
            col = i % 2
            row = i // 2
            x = party_start_x + col * (slot_width + slot_spacing_x)
            y = party_start_y + row * (slot_height + slot_spacing_y)
            
            monster = self.party[i] if i < len(self.party) else None
            is_selected = (self.selected_party_index == i)
            
            slot = PokemonSlotPC(
                x, y, slot_width, slot_height, monster,
                on_click=lambda idx=i: self._on_party_slot_clicked(idx),
                is_selected=is_selected
            )
            self.party_slots.append(slot)
        
        # PC slots (right side) - 4 columns x 3 rows
        pc_start_x = self.panel_x + 320
        pc_start_y = self.panel_y + 80
        
        start_index = self.pc_page * self.pc_slots_per_page
        
        for i in range(self.pc_slots_per_page):
            col = i % 4
            row = i // 4
            x = pc_start_x + col * (slot_width + slot_spacing_x)
            y = pc_start_y + row * (slot_height + slot_spacing_y)
            
            pc_index = start_index + i
            monster = self.pc_pokemon[pc_index] if pc_index < len(self.pc_pokemon) else None
            is_selected = (self.selected_pc_index == pc_index)
            
            slot = PokemonSlotPC(
                x, y, slot_width, slot_height, monster,
                on_click=lambda idx=pc_index: self._on_pc_slot_clicked(idx),
                is_selected=is_selected
            )
            self.pc_slots.append(slot)
    
    def _on_party_slot_clicked(self, index: int):
        """Handle party slot click."""
        if index >= len(self.party):
            return
        
        # If PC slot was selected, swap/withdraw
        if self.selected_pc_index is not None:
            self._swap_pokemon()
            return
        
        # Toggle selection
        if self.selected_party_index == index:
            self.selected_party_index = None
        else:
            self.selected_party_index = index
            self.selected_pc_index = None
        
        self._create_slots()
    
    def _on_pc_slot_clicked(self, index: int):
        """Handle PC slot click."""
        # If party slot was selected, swap/deposit
        if self.selected_party_index is not None:
            self._swap_pokemon()
            return
        
        # Toggle selection (only if there's a Pokemon there)
        if index < len(self.pc_pokemon):
            if self.selected_pc_index == index:
                self.selected_pc_index = None
            else:
                self.selected_pc_index = index
                self.selected_party_index = None
            
            self._create_slots()
    
    def _swap_pokemon(self):
        """Swap Pokemon between party and PC."""
        if self.selected_party_index is not None and self.selected_pc_index is not None:
            # Swap party Pokemon with PC Pokemon
            if self.selected_pc_index < len(self.pc_pokemon):
                party_mon = self.party[self.selected_party_index]
                pc_mon = self.pc_pokemon[self.selected_pc_index]
                
                # Swap them
                self.party[self.selected_party_index] = pc_mon
                self.pc_pokemon[self.selected_pc_index] = party_mon
                
                self.message = f"Swapped {party_mon.get('name', '???')} with {pc_mon.get('name', '???')}!"
                self.message_timer = 2.0
                Logger.info(self.message)
        
        elif self.selected_party_index is not None:
            # Deposit to empty PC slot
            if len(self.party) <= 1:
                self.message = "Can't deposit your last Pokemon!"
                self.message_timer = 2.0
                Logger.warning(self.message)
            else:
                party_mon = self.party[self.selected_party_index]
                if self.on_deposit and self.on_deposit(party_mon):
                    self.party.pop(self.selected_party_index)
                    self.message = f"Deposited {party_mon.get('name', '???')} to PC!"
                    self.message_timer = 2.0
                else:
                    self.message = "PC storage is full!"
                    self.message_timer = 2.0
        
        elif self.selected_pc_index is not None:
            # Withdraw to party
            if len(self.party) >= 6:
                self.message = "Party is full! Deposit a Pokemon first."
                self.message_timer = 2.0
                Logger.warning(self.message)
            else:
                if self.on_withdraw:
                    pc_mon = self.on_withdraw(self.selected_pc_index)
                    if pc_mon:
                        self.party.append(pc_mon)
                        self.message = f"Withdrew {pc_mon.get('name', '???')} to party!"
                        self.message_timer = 2.0
        
        # Reset selection
        self.selected_party_index = None
        self.selected_pc_index = None
        self._create_slots()
    
    def _next_page(self):
        """Go to next PC page."""
        max_pages = (len(self.pc_pokemon) // self.pc_slots_per_page) + 1
        if self.pc_page < max_pages - 1:
            self.pc_page += 1
            self.selected_pc_index = None
            self._create_slots()
    
    def _prev_page(self):
        """Go to previous PC page."""
        if self.pc_page > 0:
            self.pc_page -= 1
            self.selected_pc_index = None
            self._create_slots()
    
    def update(self, dt: float):
        """Update the PC UI."""
        if not self.overlay_show:
            return
        
        # Update message timer
        if self.message_timer > 0:
            self.message_timer -= dt
            if self.message_timer <= 0:
                self.message = ""
        
        # Update slots
        for slot in self.party_slots:
            slot.update(dt)
        for slot in self.pc_slots:
            slot.update(dt)
        
        # Handle keyboard navigation
        if input_manager.key_pressed(pg.K_ESCAPE):
            self.close()
            return
        
        if input_manager.key_pressed(pg.K_LEFT):
            self._prev_page()
        if input_manager.key_pressed(pg.K_RIGHT):
            self._next_page()
        
        # Handle close button click
        mouse_pos = input_manager.mouse_pos
        close_rect = pg.Rect(self.panel_x + self.panel_width - 50, self.panel_y + 10, 40, 40)
        if close_rect.collidepoint(mouse_pos) and input_manager.mouse_pressed(1):
            self.close()
        
        # Handle page button clicks
        prev_rect = pg.Rect(self.panel_x + 420, self.panel_y + self.panel_height - 60, 80, 35)
        next_rect = pg.Rect(self.panel_x + self.panel_width - 110, self.panel_y + self.panel_height - 60, 80, 35)
        
        if prev_rect.collidepoint(mouse_pos) and input_manager.mouse_pressed(1):
            self._prev_page()
        if next_rect.collidepoint(mouse_pos) and input_manager.mouse_pressed(1):
            self._next_page()
        
        # Handle action buttons
        deposit_rect = pg.Rect(self.panel_x + 30, self.panel_y + self.panel_height - 60, 100, 35)
        withdraw_rect = pg.Rect(self.panel_x + 145, self.panel_y + self.panel_height - 60, 100, 35)
        
        if deposit_rect.collidepoint(mouse_pos) and input_manager.mouse_pressed(1):
            if self.selected_party_index is not None:
                self._deposit_selected()
        
        if withdraw_rect.collidepoint(mouse_pos) and input_manager.mouse_pressed(1):
            if self.selected_pc_index is not None:
                self._withdraw_selected()
    
    def _deposit_selected(self):
        """Deposit the selected party Pokemon."""
        if self.selected_party_index is None:
            return
        
        if len(self.party) <= 1:
            self.message = "Can't deposit your last Pokemon!"
            self.message_timer = 2.0
            return
        
        party_mon = self.party[self.selected_party_index]
        if self.on_deposit and self.on_deposit(party_mon):
            self.party.pop(self.selected_party_index)
            self.message = f"Deposited {party_mon.get('name', '???')} to PC!"
            self.message_timer = 2.0
            self.selected_party_index = None
            self._create_slots()
        else:
            self.message = "PC storage is full!"
            self.message_timer = 2.0
    
    def _withdraw_selected(self):
        """Withdraw the selected PC Pokemon."""
        if self.selected_pc_index is None:
            return
        
        if len(self.party) >= 6:
            self.message = "Party is full! Deposit a Pokemon first."
            self.message_timer = 2.0
            return
        
        if self.on_withdraw:
            pc_mon = self.on_withdraw(self.selected_pc_index)
            if pc_mon:
                self.party.append(pc_mon)
                self.message = f"Withdrew {pc_mon.get('name', '???')} to party!"
                self.message_timer = 2.0
                self.selected_pc_index = None
                self._create_slots()
    
    def draw(self, screen: pg.Surface):
        """Draw the PC UI."""
        if not self.overlay_show:
            return
        
        # Darken background
        screen.blit(self.darken, (0, 0))
        
        # Main panel
        panel_rect = pg.Rect(self.panel_x, self.panel_y, self.panel_width, self.panel_height)
        pg.draw.rect(screen, (40, 45, 60), panel_rect, border_radius=15)
        pg.draw.rect(screen, (80, 90, 120), panel_rect, 3, border_radius=15)
        
        # Title
        title_font = pg.font.Font(None, 36)
        title_text = title_font.render("Pokemon Storage System", True, (255, 255, 255))
        title_rect = title_text.get_rect(centerx=self.panel_x + self.panel_width // 2, y=self.panel_y + 15)
        screen.blit(title_text, title_rect)
        
        # Close button
        close_rect = pg.Rect(self.panel_x + self.panel_width - 50, self.panel_y + 10, 40, 40)
        mouse_pos = input_manager.mouse_pos
        close_color = (200, 80, 80) if close_rect.collidepoint(mouse_pos) else (150, 60, 60)
        pg.draw.rect(screen, close_color, close_rect, border_radius=8)
        close_font = pg.font.Font(None, 30)
        close_text = close_font.render("X", True, (255, 255, 255))
        close_text_rect = close_text.get_rect(center=close_rect.center)
        screen.blit(close_text, close_text_rect)
        
        # Section labels
        section_font = pg.font.Font(None, 28)
        
        # Party section
        party_label = section_font.render("Your Party", True, (200, 200, 255))
        screen.blit(party_label, (self.panel_x + 30, self.panel_y + 55))
        
        party_count = section_font.render(f"({len(self.party)}/6)", True, (150, 150, 150))
        screen.blit(party_count, (self.panel_x + 150, self.panel_y + 55))
        
        # PC section
        pc_label = section_font.render("PC Storage", True, (200, 255, 200))
        screen.blit(pc_label, (self.panel_x + 320, self.panel_y + 55))
        
        pc_count = section_font.render(f"({len(self.pc_pokemon)}/120)", True, (150, 150, 150))
        screen.blit(pc_count, (self.panel_x + 450, self.panel_y + 55))
        
        # Page indicator
        max_pages = max(1, (len(self.pc_pokemon) // self.pc_slots_per_page) + 1)
        page_text = section_font.render(f"Page {self.pc_page + 1}/{max_pages}", True, (200, 200, 200))
        page_rect = page_text.get_rect(centerx=self.panel_x + 650, y=self.panel_y + self.panel_height - 55)
        screen.blit(page_text, page_rect)
        
        # Divider line (centered between party and PC sections)
        pg.draw.line(screen, (80, 80, 100), 
                     (self.panel_x + 310, self.panel_y + 70),
                     (self.panel_x + 310, self.panel_y + self.panel_height - 70), 2)
        
        # Draw slots
        for slot in self.party_slots:
            slot.draw(screen)
        for slot in self.pc_slots:
            slot.draw(screen)
        
        # Action buttons
        deposit_rect = pg.Rect(self.panel_x + 30, self.panel_y + self.panel_height - 60, 100, 35)
        withdraw_rect = pg.Rect(self.panel_x + 145, self.panel_y + self.panel_height - 60, 100, 35)
        
        # Deposit button
        dep_color = (80, 120, 80) if self.selected_party_index is not None else (60, 60, 60)
        if deposit_rect.collidepoint(mouse_pos) and self.selected_party_index is not None:
            dep_color = (100, 150, 100)
        pg.draw.rect(screen, dep_color, deposit_rect, border_radius=8)
        pg.draw.rect(screen, (40, 40, 40), deposit_rect, 2, border_radius=8)
        btn_font = pg.font.Font(None, 22)
        dep_text = btn_font.render("Deposit", True, (255, 255, 255))
        dep_text_rect = dep_text.get_rect(center=deposit_rect.center)
        screen.blit(dep_text, dep_text_rect)
        
        # Withdraw button
        with_color = (80, 80, 120) if self.selected_pc_index is not None else (60, 60, 60)
        if withdraw_rect.collidepoint(mouse_pos) and self.selected_pc_index is not None:
            with_color = (100, 100, 150)
        pg.draw.rect(screen, with_color, withdraw_rect, border_radius=8)
        pg.draw.rect(screen, (40, 40, 40), withdraw_rect, 2, border_radius=8)
        with_text = btn_font.render("Withdraw", True, (255, 255, 255))
        with_text_rect = with_text.get_rect(center=withdraw_rect.center)
        screen.blit(with_text, with_text_rect)
        
        # Page navigation buttons
        prev_rect = pg.Rect(self.panel_x + 420, self.panel_y + self.panel_height - 60, 80, 35)
        next_rect = pg.Rect(self.panel_x + self.panel_width - 110, self.panel_y + self.panel_height - 60, 80, 35)
        
        # Previous button
        prev_color = (70, 70, 90) if self.pc_page > 0 else (50, 50, 50)
        if prev_rect.collidepoint(mouse_pos) and self.pc_page > 0:
            prev_color = (90, 90, 110)
        pg.draw.rect(screen, prev_color, prev_rect, border_radius=8)
        pg.draw.rect(screen, (40, 40, 40), prev_rect, 2, border_radius=8)
        prev_text = btn_font.render("< Prev", True, (255, 255, 255) if self.pc_page > 0 else (100, 100, 100))
        prev_text_rect = prev_text.get_rect(center=prev_rect.center)
        screen.blit(prev_text, prev_text_rect)
        
        # Next button
        has_next = (self.pc_page + 1) * self.pc_slots_per_page < len(self.pc_pokemon) + self.pc_slots_per_page
        next_color = (70, 70, 90) if has_next else (50, 50, 50)
        if next_rect.collidepoint(mouse_pos) and has_next:
            next_color = (90, 90, 110)
        pg.draw.rect(screen, next_color, next_rect, border_radius=8)
        pg.draw.rect(screen, (40, 40, 40), next_rect, 2, border_radius=8)
        next_text = btn_font.render("Next >", True, (255, 255, 255))
        next_text_rect = next_text.get_rect(center=next_rect.center)
        screen.blit(next_text, next_text_rect)
        
        # Message
        if self.message:
            msg_font = pg.font.Font(None, 26)
            msg_surface = msg_font.render(self.message, True, (255, 255, 100))
            msg_rect = msg_surface.get_rect(centerx=self.panel_x + self.panel_width // 2, y=self.panel_y + self.panel_height - 90)
            
            # Background for message
            bg_rect = msg_rect.inflate(20, 10)
            pg.draw.rect(screen, (0, 0, 0, 200), bg_rect, border_radius=5)
            screen.blit(msg_surface, msg_rect)