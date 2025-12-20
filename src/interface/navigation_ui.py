"""
Navigation UI - Beautiful interface for navigating to destinations.
Uses BFS pathfinding to guide the player.
"""
import pygame as pg
import math
from collections import deque
from src.utils import GameSettings, Logger, Position
from src.core.services import input_manager
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core import GameManager


# Destination data: (name, map_path, tile_x, tile_y, icon_color, description)
DESTINATIONS = [
    ("Home", "map.tmx", 16, 28, (120, 200, 120), "Your cozy house"),
    ("Gym", "map.tmx", 24, 23, (230, 90, 90), "Battle trainers"),
    ("Shop", "map.tmx", 54, 14, (90, 160, 230), "Buy items"),
    ("Professor", "map.tmx", 10, 23, (190, 140, 230), "Quiz for coins"),
]


class DestinationCard:
    """A beautiful destination card with hover effects."""
    
    def __init__(self, x: int, y: int, width: int, height: int,
                 name: str, description: str, icon_color: tuple,
                 on_click):
        self.base_rect = pg.Rect(x, y, width, height)
        self.rect = self.base_rect.copy()
        self.name = name
        self.description = description
        self.icon_color = icon_color
        self.on_click = on_click
        self.hovered = False
        self.hover_progress = 0.0
        self.click_scale = 1.0
        
        # Load fonts
        try:
            self.name_font = pg.font.Font("assets/fonts/Minecraft.ttf", 14)
            self.desc_font = pg.font.Font("assets/fonts/Minecraft.ttf", 9)
        except:
            self.name_font = pg.font.Font(None, 20)
            self.desc_font = pg.font.Font(None, 14)
    
    def update(self, dt: float, mouse_pos: tuple) -> bool:
        """Update card state. Returns True if clicked."""
        self.hovered = self.rect.collidepoint(mouse_pos)
        
        # Smooth hover animation
        target = 1.0 if self.hovered else 0.0
        self.hover_progress += (target - self.hover_progress) * 12 * dt
        
        # Click scale animation
        self.click_scale += (1.0 - self.click_scale) * 10 * dt
        
        if self.hovered and input_manager.mouse_pressed(1):
            self.click_scale = 0.95
            self.on_click()
            return True
        return False
    
    def draw(self, screen: pg.Surface, delay_offset: float = 0):
        """Draw the destination card."""
        # Hover lift effect
        lift = int(3 * self.hover_progress)
        
        draw_rect = self.rect.copy()
        draw_rect.y -= lift
        
        # Scale for click
        if self.click_scale != 1.0:
            w_diff = int(draw_rect.width * (1 - self.click_scale))
            h_diff = int(draw_rect.height * (1 - self.click_scale))
            draw_rect.inflate_ip(-w_diff, -h_diff)
        
        # Shadow (moves down when hovered for lift effect)
        shadow_rect = self.base_rect.copy()
        shadow_rect.x += 3
        shadow_rect.y += 3 + lift
        shadow_alpha = 60 + int(30 * self.hover_progress)
        shadow_surf = pg.Surface((shadow_rect.width, shadow_rect.height), pg.SRCALPHA)
        pg.draw.rect(shadow_surf, (0, 0, 0, shadow_alpha), (0, 0, shadow_rect.width, shadow_rect.height), border_radius=12)
        screen.blit(shadow_surf, shadow_rect.topleft)
        
        # Background gradient effect
        base_color = (50, 58, 78)
        hover_add = int(20 * self.hover_progress)
        bg_color = tuple(min(255, c + hover_add) for c in base_color)
        
        pg.draw.rect(screen, bg_color, draw_rect, border_radius=12)
        
        # Top highlight
        highlight_rect = pg.Rect(draw_rect.x + 2, draw_rect.y + 2, draw_rect.width - 4, 15)
        highlight_color = tuple(min(255, c + 12) for c in bg_color)
        pg.draw.rect(screen, highlight_color, highlight_rect, 
                     border_top_left_radius=10, border_top_right_radius=10)
        
        # Border - colored when hovered
        if self.hover_progress > 0.1:
            border_color = tuple(int(c * (0.5 + 0.5 * self.hover_progress)) for c in self.icon_color)
        else:
            border_color = (70, 80, 100)
        pg.draw.rect(screen, border_color, draw_rect, 2, border_radius=12)
        
        # Icon circle with glow
        icon_x = draw_rect.x + 28
        icon_y = draw_rect.centery
        
        # Glow effect
        if self.hover_progress > 0.1:
            glow_size = int(24 + 6 * self.hover_progress)
            glow_surf = pg.Surface((glow_size * 2, glow_size * 2), pg.SRCALPHA)
            glow_alpha = int(50 * self.hover_progress)
            pg.draw.circle(glow_surf, (*self.icon_color, glow_alpha), (glow_size, glow_size), glow_size)
            screen.blit(glow_surf, (icon_x - glow_size, icon_y - glow_size))
        
        # Icon background
        pg.draw.circle(screen, (30, 35, 50), (icon_x, icon_y), 16)
        pg.draw.circle(screen, self.icon_color, (icon_x, icon_y), 13)
        
        # Simple location pin
        pin_color = (255, 255, 255)
        pg.draw.circle(screen, pin_color, (icon_x, icon_y - 2), 4)
        pg.draw.polygon(screen, pin_color, [
            (icon_x, icon_y + 7),
            (icon_x - 3, icon_y + 1),
            (icon_x + 3, icon_y + 1),
        ])
        
        # Name text
        name_text = self.name_font.render(self.name, True, (255, 255, 255))
        screen.blit(name_text, (draw_rect.x + 52, draw_rect.centery - 12))
        
        # Description text
        desc_color = (140, 150, 170) if not self.hovered else (180, 190, 210)
        desc_text = self.desc_font.render(self.description, True, desc_color)
        screen.blit(desc_text, (draw_rect.x + 52, draw_rect.centery + 4))
        
        # Arrow when hovered
        if self.hover_progress > 0.3:
            arrow_x = draw_rect.right - 20
            arrow_y = draw_rect.centery
            arrow_color = (*self.icon_color[:3], int(200 * self.hover_progress))
            
            # Animated arrow position
            arrow_offset = int(3 * math.sin(pg.time.get_ticks() / 200))
            
            arrow_surf = pg.Surface((20, 20), pg.SRCALPHA)
            pg.draw.polygon(arrow_surf, arrow_color, [
                (12 + arrow_offset, 10),
                (4 + arrow_offset, 4),
                (4 + arrow_offset, 16),
            ])
            screen.blit(arrow_surf, (arrow_x - 10, arrow_y - 10))


class NavigationUI:
    """Beautiful navigation interface with BFS pathfinding."""
    
    def __init__(self, game_manager: "GameManager"):
        self.game_manager = game_manager
        self.overlay_show = False
        self.is_navigating = False
        
        # Path data
        self.current_path: list[tuple[int, int]] = []
        self.path_index = 0
        self.target_destination = None
        self.navigation_speed = 4.0 * GameSettings.TILE_SIZE
        
        # UI dimensions
        self.panel_width = 300
        self.panel_height = 380
        self.panel_x = (GameSettings.SCREEN_WIDTH - self.panel_width) // 2
        self.panel_y = (GameSettings.SCREEN_HEIGHT - self.panel_height) // 2
        
        # Destination cards
        self.cards: list[DestinationCard] = []
        
        # Animation
        self.open_animation = 0.0
        self.path_pulse = 0.0
        
        # Status message
        self.status_message = ""
        self.status_color = (255, 255, 100)
        self.status_timer = 0.0
        
        # Darken background
        self.darken = pg.Surface((GameSettings.SCREEN_WIDTH, GameSettings.SCREEN_HEIGHT))
        self.darken.fill("Black")
        
        # Load fonts
        try:
            self.title_font = pg.font.Font("assets/fonts/Minecraft.ttf", 20)
            self.status_font = pg.font.Font("assets/fonts/Minecraft.ttf", 11)
            self.hint_font = pg.font.Font("assets/fonts/Minecraft.ttf", 9)
        except:
            self.title_font = pg.font.Font(None, 26)
            self.status_font = pg.font.Font(None, 16)
            self.hint_font = pg.font.Font(None, 14)
    
    def open(self):
        """Open the navigation menu."""
        # Only allow navigation on main map
        if self.game_manager.current_map.path_name != "map.tmx":
            Logger.info("Navigation only available on main map")
            return
        
        self.overlay_show = True
        self.open_animation = 0.0
        self.status_message = "Select a destination"
        self.status_color = (180, 190, 210)
        self._create_cards()
        input_manager.reset()
        Logger.info("Navigation UI opened")
    
    def close(self):
        """Close the navigation menu."""
        self.overlay_show = False
        self.cards.clear()
        input_manager.reset()
    
    def stop_navigation(self):
        """Stop current navigation."""
        self.is_navigating = False
        self.current_path = []
        self.path_index = 0
        self.target_destination = None
        Logger.info("Navigation stopped")
    
    def _create_cards(self):
        """Create destination cards."""
        self.cards.clear()
        
        card_width = 240
        card_height = 50
        start_x = self.panel_x + (self.panel_width - card_width) // 2
        start_y = self.panel_y + 70
        spacing = 58
        
        for i, (name, map_path, tile_x, tile_y, color, desc) in enumerate(DESTINATIONS):
            card = DestinationCard(
                x=start_x,
                y=start_y + i * spacing,
                width=card_width,
                height=card_height,
                name=name,
                description=desc,
                icon_color=color,
                on_click=lambda n=name, mp=map_path, tx=tile_x, ty=tile_y: self._navigate_to(n, mp, tx, ty)
            )
            self.cards.append(card)
    
    def _navigate_to(self, name: str, map_path: str, tile_x: int, tile_y: int):
        """Start navigation to a destination."""
        # Check if we're on the correct map
        if self.game_manager.current_map.path_name != map_path:
            self.status_message = "Must be on main map!"
            self.status_color = (255, 100, 100)
            self.status_timer = 2.0
            return
        
        player = self.game_manager.player
        if not player:
            return
        
        # Get player tile position
        start_x = int(player.position.x // GameSettings.TILE_SIZE)
        start_y = int(player.position.y // GameSettings.TILE_SIZE)
        
        # Find path using BFS
        path = self._bfs_pathfind(start_x, start_y, tile_x, tile_y)
        
        if path:
            self.current_path = path
            self.path_index = 0
            self.is_navigating = True
            self.target_destination = name
            self.close()
            Logger.info(f"Navigation started to {name}, path length: {len(path)}")
        else:
            self.status_message = "No path found!"
            self.status_color = (255, 100, 100)
            self.status_timer = 2.0
    
    def _bfs_pathfind(self, start_x: int, start_y: int, end_x: int, end_y: int) -> list[tuple[int, int]]:
        """Find shortest path using BFS algorithm."""
        current_map = self.game_manager.current_map
        
        map_width = current_map.tmxdata.width
        map_height = current_map.tmxdata.height
        
        # Create collision grid
        collision_set = set()
        for rect in current_map._collision_map:
            tile_x = rect.x // GameSettings.TILE_SIZE
            tile_y = rect.y // GameSettings.TILE_SIZE
            collision_set.add((tile_x, tile_y))
        
        # Add enemy trainer positions as obstacles
        for enemy in self.game_manager.current_enemy_trainers:
            enemy_tile_x = int(enemy.position.x // GameSettings.TILE_SIZE)
            enemy_tile_y = int(enemy.position.y // GameSettings.TILE_SIZE)
            collision_set.add((enemy_tile_x, enemy_tile_y))
        
        # Add shop positions as obstacles
        for shop in self.game_manager.current_shops:
            shop_tile_x = int(shop.position.x // GameSettings.TILE_SIZE)
            shop_tile_y = int(shop.position.y // GameSettings.TILE_SIZE)
            collision_set.add((shop_tile_x, shop_tile_y))
        
        # Add teleporter positions as obstacles
        for tp in current_map.teleporters:
            tp_tile_x = int(tp.pos.x // GameSettings.TILE_SIZE)
            tp_tile_y = int(tp.pos.y // GameSettings.TILE_SIZE)
            collision_set.add((tp_tile_x, tp_tile_y))
        
        # BFS
        queue = deque([(start_x, start_y, [(start_x, start_y)])])
        visited = {(start_x, start_y)}
        
        directions = [(0, -1), (0, 1), (-1, 0), (1, 0)]
        
        while queue:
            x, y, path = queue.popleft()
            
            if x == end_x and y == end_y:
                return path
            
            for dx, dy in directions:
                nx, ny = x + dx, y + dy
                
                if nx < 0 or nx >= map_width or ny < 0 or ny >= map_height:
                    continue
                
                if (nx, ny) in visited:
                    continue
                
                if (nx, ny) in collision_set:
                    continue
                
                visited.add((nx, ny))
                queue.append((nx, ny, path + [(nx, ny)]))
        
        return []
    
    def update(self, dt: float):
        """Update navigation UI."""
        self.path_pulse += dt * 4
        
        # Update status timer
        if self.status_timer > 0:
            self.status_timer -= dt
        
        if not self.overlay_show:
            # Update path following
            if self.is_navigating and self.current_path:
                self._follow_path(dt)
            return
        
        # Update open animation
        self.open_animation = min(1.0, self.open_animation + dt * 7)
        
        mouse_pos = input_manager.mouse_pos
        
        # Handle close
        if input_manager.key_pressed(pg.K_ESCAPE):
            self.close()
            return
        
        # Close button
        close_rect = pg.Rect(self.panel_x + self.panel_width - 38, self.panel_y + 10, 26, 26)
        if close_rect.collidepoint(mouse_pos) and input_manager.mouse_pressed(1):
            self.close()
            return
        
        # Click outside to close
        panel_rect = pg.Rect(self.panel_x, self.panel_y, self.panel_width, self.panel_height)
        if input_manager.mouse_pressed(1) and not panel_rect.collidepoint(mouse_pos):
            self.close()
            return
        
        # Update cards
        for card in self.cards:
            card.update(dt, mouse_pos)
    
    def _follow_path(self, dt: float):
        """Make the player follow the current path."""
        player = self.game_manager.player
        if not player:
            self.stop_navigation()
            return
        
        if self.path_index >= len(self.current_path):
            self.stop_navigation()
            Logger.info("Navigation complete!")
            return
        
        target_x, target_y = self.current_path[self.path_index]
        target_px = target_x * GameSettings.TILE_SIZE
        target_py = target_y * GameSettings.TILE_SIZE
        
        dx = target_px - player.position.x
        dy = target_py - player.position.y
        distance = (dx ** 2 + dy ** 2) ** 0.5
        
        if distance < 5:
            self.path_index += 1
            return
        
        if distance > 0:
            dx /= distance
            dy /= distance
        
        # Update player direction
        if abs(dx) > abs(dy):
            player.direction = "right" if dx > 0 else "left"
        else:
            player.direction = "down" if dy > 0 else "up"
        
        player.animation.switch(player.direction)
        
        # Move player
        move_x = dx * self.navigation_speed * dt
        move_y = dy * self.navigation_speed * dt
        
        to_check_x = player.animation.rect.copy()
        to_check_x.x += int(move_x)
        if not self.game_manager.check_collision(to_check_x):
            player.position.x += move_x
        
        to_check_y = player.animation.rect.copy()
        to_check_y.y += int(move_y)
        if not self.game_manager.check_collision(to_check_y):
            player.position.y += move_y
    
    def draw(self, screen: pg.Surface):
        """Draw navigation UI."""
        # Draw path on world
        if self.is_navigating and self.current_path and self.game_manager.player:
            self._draw_path(screen)
        
        if not self.overlay_show:
            return
        
        # Darken background with fade
        alpha = int(160 * self.open_animation)
        self.darken.set_alpha(alpha)
        screen.blit(self.darken, (0, 0))
        
        # Animated panel
        scale = 0.9 + 0.1 * self.open_animation
        panel_w = int(self.panel_width * scale)
        panel_h = int(self.panel_height * scale)
        panel_x = (GameSettings.SCREEN_WIDTH - panel_w) // 2
        panel_y = (GameSettings.SCREEN_HEIGHT - panel_h) // 2
        panel_rect = pg.Rect(panel_x, panel_y, panel_w, panel_h)
        
        # Panel shadow
        shadow_rect = panel_rect.copy()
        shadow_rect.x += 5
        shadow_rect.y += 5
        pg.draw.rect(screen, (10, 15, 25), shadow_rect, border_radius=16)
        
        # Panel background
        pg.draw.rect(screen, (35, 42, 58), panel_rect, border_radius=14)
        
        # Inner panel
        inner_rect = panel_rect.inflate(-6, -6)
        pg.draw.rect(screen, (42, 50, 68), inner_rect, border_radius=11)
        
        # Title bar
        title_bar = pg.Rect(panel_rect.x + 3, panel_rect.y + 3, panel_rect.width - 6, 42)
        pg.draw.rect(screen, (55, 65, 88), title_bar, 
                     border_top_left_radius=11, border_top_right_radius=11)
        
        # Border
        pg.draw.rect(screen, (75, 90, 120), panel_rect, 2, border_radius=14)
        
        # Title with icon
        title_x = panel_rect.centerx
        
        # Compass icon
        compass_x = title_x - 60
        compass_y = panel_rect.y + 24
        pg.draw.circle(screen, (100, 180, 255), (compass_x, compass_y), 10, 2)
        pg.draw.line(screen, (255, 100, 100), (compass_x, compass_y - 6), (compass_x, compass_y + 2), 2)
        pg.draw.line(screen, (255, 255, 255), (compass_x - 5, compass_y), (compass_x + 5, compass_y), 2)
        
        # Title text
        title_text = self.title_font.render("Navigation", True, (255, 255, 255))
        title_rect = title_text.get_rect(midleft=(compass_x + 18, compass_y))
        screen.blit(title_text, title_rect)
        
        # Close button
        close_rect = pg.Rect(panel_rect.right - 38, panel_rect.y + 10, 26, 26)
        mouse_pos = input_manager.mouse_pos
        close_hovered = close_rect.collidepoint(mouse_pos)
        close_color = (200, 80, 80) if close_hovered else (120, 60, 60)
        pg.draw.rect(screen, close_color, close_rect, border_radius=6)
        
        # X mark
        x_color = (255, 255, 255) if close_hovered else (180, 180, 180)
        pg.draw.line(screen, x_color, 
                     (close_rect.x + 7, close_rect.y + 7),
                     (close_rect.right - 7, close_rect.bottom - 7), 2)
        pg.draw.line(screen, x_color,
                     (close_rect.right - 7, close_rect.y + 7),
                     (close_rect.x + 7, close_rect.bottom - 7), 2)
        
        # Draw cards with staggered animation
        for i, card in enumerate(self.cards):
            card_anim = max(0, self.open_animation - i * 0.05)
            if card_anim > 0:
                # Slide in from right
                original_x = card.base_rect.x
                card.rect.x = original_x + int((1 - card_anim) * 50)
                card.draw(screen)
                card.rect.x = original_x
        
        # Status message
        if self.status_message:
            status_text = self.status_font.render(self.status_message, True, self.status_color)
            status_rect = status_text.get_rect(centerx=panel_rect.centerx, y=panel_rect.bottom - 35)
            screen.blit(status_text, status_rect)
        
        # Hint
        hint_text = self.hint_font.render("ESC to close  |  Q to cancel navigation", True, (100, 110, 130))
        hint_rect = hint_text.get_rect(centerx=panel_rect.centerx, y=panel_rect.bottom - 18)
        screen.blit(hint_text, hint_rect)
    
    def _draw_path(self, screen: pg.Surface):
        """Draw the navigation path on screen."""
        if not self.game_manager.player:
            return
        
        camera = self.game_manager.player.camera
        
        # Draw path segments
        points = []
        for i in range(self.path_index, len(self.current_path)):
            tile_x, tile_y = self.current_path[i]
            screen_x = tile_x * GameSettings.TILE_SIZE - camera.x + GameSettings.TILE_SIZE // 2
            screen_y = tile_y * GameSettings.TILE_SIZE - camera.y + GameSettings.TILE_SIZE // 2
            points.append((int(screen_x), int(screen_y)))
        
        # Draw line
        if len(points) >= 2:
            pg.draw.lines(screen, (80, 180, 255), False, points, 3)
        
        # Draw animated dots
        pulse = (math.sin(self.path_pulse) + 1) / 2  # 0 to 1
        
        for i, (tile_x, tile_y) in enumerate(self.current_path[self.path_index:]):
            screen_x = tile_x * GameSettings.TILE_SIZE - camera.x + GameSettings.TILE_SIZE // 2
            screen_y = tile_y * GameSettings.TILE_SIZE - camera.y + GameSettings.TILE_SIZE // 2
            
            # Current target is bigger and pulses
            if i == 0:
                radius = int(6 + 2 * pulse)
                color = (100, 220, 255)
            else:
                radius = 4
                color = (80, 160, 220)
            
            pg.draw.circle(screen, color, (int(screen_x), int(screen_y)), radius)
            pg.draw.circle(screen, (255, 255, 255), (int(screen_x), int(screen_y)), radius, 1)
        
        # Draw destination marker
        if len(self.current_path) > 0:
            dest_x, dest_y = self.current_path[-1]
            screen_x = dest_x * GameSettings.TILE_SIZE - camera.x + GameSettings.TILE_SIZE // 2
            screen_y = dest_y * GameSettings.TILE_SIZE - camera.y + GameSettings.TILE_SIZE // 2
            
            # Pulsing destination marker
            marker_size = int(10 + 3 * pulse)
            
            # Outer glow
            glow_surf = pg.Surface((marker_size * 4, marker_size * 4), pg.SRCALPHA)
            pg.draw.circle(glow_surf, (100, 220, 255, 50), (marker_size * 2, marker_size * 2), marker_size * 2)
            screen.blit(glow_surf, (int(screen_x) - marker_size * 2, int(screen_y) - marker_size * 2))
            
            # Pin marker
            pg.draw.circle(screen, (255, 100, 100), (int(screen_x), int(screen_y) - 8), 8)
            pg.draw.polygon(screen, (255, 100, 100), [
                (int(screen_x), int(screen_y) + 5),
                (int(screen_x) - 5, int(screen_y) - 3),
                (int(screen_x) + 5, int(screen_y) - 3),
            ])
            pg.draw.circle(screen, (255, 255, 255), (int(screen_x), int(screen_y) - 8), 3)