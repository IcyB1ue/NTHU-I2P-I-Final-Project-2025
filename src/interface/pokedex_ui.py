"""
Pokedex UI - Shows all Pokemon in the game.
Captured Pokemon appear in color, uncaptured appear as black silhouettes.
"""
import pygame as pg
from typing import Callable

from src.utils import GameSettings, Logger
from src.core.services import input_manager


# Element type colors
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

# All Pokemon in the game (id, name, sprite_path, element, base_hp, base_atk, base_def)
POKEDEX_DATA = [
    (1, "Bulbasaur", "menu_sprites/bulbasaur.png", "Grass", 45, 7, 7),
    (2, "Ivysaur", "menu_sprites/ivysaur.png", "Grass", 60, 9, 9),
    (3, "Venusaur", "menu_sprites/venusaur.png", "Grass", 80, 12, 12),
    (4, "Charmander", "menu_sprites/charmander.png", "Fire", 39, 8, 6),
    (5, "Charmeleon", "menu_sprites/charmeleon.png", "Fire", 58, 10, 8),
    (6, "Charizard", "menu_sprites/charizard.png", "Fire", 78, 14, 11),
    (7, "Squirtle", "menu_sprites/squirtle.png", "Water", 44, 8, 10),
    (8, "Wartortle", "menu_sprites/wartortle.png", "Water", 59, 9, 11),
    (9, "Blastoise", "menu_sprites/blastoise.png", "Water", 79, 12, 14),
    (10, "Caterpie", "menu_sprites/caterpie.png", "Bug", 25, 5, 5),
    (11, "Weedle", "menu_sprites/weedle.png", "Bug", 25, 6, 4),
    (12, "Pidgey", "menu_sprites/pidgey.png", "Flying", 35, 7, 5),
    (13, "Rattata", "menu_sprites/rattata.png", "Normal", 30, 8, 4),
    (14, "Pikachu", "menu_sprites/pikachu.png", "Electric", 40, 10, 6),
    (15, "Raichu", "menu_sprites/raichu.png", "Electric", 60, 14, 8),
    (16, "Geodude", "menu_sprites/geodude.png", "Rock", 45, 9, 10),
    (17, "Zubat", "menu_sprites/zubat.png", "Poison", 35, 7, 5),
    (18, "Oddish", "menu_sprites/oddish.png", "Grass", 38, 7, 6),
    (19, "Bellsprout", "menu_sprites/bellsprout.png", "Grass", 35, 8, 5),
    (20, "Magikarp", "menu_sprites/magikarp.png", "Water", 20, 3, 3),
    (21, "Psyduck", "menu_sprites/psyduck.png", "Water", 40, 8, 6),
    (22, "Poliwag", "menu_sprites/poliwag.png", "Water", 40, 7, 5),
    (23, "Gastly", "menu_sprites/gastly.png", "Ghost", 35, 10, 4),
    (24, "Haunter", "menu_sprites/haunter.png", "Ghost", 45, 12, 5),
    (25, "Gengar", "menu_sprites/gengar.png", "Ghost", 60, 15, 8),
    (26, "Dratini", "menu_sprites/dratini.png", "Dragon", 45, 10, 7),
    (27, "Dragonair", "menu_sprites/dragonair.png", "Dragon", 61, 12, 9),
    (28, "Dragonite", "menu_sprites/dragonite.png", "Dragon", 91, 16, 13),
]


class PokedexEntry:
    """A single entry in the Pokedex grid."""
    
    def __init__(self, x: int, y: int, size: int, pokemon_data: tuple, is_captured: bool):
        self.rect = pg.Rect(x, y, size, size)
        self.pokemon_id, self.name, self.sprite_path, self.element, self.hp, self.atk, self.def_ = pokemon_data
        self.is_captured = is_captured
        self.hovered = False
        self.sprite = None
        self.silhouette = None
        self._load_sprite()
    
    def _load_sprite(self):
        """Load the Pokemon sprite and create silhouette."""
        try:
            full_path = f"assets/images/{self.sprite_path}"
            original = pg.image.load(full_path).convert_alpha()
            self.sprite = pg.transform.scale(original, (56, 56))
            
            # Create silhouette (black version)
            self.silhouette = self.sprite.copy()
            # Make it black but keep alpha
            pixels = pg.PixelArray(self.silhouette)
            for x_pos in range(self.silhouette.get_width()):
                for y_pos in range(self.silhouette.get_height()):
                    color = self.silhouette.get_at((x_pos, y_pos))
                    if color.a > 0:  # If not transparent
                        pixels[x_pos, y_pos] = (20, 20, 30, color.a)
            del pixels
        except Exception as e:
            Logger.error(f"Failed to load sprite {self.sprite_path}: {e}")
            # Create placeholder
            self.sprite = pg.Surface((56, 56), pg.SRCALPHA)
            self.sprite.fill((100, 100, 100, 128))
            self.silhouette = pg.Surface((56, 56), pg.SRCALPHA)
            self.silhouette.fill((20, 20, 30, 128))
    
    def update(self, mouse_pos: tuple):
        """Update hover state."""
        self.hovered = self.rect.collidepoint(mouse_pos)
    
    def draw(self, screen: pg.Surface):
        """Draw the Pokedex entry."""
        # Background
        if self.hovered:
            bg_color = (70, 80, 100) if self.is_captured else (40, 45, 55)
        else:
            bg_color = (50, 60, 80) if self.is_captured else (30, 35, 45)
        
        pg.draw.rect(screen, bg_color, self.rect, border_radius=8)
        
        # Border based on element (only if captured)
        if self.is_captured:
            border_color = ELEMENT_COLORS.get(self.element, (128, 128, 128))
            pg.draw.rect(screen, border_color, self.rect, 2, border_radius=8)
        else:
            pg.draw.rect(screen, (50, 50, 60), self.rect, 1, border_radius=8)
        
        # Draw sprite or silhouette
        sprite_to_draw = self.sprite if self.is_captured else self.silhouette
        if sprite_to_draw:
            sprite_rect = sprite_to_draw.get_rect(center=(self.rect.centerx, self.rect.centery))
            screen.blit(sprite_to_draw, sprite_rect)
        
        # Draw ID number
        try:
            id_font = pg.font.Font("assets/fonts/Minecraft.ttf", 9)
        except:
            id_font = pg.font.Font(None, 12)
        
        id_text = id_font.render(f"#{self.pokemon_id:03d}", True, (150, 150, 150))
        screen.blit(id_text, (self.rect.x + 4, self.rect.y + 2))


class PokedexUI:
    """The Pokedex interface showing all Pokemon."""
    
    def __init__(self, get_captured_pokemon: Callable[[], list[str]]):
        """
        Initialize Pokedex.
        get_captured_pokemon: Function that returns list of captured Pokemon names.
        """
        self.overlay_show = False
        self.get_captured_pokemon = get_captured_pokemon
        
        # UI dimensions
        self.panel_width = 750
        self.panel_height = 550
        self.panel_x = (GameSettings.SCREEN_WIDTH - self.panel_width) // 2
        self.panel_y = (GameSettings.SCREEN_HEIGHT - self.panel_height) // 2
        
        # Grid layout - 5 columns to make room for detail panel
        self.grid_cols = 5
        self.entry_size = 85
        self.grid_spacing = 8
        self.grid_start_x = self.panel_x + 30
        self.grid_start_y = self.panel_y + 80
        
        # Scrolling
        self.scroll_offset = 0
        self.max_scroll = 0
        
        # Entries
        self.entries: list[PokedexEntry] = []
        
        # Selected entry for details
        self.selected_entry: PokedexEntry | None = None
        
        # Darken background
        self.darken = pg.Surface((GameSettings.SCREEN_WIDTH, GameSettings.SCREEN_HEIGHT))
        self.darken.fill("Black")
        self.darken.set_alpha(200)
        
        # Load fonts
        try:
            self.title_font = pg.font.Font("assets/fonts/Minecraft.ttf", 28)
            self.name_font = pg.font.Font("assets/fonts/Minecraft.ttf", 20)
            self.stat_font = pg.font.Font("assets/fonts/Minecraft.ttf", 14)
            self.small_font = pg.font.Font("assets/fonts/Minecraft.ttf", 12)
        except:
            self.title_font = pg.font.Font(None, 36)
            self.name_font = pg.font.Font(None, 28)
            self.stat_font = pg.font.Font(None, 20)
            self.small_font = pg.font.Font(None, 16)
    
    def open(self):
        """Open the Pokedex."""
        self.overlay_show = True
        self.scroll_offset = 0
        self.selected_entry = None
        self._create_entries()
        input_manager.reset()
        Logger.info("Pokedex opened")
    
    def close(self):
        """Close the Pokedex."""
        self.overlay_show = False
        self.entries.clear()
        input_manager.reset()
    
    def _create_entries(self):
        """Create all Pokedex entries."""
        self.entries.clear()
        captured = self.get_captured_pokemon()
        captured_names = set(captured)
        
        for i, pokemon_data in enumerate(POKEDEX_DATA):
            col = i % self.grid_cols
            row = i // self.grid_cols
            
            x = self.grid_start_x + col * (self.entry_size + self.grid_spacing)
            y = self.grid_start_y + row * (self.entry_size + self.grid_spacing)
            
            is_captured = pokemon_data[1] in captured_names
            
            entry = PokedexEntry(x, y, self.entry_size, pokemon_data, is_captured)
            self.entries.append(entry)
        
        # Calculate max scroll
        total_rows = (len(POKEDEX_DATA) + self.grid_cols - 1) // self.grid_cols
        total_height = total_rows * (self.entry_size + self.grid_spacing)
        visible_height = self.panel_height - 120
        self.max_scroll = max(0, total_height - visible_height)
        
        # Count captured
        self.captured_count = len(captured_names & {p[1] for p in POKEDEX_DATA})
        self.total_count = len(POKEDEX_DATA)
    
    def update(self, dt: float):
        """Update the Pokedex."""
        if not self.overlay_show:
            return
        
        mouse_pos = input_manager.mouse_pos
        
        # Handle close
        if input_manager.key_pressed(pg.K_ESCAPE):
            self.close()
            return
        
        # Close button
        close_rect = pg.Rect(self.panel_x + self.panel_width - 45, self.panel_y + 12, 32, 32)
        if close_rect.collidepoint(mouse_pos) and input_manager.mouse_pressed(1):
            self.close()
            return
        
        # Scroll with mouse wheel
        # pygame doesn't have built-in scroll detection in input_manager, so we'll use arrow keys
        if input_manager.key_down(pg.K_DOWN):
            self.scroll_offset = min(self.max_scroll, self.scroll_offset + 200 * dt)
        if input_manager.key_down(pg.K_UP):
            self.scroll_offset = max(0, self.scroll_offset - 200 * dt)
        
        # Update entries with scroll offset
        for i, entry in enumerate(self.entries):
            col = i % self.grid_cols
            row = i // self.grid_cols
            
            entry.rect.x = self.grid_start_x + col * (self.entry_size + self.grid_spacing)
            entry.rect.y = self.grid_start_y + row * (self.entry_size + self.grid_spacing) - int(self.scroll_offset)
            
            # Only update if visible
            if self.grid_start_y - self.entry_size < entry.rect.y < self.panel_y + self.panel_height:
                entry.update(mouse_pos)
                
                # Check for click to show details
                if entry.hovered and input_manager.mouse_pressed(1):
                    self.selected_entry = entry if entry.is_captured else None
    
    def draw(self, screen: pg.Surface):
        """Draw the Pokedex."""
        if not self.overlay_show:
            return
        
        # Darken background
        screen.blit(self.darken, (0, 0))
        
        # Main panel with gradient-like effect
        panel_rect = pg.Rect(self.panel_x, self.panel_y, self.panel_width, self.panel_height)
        
        # Draw panel background
        pg.draw.rect(screen, (25, 30, 45), panel_rect, border_radius=15)
        
        # Inner border
        inner_rect = panel_rect.inflate(-6, -6)
        pg.draw.rect(screen, (35, 42, 62), inner_rect, border_radius=12)
        
        # Outer border
        pg.draw.rect(screen, (70, 85, 120), panel_rect, 3, border_radius=15)
        
        # Title bar
        title_bar = pg.Rect(self.panel_x, self.panel_y, self.panel_width, 55)
        pg.draw.rect(screen, (180, 60, 60), title_bar, border_top_left_radius=15, border_top_right_radius=15)
        pg.draw.rect(screen, (220, 80, 80), title_bar.inflate(-4, -4), border_top_left_radius=12, border_top_right_radius=12)
        
        # Title
        title_text = self.title_font.render("POKEDEX", True, (255, 255, 255))
        title_rect = title_text.get_rect(center=(self.panel_x + self.panel_width // 2, self.panel_y + 28))
        screen.blit(title_text, title_rect)
        
        # Captured count
        count_text = self.small_font.render(f"Captured: {self.captured_count}/{self.total_count}", True, (255, 220, 150))
        count_rect = count_text.get_rect(x=self.panel_x + 20, centery=self.panel_y + 28)
        screen.blit(count_text, count_rect)
        
        # Close button
        close_rect = pg.Rect(self.panel_x + self.panel_width - 45, self.panel_y + 12, 32, 32)
        mouse_pos = input_manager.mouse_pos
        close_color = (255, 100, 100) if close_rect.collidepoint(mouse_pos) else (200, 70, 70)
        pg.draw.rect(screen, close_color, close_rect, border_radius=6)
        
        close_x = self.small_font.render("X", True, (255, 255, 255))
        close_x_rect = close_x.get_rect(center=close_rect.center)
        screen.blit(close_x, close_x_rect)
        
        # Create clipping rect for grid area only (not the detail panel area)
        grid_width = self.grid_cols * (self.entry_size + self.grid_spacing)
        clip_rect = pg.Rect(self.panel_x + 10, self.grid_start_y - 5, 
                           grid_width + 40, self.panel_height - 90)
        
        # Draw entries (with clipping)
        old_clip = screen.get_clip()
        screen.set_clip(clip_rect)
        
        for entry in self.entries:
            # Only draw if in visible area
            if entry.rect.bottom > clip_rect.top and entry.rect.top < clip_rect.bottom:
                entry.draw(screen)
        
        screen.set_clip(old_clip)
        
        # Scroll indicators - centered on grid area
        grid_center_x = self.grid_start_x + grid_width // 2
        
        if self.scroll_offset > 0:
            # Up arrow
            pg.draw.polygon(screen, (150, 150, 180), [
                (grid_center_x, self.grid_start_y - 15),
                (grid_center_x - 10, self.grid_start_y - 5),
                (grid_center_x + 10, self.grid_start_y - 5),
            ])
        
        if self.scroll_offset < self.max_scroll:
            # Down arrow
            bottom_y = self.panel_y + self.panel_height - 15
            pg.draw.polygon(screen, (150, 150, 180), [
                (grid_center_x, bottom_y + 5),
                (grid_center_x - 10, bottom_y - 5),
                (grid_center_x + 10, bottom_y - 5),
            ])
        
        # Draw selected Pokemon details (overlay on right side)
        if self.selected_entry and self.selected_entry.is_captured:
            self._draw_details(screen)
        else:
            # Draw hint text in detail panel area when nothing selected
            hint_x = self.panel_x + 510 + 100  # Center of detail panel area
            hint_y = self.panel_y + 180
            hint_text = self.small_font.render("Click a captured", True, (100, 110, 130))
            hint_rect = hint_text.get_rect(centerx=hint_x, y=hint_y)
            screen.blit(hint_text, hint_rect)
            hint_text2 = self.small_font.render("Pokemon to view", True, (100, 110, 130))
            hint_rect2 = hint_text2.get_rect(centerx=hint_x, y=hint_y + 18)
            screen.blit(hint_text2, hint_rect2)
            hint_text3 = self.small_font.render("details", True, (100, 110, 130))
            hint_rect3 = hint_text3.get_rect(centerx=hint_x, y=hint_y + 36)
            screen.blit(hint_text3, hint_rect3)
        
        # Scroll hint at bottom
        scroll_hint = self.small_font.render("Use UP/DOWN arrows to scroll", True, (90, 100, 120))
        scroll_hint_rect = scroll_hint.get_rect(centerx=self.panel_x + self.panel_width // 2, 
                                                  y=self.panel_y + self.panel_height - 22)
        screen.blit(scroll_hint, scroll_hint_rect)
    
    def _draw_details(self, screen: pg.Surface):
        """Draw details panel for selected Pokemon."""
        entry = self.selected_entry
        
        # Details panel - positioned to the right of the grid
        detail_width = 200
        detail_height = 240
        # Position after grid: grid ends at panel_x + 30 + 5*(85+8) = panel_x + 495
        detail_x = self.panel_x + 510
        detail_y = self.panel_y + 80
        
        detail_rect = pg.Rect(detail_x, detail_y, detail_width, detail_height)
        
        # Background
        pg.draw.rect(screen, (20, 25, 40), detail_rect, border_radius=10)
        pg.draw.rect(screen, ELEMENT_COLORS.get(entry.element, (100, 100, 100)), detail_rect, 2, border_radius=10)
        
        # Sprite (larger)
        if entry.sprite:
            large_sprite = pg.transform.scale(entry.sprite, (80, 80))
            sprite_rect = large_sprite.get_rect(centerx=detail_rect.centerx, y=detail_y + 15)
            screen.blit(large_sprite, sprite_rect)
        
        # Name
        name_text = self.name_font.render(entry.name, True, (255, 255, 255))
        name_rect = name_text.get_rect(centerx=detail_rect.centerx, y=detail_y + 100)
        screen.blit(name_text, name_rect)
        
        # ID
        id_text = self.small_font.render(f"#{entry.pokemon_id:03d}", True, (180, 180, 180))
        id_rect = id_text.get_rect(centerx=detail_rect.centerx, y=detail_y + 122)
        screen.blit(id_text, id_rect)
        
        # Element badge
        elem_color = ELEMENT_COLORS.get(entry.element, (128, 128, 128))
        elem_rect = pg.Rect(detail_rect.centerx - 40, detail_y + 145, 80, 22)
        pg.draw.rect(screen, elem_color, elem_rect, border_radius=10)
        elem_text = self.small_font.render(entry.element, True, (255, 255, 255))
        elem_text_rect = elem_text.get_rect(center=elem_rect.center)
        screen.blit(elem_text, elem_text_rect)
        
        # Stats
        stats_y = detail_y + 178
        stats = [
            ("HP", entry.hp, (100, 200, 100)),
            ("ATK", entry.atk, (200, 100, 100)),
            ("DEF", entry.def_, (100, 150, 200)),
        ]
        
        for i, (stat_name, value, color) in enumerate(stats):
            stat_text = self.stat_font.render(f"{stat_name}: {value}", True, color)
            stat_rect = stat_text.get_rect(centerx=detail_rect.centerx, y=stats_y + i * 18)
            screen.blit(stat_text, stat_rect)