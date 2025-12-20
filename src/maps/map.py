import pygame as pg
import pytmx

from src.utils import load_tmx, Position, GameSettings, PositionCamera, Teleport

class Map:
    # Map Properties
    path_name: str
    tmxdata: pytmx.TiledMap
    # Position Argument
    spawn: Position
    teleporters: list[Teleport]
    # Rendering Properties
    _surface: pg.Surface
    _collision_map: list[pg.Rect]
    _bush_map: list[pg.Rect]
    _water_map: list[pg.Rect]

    def __init__(self, path: str, tp: list[Teleport], spawn: Position):
        self.path_name = path
        self.tmxdata = load_tmx(path)
        self.spawn = spawn
        self.teleporters = tp

        pixel_w = self.tmxdata.width * GameSettings.TILE_SIZE
        pixel_h = self.tmxdata.height * GameSettings.TILE_SIZE

        # Prebake the map
        self._surface = pg.Surface((pixel_w, pixel_h), pg.SRCALPHA)
        self._render_all_layers(self._surface)
        # Prebake the collision map
        self._collision_map = self._create_collision_map()
        self._bush_map = self._create_bush_map()
        self._water_map = self._create_water_map()

    def update(self, dt: float):
        return

    def draw(self, screen: pg.Surface, camera: PositionCamera):
        screen.blit(self._surface, camera.transform_position(Position(0, 0)))
        
        # Draw the hitboxes collision map
        if GameSettings.DRAW_HITBOXES:
            for rect in self._collision_map:
                pg.draw.rect(screen, (255, 0, 0), camera.transform_rect(rect), 1)
            for rect in self._bush_map:
                pg.draw.rect(screen, (0, 255, 0), camera.transform_rect(rect), 1)
            for rect in self._water_map:
                pg.draw.rect(screen, (0, 0, 255), camera.transform_rect(rect), 1)

        
    def check_collision(self, rect: pg.Rect) -> bool:
        '''
        [TODO HACKATHON 4]
        Return True if collide if rect param collide with self._collision_map
        Hint: use API colliderect and iterate each rectangle to check
        '''
        for rectangle in self._collision_map:
            if rect.colliderect(rectangle):
                return True
        return False
    
    def check_water_collision(self, rect: pg.Rect) -> bool:
        """Check if rect collides with water tiles."""
        for water_rect in self._water_map:
            if rect.colliderect(water_rect):
                return True
        return False
        
    def check_teleport(self, pos: Position) -> Teleport | None:
        '''[TODO HACKATHON 6] 
        Teleportation: Player can enter a building by walking into certain tiles defined inside saves/*.json, and the map will be changed
        Hint: Maybe there is an way to switch the map using something from src/core/managers/game_manager.py called switch_... 
        '''
        for tp in self.teleporters:
            if pos.x // GameSettings.TILE_SIZE == tp.pos.x // GameSettings.TILE_SIZE and (pos.y-1) // GameSettings.TILE_SIZE == tp.pos.y // GameSettings.TILE_SIZE:
                return tp
            
        return None

    def _render_all_layers(self, target: pg.Surface) -> None:
        for layer in self.tmxdata.visible_layers:
            if isinstance(layer, pytmx.TiledTileLayer):
                self._render_tile_layer(target, layer)
            # elif isinstance(layer, pytmx.TiledImageLayer) and layer.image:
            #     target.blit(layer.image, (layer.x or 0, layer.y or 0))
 
    def _render_tile_layer(self, target: pg.Surface, layer: pytmx.TiledTileLayer) -> None:
        for x, y, gid in layer:
            if gid == 0:
                continue
            image = self.tmxdata.get_tile_image_by_gid(gid)
            if image is None:
                continue

            image = pg.transform.scale(image, (GameSettings.TILE_SIZE, GameSettings.TILE_SIZE))
            target.blit(image, (x * GameSettings.TILE_SIZE, y * GameSettings.TILE_SIZE))
    
    def _create_collision_map(self) -> list[pg.Rect]:
        rects = []
        for layer in self.tmxdata.layers:
            if isinstance(layer, pytmx.TiledTileLayer) and ("collision" in layer.name.lower() or "house" in layer.name.lower() or "border" in layer.name.lower()):
                for x, y, gid in layer:
                    if gid != 0:
                        '''
                        [TODO HACKATHON 4]
                        rects.append(pg.Rect(...))
                        Append the collision rectangle to the rects[] array
                        Remember scale the rectangle with the TILE_SIZE from settings
                        '''
                        rects.append(pg.Rect(x * GameSettings.TILE_SIZE, y * GameSettings.TILE_SIZE, GameSettings.TILE_SIZE, GameSettings.TILE_SIZE))
        return rects
    
    def _create_bush_map(self) -> list[pg.Rect]:
        rects = []
        for layer in self.tmxdata.visible_layers:
            if isinstance(layer, pytmx.TiledTileLayer) and ("pokemonbush" in layer.name.lower()):
                for x, y, gid in layer:
                    if gid != 0:
                        rects.append(pg.Rect(x * GameSettings.TILE_SIZE, y * GameSettings.TILE_SIZE, GameSettings.TILE_SIZE, GameSettings.TILE_SIZE))
        return rects
    
    def _create_water_map(self) -> list[pg.Rect]:
        """Create water tile collision map."""
        rects = []
        for layer in self.tmxdata.layers:
            if isinstance(layer, pytmx.TiledTileLayer) and ("water" in layer.name.lower() or "pond" in layer.name.lower() or "lake" in layer.name.lower() or "sea" in layer.name.lower()):
                for x, y, gid in layer:
                    if gid != 0:
                        rects.append(pg.Rect(x * GameSettings.TILE_SIZE, y * GameSettings.TILE_SIZE, GameSettings.TILE_SIZE, GameSettings.TILE_SIZE))
        return rects

    @classmethod
    def from_dict(cls, data: dict) -> "Map":
        tp = [Teleport.from_dict(t) for t in data["teleport"]]
        pos = Position(data["player"]["x"] * GameSettings.TILE_SIZE, data["player"]["y"] * GameSettings.TILE_SIZE)
        return cls(data["path"], tp, pos)

    def to_dict(self):
        return {
            "path": self.path_name,
            "teleport": [t.to_dict() for t in self.teleporters],
            "player": {
                "x": self.spawn.x // GameSettings.TILE_SIZE,
                "y": self.spawn.y // GameSettings.TILE_SIZE,
            }
        }

class Minimap:
    def __init__(self, world_width, world_height, map_surface, size=350, position=None):
        self.size = size
        self.world_width = world_width
        self.world_height = world_height
        self.scale_x = size / world_width
        self.scale_y = size / world_height
        
        # Create a surface for the minimap
        self.surface = pg.Surface((self.size, self.size), pg.SRCALPHA)
        
        # Scale down the entire map to fit the minimap
        self.map_thumbnail = pg.transform.smoothscale(map_surface, (self.size, self.size))
        
        # Allow custom positioning, default to top-left
        if position is None:
            position = (20, 20)
        self.rect = self.surface.get_rect(topleft=position)

    def draw(self, screen, player_pos, entities=None):
        # 1. Draw the scaled-down map as background
        self.surface.blit(self.map_thumbnail, (0, 0))
        
        # 2. Add a semi-transparent dark overlay for better visibility
        dark_overlay = pg.Surface((self.size, self.size), pg.SRCALPHA)
        dark_overlay.fill((0, 0, 0, 80))  # Slight darkening for contrast
        self.surface.blit(dark_overlay, (0, 0))
        
        # 3. Draw entities (enemies, online players, etc.)
        if entities:
            for entity in entities:
                # Calculate scaled position with bounds checking
                ent_x = max(0, min(self.size - 1, entity.pos.x * self.scale_x))
                ent_y = max(0, min(self.size - 1, entity.pos.y * self.scale_y))
                
                # Use entity color if available, otherwise default to red
                color = getattr(entity, 'color', (255, 0, 0))
                # Draw outer glow
                pg.draw.circle(self.surface, (*color[:3], 100), (int(ent_x), int(ent_y)), 4)
                # Draw inner dot
                pg.draw.circle(self.surface, color, (int(ent_x), int(ent_y)), 2)
        
        # 4. Draw Player Indication (on top of entities)
        # Calculate scaled position with bounds checking
        mini_x = max(0, min(self.size - 1, player_pos.x * self.scale_x))
        mini_y = max(0, min(self.size - 1, player_pos.y * self.scale_y))
        
        # Draw a glowing dot for the player with better visibility
        pg.draw.circle(self.surface, (100, 255, 100), (int(mini_x), int(mini_y)), 5)  # Outer glow
        pg.draw.circle(self.surface, (0, 255, 0), (int(mini_x), int(mini_y)), 3)      # Middle
        pg.draw.circle(self.surface, (200, 255, 200), (int(mini_x), int(mini_y)), 1)  # Center highlight
        
        # 5. Draw to main screen
        screen.blit(self.surface, self.rect)
        
        # 6. Draw border
        pg.draw.rect(screen, (255, 255, 255), self.rect, 2)