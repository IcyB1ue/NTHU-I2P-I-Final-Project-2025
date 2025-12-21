import pygame as pg
import random
import math

from src.scenes.scene import Scene
from src.core import GameManager, OnlineManager
from src.utils import Logger, PositionCamera, GameSettings, Position
from src.core.managers.time_event_manager import TimeEventManager, TimeEvent
from src.core.services import sound_manager, input_manager, scene_manager
from src.sprites import Sprite, Text, Animation
from typing import override, Any
from src.interface.components.button import Button
from src.interface.components.toggle_button import ToggleButton
from src.interface.components.slider import Slider
from src.interface.shop_ui import ShopUI
from src.interface.navigation_ui import NavigationUI
from src.interface.components.chat_overlay import ChatOverlay
from src.entities.enemy_trainer import EnemyTrainer
from src.entities.shopkeeper import ShopEntity, ShopItem
from src.maps.map import Minimap

from src.core.managers.tutorial_manager import TutorialManager, TutorialQuest

# Water Gym Puzzle System imports
from src.puzzles.puzzle_ui import PuzzleUI
from src.puzzles.water_gym_manager import WaterGymManager, WaterGymState
from src.interface.professor_dialog import ProfessorDialog
from src.interface.quest_ui import QuestUI
from src.interface.pc_ui import PCUI
from src.interface.coding_quiz_ui import CodingQuizUI
from src.interface.game_menu_ui import GameMenuUI
from src.interface.pokedex_ui import PokedexUI
from src.interface.achievements_ui import AchievementsUI
from src.interface.evolution_ui import EvolutionUI
from src.entities.professor_npc import ProfessorNPC
from src.entities.ghost_gengar import GhostGengar
from src.scenes.battle_scene import last_battle_result, get_need_professor_heal_dialog_battle, get_pending_evolution
from src.scenes.wild_pokemon_scene import set_need_water_pokemon, set_water_pokemon_blocked, get_need_professor_heal_dialog
from src.utils.definition import evolve_monster


class OnlinePlayerSprite:
    """Handles rendering of online players with proper animations."""
    
    def __init__(self):
        self.animation = Animation(
            "character/ow1.png", ["down", "left", "right", "up"], 4,
            (GameSettings.TILE_SIZE, GameSettings.TILE_SIZE)
        )
        self._current_direction = "down"
        self._is_moving = False
        self._idle_frame_shown = False
    
    def update(self, dt: float, direction: str, is_moving: bool, position: Position):
        """Update animation based on direction and movement state."""
        self.animation.rect.topleft = (round(position.x), round(position.y))
        
        if direction in ["down", "left", "right", "up"]:
            if direction != self._current_direction:
                self.animation.switch(direction)
                self._current_direction = direction
        
        self._is_moving = is_moving
        
        if is_moving:
            self.animation.update(dt)
            self._idle_frame_shown = False
        else:
            if not self._idle_frame_shown:
                self.animation.accumulator = 0
                self._idle_frame_shown = True
    
    def draw(self, screen: pg.Surface, camera: PositionCamera):
        """Draw the online player with camera transformation."""
        self.animation.draw(screen, camera)


class GameScene(Scene):
    game_manager: GameManager
    online_manager: OnlineManager | None
    online_player_sprites: dict[int, OnlinePlayerSprite]
    minimap: Minimap | None
    shop_ui: ShopUI
    navigation_ui: NavigationUI
    chat_overlay: ChatOverlay | None
    player_name: str
    

    def __init__(self):
        super().__init__()
        manager = GameManager.load("saves/game0.json")
        if manager is None:
            Logger.error("Failed to load game manager")
            exit(1)
        self.game_manager = manager
        self.setting: Settings = Settings(self.game_manager)
        self.game_manager.bag.reload_bag()
        
        self.shop_ui = ShopUI()
        self.navigation_ui = NavigationUI(self.game_manager)

        self.current_map_path = self.game_manager.current_map.path_name if self.game_manager.current_map else None
        self.previous_map_path = None  # Track previous map for tutorial triggers

        self.online_manager = OnlineManager() if GameSettings.IS_ONLINE else None
        self.online_player_sprites = {}
        
        if self.online_manager:
            self.chat_overlay = ChatOverlay(
                send_callback=self._send_chat_message,
                get_messages=self._get_chat_messages
            )
        else:
            self.chat_overlay = None

        self.minimap = None
        self._init_minimap()
        
        # Player name (set from intro scene)
        self.player_name = "Player"

        px, py = GameSettings.SCREEN_WIDTH // 2, GameSettings.SCREEN_HEIGHT * 3 // 4
        self.bag_button = Button(
            "UI/button_backpack.png", "UI/button_backpack_hover.png",
            px + 500, py - 500, 75, 75,
            lambda: manager.bag.open()
        )
        self.settings_button = Button(
            "UI/button_setting.png", "UI/button_setting_hover.png",
            px + 500, py - 400, 75, 75,
            lambda: self.setting.open()
        )
        # Menu button (opens game menu with Navigation and Pokedex)
        self.menu_button = Button(
            "UI/button_play.png", "UI/button_play_hover.png",
            px + 500, py - 300, 75, 75,
            lambda: self.game_menu_ui.open()
        )
        
        # Pokedex UI
        self.pokedex_ui = PokedexUI(
            get_captured_pokemon=self._get_captured_pokemon_names
        )
        
        # Achievements UI
        self.achievements_ui = AchievementsUI(
            get_unlocked_badges=self._get_unlocked_badges,
            get_unlocked_achievements=self._get_unlocked_achievements
        )
        
        # Evolution UI
        self.evolution_ui = EvolutionUI(
            on_complete=self._on_evolution_complete
        )
        self._pending_evolution_monster = None  # Store monster for evolution completion
        
        # Game Menu UI (Navigation + Pokedex + Achievements selector)
        self.game_menu_ui = GameMenuUI(
            on_navigation=lambda: self.navigation_ui.open(),
            on_pokedex=lambda: self.pokedex_ui.open(),
            on_achievements=lambda: self.achievements_ui.open(),
            is_on_main_map=lambda: self.game_manager.current_map.path_name == "map.tmx"
        )

        # ============== TUTORIAL SYSTEM ==============
        self.tutorial_manager = TutorialManager()
        self.tutorial_manager.on_dialogue_request = self._show_professor_dialogue
        self.tutorial_manager.on_quest_complete = self._on_quest_complete
        
        # Professor dialog UI
        self.professor_dialog = ProfessorDialog()
        
        # Quest UI
        self.quest_ui = QuestUI()
        
        # PC UI
        self.pc_ui = PCUI()
        
        # Coding Quiz UI (professor minigame)
        self.coding_quiz_ui = CodingQuizUI(on_complete=self._on_quiz_complete)
        
        # Professor NPC for minigame (positioned to the left of house on map.tmx)
        # Position will be set when on map.tmx - approximately 3 tiles left of house entrance
        self.professor_npc: ProfessorNPC | None = None
        self._setup_professor_npc()
        
        # Night/Gengar system
        self.gengars: list[GhostGengar] = []
        self.midnight_merchant: ShopEntity | None = None
        self.is_night = False
        self.night_overlay_alpha = 0
        self.day_overlay_color = (0, 0, 0)  # Current overlay RGB
        
        # Day/night cycle (after tutorial)
        self.day_night_cycle_enabled = False
        self.time_of_day = 8.0  # Start at 8 AM (0-24 hours)
        self.day_cycle_speed = 0.1  # Hours per real second (0.1 = 1 game hour per 10 real seconds)
        
        # Initialize Time Event Manager
        self.time_event_manager = TimeEventManager(self)
        self._init_time_events()

        
        # Day phase constants
        # DAWN: 5:00 - 7:00 (orange/pink tint)
        # DAY: 7:00 - 18:00 (no tint)
        # DUSK: 18:00 - 20:00 (orange/red tint)
        # NIGHT: 20:00 - 5:00 (dark blue tint + Gengars)
        
        # Track if tutorial has started
        self.tutorial_started = False
        
        # Teleport cooldown to prevent teleporting right after dialogue
        self.teleport_cooldown = 0.0
        
        # Track monster count to detect new catches
        self.last_monster_count = len(self.game_manager.bag._monsters_data)
        
        # Track position when leaving house for delayed dialogue
        self.left_house_position: Position | None = None
        self.waiting_for_distance = False
        self.distance_to_walk = 3 * GameSettings.TILE_SIZE  # Walk 3 tiles before dialogue
        
        # Portal at southeast corner (59-61, 31-32) after Fire Gym - leads to Water World
        self.tree_removed = False
        self.pending_tree_dialogue = False
        # Water tiles that appear when tree is removed (6 tiles: 3 wide x 2 tall)
        # Visual tiles are at y=31,32 but teleport triggers at y=30,31 (one tile higher)
        self.water_tiles = [(59, 31), (59, 32), (60, 31), (60, 32), (61, 31), (61, 32)]
        # Teleporter positions to Water World (at x=61)
        self.water_world_teleport_tiles = [(61, 30), (61, 31)]
        # Return teleporter positions from Water World back to main map (at x=0, y=19-22)
        self.water_world_return_tiles = [(0, 19), (0, 20), (0, 21), (0, 22)]
        self.water_world_teleport_active = False
        
        # Water world transition effect
        self.water_transition_blackout = 0  # 0-255 alpha for blackout
        self.water_transition_active = False
        self.water_transition_delay = 0  # Delay before teleporting
        self.water_transition_teleporting = False
        self.water_transition_returning = False  # True when returning from water world
        
        # ============== WATER GYM PUZZLE SYSTEM ==============
        self.water_gym_manager: WaterGymManager | None = None
        self.puzzle_ui: PuzzleUI | None = None
        self.puzzle_active = False
        self.water_gym_night_triggered = False
        self._water_gym_wait_timer = 0.0
        self._puzzle_paused = False  # True when puzzle is paused for wild encounter
        self._puzzle_resume_x = 0
        self._puzzle_resume_y = 0
        
        # Water gym spawn tracking (for delayed dialogue)
        self.water_gym_spawn_pos: Position | None = None
        self.water_gym_entry_dialogue_shown = False
        
        # ============== HOSPITAL REST SYSTEM ==============
        self.hospital_rest_timer = 0.0
        self.hospital_rest_phase = 0  # 0=not resting, 1=waiting, 2=fade to black, 3=hold black, 4=fade out, 5=dialogue
        self.hospital_blackout_alpha = 0
        self.hospital_rest_started = False
        self._pending_hospital_transition = False  # Flag to transition to hospital after Misty dialogue
        self._hospital_transition_phase = 0  # 0=waiting for dialogue, 1=fade to black, 2=teleport, 3=fade in
        self._hospital_transition_alpha = 0
        
        # Water World spawn tracking (for walk-away dialogue trigger)
        self.water_world_spawn_pos: Position | None = None
        self.water_world_walk_triggered = False
        
        # ============== CORRUPTED BATTLE & ENDING ==============
        self.corrupted_battle_pending = False
        self.corrupted_trainer_moved = False
        self.water_badge_received = False
        self.ending_sequence_active = False
        self.ending_phase = 0  # 0=not active, 1=teleporting, 2=fade to black, 3=show text
        self.ending_blackout_alpha = 0
        self.ending_text_shown = False
        
        # Dialogue tracking to prevent repeats
        self.shown_dialogues: set[str] = set()

    # ============== TUTORIAL METHODS ==============
    
    def _show_professor_dialogue(self, dialogues: list[str]):
        """Show professor dialogue."""
        self.professor_dialog.show(dialogues)
    
    def _on_quest_complete(self, quest: TutorialQuest):
        """Handle quest completion."""
        Logger.info(f"Quest completed: {quest.name}")
        
        if quest == TutorialQuest.SURVIVE_THE_NIGHT:
            # Give rewards
            self.game_manager.bag.add_item("Pokeball", 5, "ingame_ui/ball.png")
            self.game_manager.bag.add_item("Gengar Repeller", 1, "ingame_ui/repeller.png")
            self.gengars.clear()
            self.is_night = False
            # Enable day/night cycle after this quest
            self.day_night_cycle_enabled = True
        
        elif quest == TutorialQuest.FIGHT_FIRE_GYM:
            # Only open portal if player actually WON the fire gym
            if self.tutorial_manager.fire_gym_won:
                # Mark tree as removed and set pending dialogue
                self.tree_removed = True
                self.pending_tree_dialogue = True
                self.water_world_teleport_active = True
                
                # Remove collision at all water tile positions
                for tile_x, tile_y in self.water_tiles:
                    self.game_manager.remove_collision_tile("map.tmx", tile_x, tile_y)
                
                Logger.info("Fire Gym WON - Portal will open!")
            else:
                # Lost - water pokemon spawns enabled for catch quest
                set_water_pokemon_blocked(False)
                set_need_water_pokemon(True)
                Logger.info("Fire Gym lost - starting water pokemon quest")
        
        elif quest == TutorialQuest.CATCH_WATER_POKEMON:
            # Caught water Pokemon, no longer need guaranteed spawns
            set_need_water_pokemon(False)
        
        elif quest == TutorialQuest.WATER_WALKING:
            # Tutorial complete
            pass
    
    def _spawn_gengars(self):
        """Spawn Gengars for night time."""
        self.gengars.clear()
        
        if not self.game_manager.player:
            return
        
        player_x = self.game_manager.player.position.x / GameSettings.TILE_SIZE
        player_y = self.game_manager.player.position.y / GameSettings.TILE_SIZE
        
        # Spawn LOTS of Gengars (15-25) in a larger area around the player
        num_gengars = random.randint(15, 25)
        
        for i in range(num_gengars):
            # Spawn at varying distances - some close, some far
            if i < 5:
                # Close gengars (8-12 tiles away)
                dist = random.randint(8, 12)
            elif i < 12:
                # Medium distance (12-20 tiles away)
                dist = random.randint(12, 20)
            else:
                # Far gengars (20-30 tiles away)
                dist = random.randint(20, 30)
            
            # Random angle
            angle = random.random() * 6.28
            
            x = player_x + math.cos(angle) * dist
            y = player_y + math.sin(angle) * dist
            
            self.gengars.append(GhostGengar(x, y))
        
        Logger.info(f"Spawned {len(self.gengars)} Gengars!")
    
    def _on_gengar_caught_player(self):
        """Called when a Gengar catches the player."""
        # Steal a random item (not Pokemon or Coins)
        items = self.game_manager.bag.items
        stealable = [item for item in items if item["name"] not in ["Coins", "Gengar Repeller"] and item["count"] > 0]
        
        if stealable:
            stolen = random.choice(stealable)
            self.game_manager.bag.remove_item(stolen["name"])
            self._show_professor_dialogue([f"Oh no! A Gengar stole your {stolen['name']}!", "Keep moving! Don't let them catch you again!"])
            Logger.info(f"Gengar stole: {stolen['name']}")
        else:
            self._show_professor_dialogue(["The Gengar tried to steal something, but you had nothing to take!", "Lucky you! Keep moving!"])
        
        # Give ALL gengars a cooldown so player has time to escape
        for gengar in self.gengars:
            gengar.reset_catch_cooldown(4.0)  # 4 seconds of immunity
    
    def _check_map_transition_tutorial(self):
        """Check if player is transitioning maps and trigger tutorial."""
        if self.previous_map_path == "home.tmx" and self.current_map_path == "map.tmx":
            if not self.tutorial_manager.has_left_house:
                # Don't show dialogue immediately - wait for player to walk away
                self.waiting_for_distance = True
                if self.game_manager.player:
                    self.left_house_position = Position(
                        self.game_manager.player.position.x,
                        self.game_manager.player.position.y
                    )
                Logger.info("Player left house, waiting for them to walk away before dialogue...")
    
    def _check_distance_from_house(self):
        """Check if player has walked far enough from the house to trigger dialogue."""
        if not self.waiting_for_distance or not self.left_house_position:
            return
        
        if not self.game_manager.player:
            return
        
        # Calculate distance from where they exited
        dx = self.game_manager.player.position.x - self.left_house_position.x
        dy = self.game_manager.player.position.y - self.left_house_position.y
        distance = (dx * dx + dy * dy) ** 0.5
        
        if distance >= self.distance_to_walk:
            # Player has walked far enough, trigger the dialogue
            self.waiting_for_distance = False
            self.left_house_position = None
            self.tutorial_manager.on_left_house()
            Logger.info("Player walked far enough, triggering tutorial dialogue!")
    
    def _has_water_pokemon(self) -> bool:
        """Check if player has a water type Pokemon."""
        for monster in self.game_manager.bag._monsters_data:
            if monster.get("element") == "Water":
                return True
        return False
    
    def _is_gengar_chase_active(self) -> bool:
        """Check if we're in the Gengar chase phase."""
        return (self.tutorial_manager.current_quest == TutorialQuest.SURVIVE_THE_NIGHT and 
                self.is_night and 
                len(self.gengars) > 0)
    
    def _can_encounter_wild_pokemon(self) -> bool:
        """Check if wild Pokemon encounters are allowed."""
        # Disable during Gengar chase
        if self._is_gengar_chase_active():
            return False
        return True
    
    def _update_day_night_cycle(self, dt: float):
        """Update day/night cycle after tutorial."""
        if not self.day_night_cycle_enabled:
            return
        
        # Check if player has Gengar Repeller
        has_repeller = self.game_manager.bag.has_item("Gengar Repeller")
        
        # Update time
        self.time_of_day += self.day_cycle_speed * dt
        if self.time_of_day >= 24.0:
            self.time_of_day -= 24.0
            
        # Update Time Events
        self.time_event_manager.update(self.time_of_day, dt)

        
        # Calculate smooth overlay based on time using sine-like curve
        # Peak darkness at midnight (0:00), peak brightness at noon (12:00)
        hour = self.time_of_day
        
        # Use cosine function for smooth day/night transition
        # cos(0) = 1 at midnight, cos(pi) = -1 at noon
        # Shift and scale to get: 1 at midnight, 0 at noon
        darkness = (math.cos((hour / 24.0) * 2 * math.pi) + 1) / 2.0
        
        # Apply gamma curve to make transitions feel more natural
        # This makes dawn/dusk transitions more gradual
        darkness = darkness ** 1.5
        
        # Calculate overlay color based on time
        if 5.0 <= hour < 7.0:
            # DAWN - blend from night blue to orange/pink
            progress = (hour - 5.0) / 2.0
            r = int(20 + (255 - 20) * progress)
            g = int(20 + (140 - 20) * progress)
            b = int(80 + (80 - 80) * progress)
            self.day_overlay_color = (r, g, b)
        elif 7.0 <= hour < 8.0:
            # Early morning - fade out dawn color
            progress = hour - 7.0
            self.day_overlay_color = (
                int(255 * (1 - progress)),
                int(140 * (1 - progress)),
                int(80 * (1 - progress))
            )
        elif 8.0 <= hour < 17.0:
            # Full day - no tint
            self.day_overlay_color = (0, 0, 0)
        elif 17.0 <= hour < 18.0:
            # Late afternoon - start orange tint
            progress = hour - 17.0
            self.day_overlay_color = (
                int(255 * progress),
                int(140 * progress),
                int(60 * progress)
            )
        elif 18.0 <= hour < 20.0:
            # DUSK - blend from orange to night blue
            progress = (hour - 18.0) / 2.0
            r = int(255 + (20 - 255) * progress)
            g = int(140 + (20 - 140) * progress)
            b = int(60 + (80 - 60) * progress)
            self.day_overlay_color = (r, g, b)
        else:
            # NIGHT - dark blue
            self.day_overlay_color = (20, 20, 80)
        
        # Set alpha based on smooth darkness function
        # Max alpha of 160 at night, 0 during midday
        self.night_overlay_alpha = int(darkness * 160)
        
        # Determine if it's night for Gengar spawning (20:00 - 5:00)
        is_night_time = hour >= 20.0 or hour < 5.0
        
        if is_night_time and not has_repeller:
            self.is_night = True
            if not self.gengars:
                self._spawn_gengars()
        else:
            self.is_night = False
            self.gengars.clear()
    
    def _get_time_of_day_string(self) -> str:
        """Get formatted time string (HH:MM)."""
        hours = int(self.time_of_day)
        minutes = int((self.time_of_day % 1) * 60)
        return f"{hours:02d}:{minutes:02d}"
    
    def _get_day_phase_string(self) -> str:
        """Get current day phase as string."""
        hour = self.time_of_day
        if 5.0 <= hour < 7.0:
            return "Dawn"
        elif 7.0 <= hour < 18.0:
            return "Day"
        elif 18.0 <= hour < 20.0:
            return "Dusk"
        else:
            return "Night"
    
    def _draw_time_display(self, screen: pg.Surface):
        """Draw the time of day display in the bottom-left corner."""
        try:
            time_font = pg.font.Font("assets/fonts/Minecraft.ttf", 16)
            phase_font = pg.font.Font("assets/fonts/Minecraft.ttf", 12)
        except:
            time_font = pg.font.Font(None, 20)
            phase_font = pg.font.Font(None, 16)
        
        time_str = self._get_time_of_day_string()
        phase_str = self._get_day_phase_string()
        
        # Get phase color
        phase_colors = {
            "Dawn": (255, 180, 100),    # Orange
            "Day": (255, 255, 150),      # Yellow
            "Dusk": (255, 130, 80),      # Red-orange
            "Night": (150, 150, 255)     # Blue
        }
        phase_color = phase_colors.get(phase_str, (255, 255, 255))
        
        # Draw background panel - BOTTOM LEFT
        panel_width = 90
        panel_height = 45
        panel_x = 10
        panel_y = GameSettings.SCREEN_HEIGHT - panel_height - 10
        
        # Semi-transparent background
        panel_surface = pg.Surface((panel_width, panel_height), pg.SRCALPHA)
        panel_surface.fill((30, 30, 40, 180))
        screen.blit(panel_surface, (panel_x, panel_y))
        
        # Border
        pg.draw.rect(screen, (60, 60, 80), (panel_x, panel_y, panel_width, panel_height), 2, border_radius=5)
        
        # Draw sun/moon icon
        icon_x = panel_x + 12
        icon_y = panel_y + panel_height // 2
        
        if phase_str == "Night":
            # Moon icon (crescent)
            pg.draw.circle(screen, (200, 200, 255), (icon_x, icon_y), 8)
            pg.draw.circle(screen, (30, 30, 40), (icon_x + 4, icon_y - 2), 7)
        elif phase_str == "Dusk" or phase_str == "Dawn":
            # Half sun
            pg.draw.circle(screen, (255, 180, 80), (icon_x, icon_y + 4), 8)
            pg.draw.rect(screen, (30, 30, 40), (icon_x - 10, icon_y + 4, 20, 10))
        else:
            # Full sun
            pg.draw.circle(screen, (255, 220, 100), (icon_x, icon_y), 8)
            # Sun rays
            for angle in range(0, 360, 45):
                rad = math.radians(angle)
                x1 = icon_x + int(10 * math.cos(rad))
                y1 = icon_y + int(10 * math.sin(rad))
                x2 = icon_x + int(13 * math.cos(rad))
                y2 = icon_y + int(13 * math.sin(rad))
                pg.draw.line(screen, (255, 220, 100), (x1, y1), (x2, y2), 2)
        
        # Draw time text
        time_text = time_font.render(time_str, True, (255, 255, 255))
        screen.blit(time_text, (panel_x + 28, panel_y + 5))
        
        # Draw phase text
        phase_text = phase_font.render(phase_str, True, phase_color)
        screen.blit(phase_text, (panel_x + 28, panel_y + 25))
    
    def _check_new_pokemon_caught(self):
        """Check if player caught a new Pokemon and notify tutorial."""
        monsters = self.game_manager.bag._monsters_data
        current_monster_count = len(monsters)
        
        if current_monster_count > self.last_monster_count:
            # Find all new Pokemon
            for i in range(self.last_monster_count, current_monster_count):
                new_monster = monsters[i]
                monster_name = new_monster.get("name", "Unknown")
                monster_element = new_monster.get("element", "Normal")
                
                Logger.info(f"New Pokemon detected: {monster_name} ({monster_element})")
                
                self.tutorial_manager.on_pokemon_caught(monster_name, monster_element)
            
            # Update count AFTER checking
            self.last_monster_count = current_monster_count
    
    def _check_trainer_battle_result(self):
        """Check if player won/lost a trainer battle and notify tutorial."""
        global last_battle_result
        
        if not last_battle_result["was_trainer_battle"]:
            return
        
        # Check if this is the Fire Gym quest AND it was actually a gym leader battle
        if self.tutorial_manager.current_quest == TutorialQuest.FIGHT_FIRE_GYM:
            # Only trigger fire gym logic if it was actually a gym leader
            if last_battle_result.get("is_gym_leader", False):
                if last_battle_result["player_won"]:
                    Logger.info("Player won against Fire Gym Leader!")
                    self.tutorial_manager.on_fire_gym_won()
                else:
                    Logger.info("Player lost to Fire Gym Leader!")
                    self.tutorial_manager.on_fire_gym_lost()
                    # Enable water pokemon spawns for catch quest
                    set_water_pokemon_blocked(False)
                    set_need_water_pokemon(True)
                    Logger.info("Water pokemon spawns enabled!")
                
                # Reset the flags
                last_battle_result["was_trainer_battle"] = False
                last_battle_result["player_won"] = False
                last_battle_result["is_gym_leader"] = False
                return
            # If not a gym leader, fall through to regular trainer logic
        
        # Check if this is the corrupted trainer battle
        if self.tutorial_manager.current_quest == TutorialQuest.FIGHT_CORRUPTED:
            if last_battle_result.get("is_corrupted", False):
                if last_battle_result["player_won"]:
                    Logger.info("Player won against Corrupted Trainer!")
                    self._on_corrupted_battle_won()
                else:
                    Logger.info("Player lost to Corrupted Trainer - try again!")
                    self._show_professor_dialogue([
                        "The corrupted shadow is too powerful!",
                        "Heal your Pokemon and try again!"
                    ])
                
                # Reset the flags
                last_battle_result["was_trainer_battle"] = False
                last_battle_result["player_won"] = False
                last_battle_result["is_corrupted"] = False
                return
        
        # Regular trainer battle (for FIGHT_FIRST_TRAINER quest or any other trainer)
        if last_battle_result["player_won"]:
            Logger.info("Player won a trainer battle! Notifying tutorial...")
            self.tutorial_manager.on_trainer_defeated()
        
        # Reset the flags
        last_battle_result["was_trainer_battle"] = False
        last_battle_result["player_won"] = False
        last_battle_result["is_gym_leader"] = False
    
    def _check_water_crossing(self):
        """Check if player just crossed water for tutorial."""
        if not self.game_manager.player:
            return
        
        if hasattr(self.game_manager.player, 'just_entered_water') and self.game_manager.player.just_entered_water:
            if self.tutorial_manager.current_quest == TutorialQuest.WATER_WALKING:
                Logger.info("Player crossed water! Completing water walking quest.")
                self.tutorial_manager.on_water_crossed()
    
    def _check_water_world_teleport(self):
        """Check if player is in water transition zone and handle blackout effect."""
        if not self.game_manager.player:
            return
        
        if not self.water_world_teleport_active:
            self.water_transition_blackout = 0
            return
        
        # Only check on main map
        if self.current_map_path != "map.tmx":
            return
        
        # If we're in teleporting state, don't do anything else
        if self.water_transition_teleporting:
            return
        
        # Get player tile position
        player_tile_x = int(self.game_manager.player.position.x // GameSettings.TILE_SIZE)
        player_tile_y = int(self.game_manager.player.position.y // GameSettings.TILE_SIZE)
        
        # Check if player is in the water zone (y = 30 or 31, x = 59-61)
        if (player_tile_y == 30 or player_tile_y == 31) and 59 <= player_tile_x <= 61:
            self.water_transition_active = True
            
            # Calculate blackout based on x position (59 = 0%, 61 = 100%)
            # Use actual pixel position for smoother transition
            player_x = self.game_manager.player.position.x
            start_x = 59 * GameSettings.TILE_SIZE
            end_x = 61 * GameSettings.TILE_SIZE
            
            if player_x >= start_x:
                progress = (player_x - start_x) / (end_x - start_x)
                progress = min(1.0, max(0.0, progress))
                self.water_transition_blackout = int(255 * progress)
            
            # Check if player reached teleporter (x = 61, y = 30 or 31)
            if player_tile_x == 61 and (player_tile_y == 30 or player_tile_y == 31):
                Logger.info("Player reached water world teleporter - starting transition!")
                self.water_transition_blackout = 255
                self.water_transition_delay = 1.0  # 1 second delay
                self.water_transition_teleporting = True
        else:
            # Player left the water zone without teleporting
            if self.water_transition_active and not self.water_transition_teleporting:
                self.water_transition_blackout = max(0, self.water_transition_blackout - 10)
                if self.water_transition_blackout == 0:
                    self.water_transition_active = False
    
    def _check_water_world_return_teleport(self):
        """Check if player is at return teleporter in water world."""
        if not self.game_manager.player:
            return
        
        # Only check on water map
        if self.current_map_path != "water_map.tmx":
            return
        
        # If we're already in teleporting state, don't check again
        if self.water_transition_teleporting:
            return
        
        # Get player tile position
        player_tile_x = int(self.game_manager.player.position.x // GameSettings.TILE_SIZE)
        player_tile_y = int(self.game_manager.player.position.y // GameSettings.TILE_SIZE)
        
        # Check if player is at return teleporter (x=0, y=19-22)
        if player_tile_x == 0 and 19 <= player_tile_y <= 22:
            Logger.info("Player reached return teleporter - going back to main map!")
            self.water_transition_blackout = 255
            self.water_transition_delay = 1.0
            self.water_transition_teleporting = True
            self.water_transition_returning = True  # Flag for return trip
    
    def _update_water_transition(self, dt: float):
        """Update water world transition delay and teleport."""
        if self.water_transition_teleporting:
            self.water_transition_delay -= dt
            
            if self.water_transition_delay <= 0:
                if self.water_transition_returning:
                    self._teleport_to_main_world()
                    self.water_transition_returning = False
                else:
                    self._teleport_to_water_world()
                self.water_transition_teleporting = False
                self.water_transition_active = False
                # Keep screen black briefly, then fade out
                self.water_transition_blackout = 255
        
        # Fade out blackout when not in transition and not on main map in water zone
        elif self.water_transition_blackout > 0 and not self.water_transition_active:
            self.water_transition_blackout = max(0, self.water_transition_blackout - 200 * dt)
    
    def _teleport_to_water_world(self):
        """Teleport to Water World briefly, show 'To.. Be.. Continued..' and return to menu."""
        Logger.info("Water World portal activated - teleporting briefly then showing ending")
        
        # Actually teleport to water world first
        if "water_map.tmx" in self.game_manager.maps:
            self.game_manager.switch_map("water_map.tmx")
            
            # Set player position in water world (2, 21)
            if self.game_manager.player:
                self.game_manager.player.position.x = 2 * GameSettings.TILE_SIZE
                self.game_manager.player.position.y = 21 * GameSettings.TILE_SIZE
            
            # Force immediate map switch
            self.game_manager.try_switch_map()
            self.current_map_path = "water_map.tmx"
            self._handle_map_change()
            
            Logger.info("Teleported to Water World!")
        
        # Trigger the ending sequence (starts with brief view, then fade to black)
        self.ending_sequence_active = True
        self.ending_phase = 1  # Start from phase 1 (brief view of water world)
        self.ending_blackout_alpha = 0
        self.ending_timer = 0.0  # Timer for showing text before returning to menu
        
        # Reset the water transition state
        self.water_transition_blackout = 0
        self.water_transition_active = False
        self.water_transition_teleporting = False
    
    def _teleport_to_main_world(self):
        """Teleport player back to main map from Water World."""
        # Use the game's map switching system
        self.game_manager.switch_map("map.tmx")
        
        # Set player position back on main map (58, 31) - just outside the portal
        self.game_manager.player.position.x = 58 * GameSettings.TILE_SIZE
        self.game_manager.player.position.y = 31 * GameSettings.TILE_SIZE
        
        # Force immediate map switch
        self.game_manager.try_switch_map()
        self.current_map_path = "map.tmx"
        self._handle_map_change()
        
        Logger.info("Teleported back to Main World!")
        
        # Show return message
        self._show_professor_dialogue([
            "You've returned from the Water World!",
            "I hope you found some interesting Water-type Pokemon there.",
            "The portal will remain open if you wish to return."
        ])

    # ============== WATER GYM PUZZLE METHODS ==============
    
    def _init_water_gym_manager(self):
        """Initialize the Water Gym manager when entering water_gym.tmx."""
        if self.water_gym_manager is None:
            self.water_gym_manager = WaterGymManager()
            self.water_gym_manager.on_dialogue = self._show_professor_dialogue
            self.water_gym_manager.on_state_change = self._on_water_gym_state_change
            
            # Create puzzle UI with game_manager reference
            self.puzzle_ui = PuzzleUI(self.game_manager)
            
            Logger.info("Water Gym Manager initialized")
    
    def _on_water_gym_state_change(self, new_state: WaterGymState):
        """Handle water gym state changes."""
        Logger.info(f"Water Gym state changed to: {new_state.name}")
        
        if new_state == WaterGymState.SNEAK_MODE:
            # Player can now sneak - notify tutorial
            self.tutorial_manager.on_night_in_water_world()
    
    def _check_water_gym_puzzle_zone(self):
        """Check if player entered the puzzle zone in the water gym."""
        if not self.water_gym_manager or not self.game_manager.player:
            return
        
        if self.current_map_path != "water_gym.tmx":
            return
        
        # Don't check if puzzle is already active
        if self.puzzle_active:
            return
        
        # Only allow puzzle during sneak mode (night)
        if self.water_gym_manager.state != WaterGymState.SNEAK_MODE:
            return
        
        # Get player tile position
        player_tile_x = int(self.game_manager.player.position.x // GameSettings.TILE_SIZE)
        player_tile_y = int(self.game_manager.player.position.y // GameSettings.TILE_SIZE)
        
        # Check if player is entering puzzle area (row 41 going up into puzzle zone rows 14-41)
        # Puzzle zone: x=2-24, y=14-41
        if 2 <= player_tile_x <= 24 and player_tile_y <= 41 and player_tile_y >= 14:
            # Check if puzzle not already completed
            if not self.water_gym_manager.puzzles_completed.get(1, False):
                self._start_puzzle()
    
    def _start_puzzle(self):
        """Start the Undertale-style colored tile puzzle."""
        # Initialize puzzle UI if needed
        if self.puzzle_ui is None:
            self.puzzle_ui = PuzzleUI(self.game_manager)
        
        # ALWAYS set callbacks (they might have been lost)
        self.puzzle_ui.on_puzzle_complete = self._on_puzzle_ui_complete
        self.puzzle_ui.on_damage = self._on_puzzle_damage
        self.puzzle_ui.on_encounter = self._on_puzzle_encounter
        
        Logger.info(f"Puzzle callbacks set: complete={self.puzzle_ui.on_puzzle_complete is not None}, damage={self.puzzle_ui.on_damage is not None}, encounter={self.puzzle_ui.on_encounter is not None}")
        
        # Start puzzle 1 at world position (2, 14) - top-left of puzzle zone
        self.puzzle_ui.start_puzzle(1, 2, 14)
        self.puzzle_active = True
        
        # Show puzzle instructions
        self._show_professor_dialogue([
            "A magical floor puzzle blocks your path!",
            "Step only on PINK or ORANGE tiles - they're safe!",
            "RED tiles will reset you. BLUE tiles make you slide!",
            "Reach the golden 'E' tile at the top to proceed."
        ])
        
        Logger.info("Started Water Gym puzzle")
    
    def _on_puzzle_damage(self, damage: int):
        """Called when player takes damage from puzzle (yellow tile)."""
        Logger.info(f"Puzzle damage callback triggered with {damage} damage")
        
        if self.game_manager.bag and self.game_manager.bag.monsters:
            lead_pokemon = self.game_manager.bag.monsters[0]
            if isinstance(lead_pokemon, dict):
                old_hp = lead_pokemon.get("hp", 0)
                new_hp = max(0, old_hp - damage)
                lead_pokemon["hp"] = new_hp
                pokemon_name = lead_pokemon.get("name", "Pokemon")
                
                Logger.info(f"Puzzle damage: {damage} to {pokemon_name}. HP: {old_hp} -> {new_hp}")
                
                # Brief pause in puzzle to show message (don't show dialogue, just message)
                if self.puzzle_ui:
                    self.puzzle_ui._show_message(f"{pokemon_name} took {damage} damage! HP: {new_hp}", 1.5)
        else:
            Logger.warning("No Pokemon in bag to take damage!")
    
    def _on_puzzle_encounter(self):
        """Called when player triggers wild encounter from puzzle (green tile)."""
        Logger.info("Puzzle encounter callback triggered!")
        
        # Store puzzle state before pausing
        self._puzzle_paused = True
        if self.puzzle_ui:
            self._puzzle_resume_x = self.puzzle_ui.player_x
            self._puzzle_resume_y = self.puzzle_ui.player_y
            Logger.info(f"Stored puzzle position for resume: ({self._puzzle_resume_x}, {self._puzzle_resume_y})")
        
        # Pause puzzle (keep puzzle_ui active so we can resume)
        self.puzzle_active = False
        
        # Trigger wild Pokemon encounter using change_scene
        scene_manager.change_scene("wild_pokemon", self.game_manager)
        Logger.info("Changed to wild_pokemon scene for puzzle encounter")
    
    def _on_puzzle_ui_complete(self, puzzle_id: int):
        """Callback when puzzle UI reports completion."""
        self._on_puzzle_complete()
    
    def _update_puzzle(self, dt: float):
        """Update active puzzle."""
        if not self.puzzle_active or not self.puzzle_ui:
            return
        
        # Don't process input during dialogue
        if self.professor_dialog.is_active:
            return
        
        # Let puzzle UI handle its own input and updates
        self.puzzle_ui.update(dt)
        
        # Force sync player position to puzzle position every frame
        if self.puzzle_ui.active and self.game_manager.player:
            # Calculate world position from puzzle position
            world_x = (self.puzzle_ui.world_start_x + self.puzzle_ui.player_x) * GameSettings.TILE_SIZE
            world_y = (self.puzzle_ui.world_start_y + self.puzzle_ui.player_y) * GameSettings.TILE_SIZE
            
            # Update player position
            self.game_manager.player.position.x = world_x
            self.game_manager.player.position.y = world_y
            
            # Update animation position
            if hasattr(self.game_manager.player, 'animation'):
                self.game_manager.player.animation.update_pos(Position(world_x, world_y))
            
            # Directly set camera position to center on player
            # Camera x/y are top-left corner, so offset by half screen
            if hasattr(self.game_manager.player, 'camera'):
                self.game_manager.player.camera.x = int(world_x - GameSettings.SCREEN_WIDTH // 2)
                self.game_manager.player.camera.y = int(world_y - GameSettings.SCREEN_HEIGHT // 2)
        
        # Update player animation during puzzle (so sprite animates)
        if self.game_manager.player and hasattr(self.game_manager.player, 'animation'):
            self.game_manager.player.animation.update(dt)
        
        # Check if puzzle ended (completed or failed)
        if not self.puzzle_ui.active and self.puzzle_active:
            # Puzzle ended but wasn't marked as complete via callback
            # This means player is still trying
            pass
    
    def _on_puzzle_complete(self):
        """Called when puzzle is completed."""
        Logger.info("Puzzle completion starting...")
        
        # CRITICAL: Deactivate puzzle first
        self.puzzle_active = False
        
        # Also ensure puzzle_ui is fully deactivated
        if self.puzzle_ui:
            self.puzzle_ui.active = False
            self.puzzle_ui.current_puzzle = None
            self.puzzle_ui.current_puzzle_id = 0
        
        # Mark puzzle as complete in manager
        if self.water_gym_manager:
            self.water_gym_manager.complete_puzzle(1)
        
        # Notify tutorial
        self.tutorial_manager.on_sneak_puzzle_completed()
        
        # Move player to in front of Misty at (4, 4)
        if self.game_manager.player:
            world_x = 4 * GameSettings.TILE_SIZE
            world_y = 4 * GameSettings.TILE_SIZE
            
            self.game_manager.player.position.x = world_x
            self.game_manager.player.position.y = world_y
            
            # Update animation position
            if hasattr(self.game_manager.player, 'animation'):
                self.game_manager.player.animation.update_pos(Position(world_x, world_y))
            
            # Update camera to center on new position
            if hasattr(self.game_manager.player, 'camera'):
                self.game_manager.player.camera.x = int(world_x - GameSettings.SCREEN_WIDTH // 2)
                self.game_manager.player.camera.y = int(world_y - GameSettings.SCREEN_HEIGHT // 2)
        
        # Immediately trigger Misty found since we teleport player there
        # This prevents the check from running during dialogue
        self.tutorial_manager.on_found_real_leader()
        
        # Set flag to transition to hospital after dialogue ends
        self._pending_hospital_transition = True
        
        Logger.info(f"Puzzle completed! Teleported to (4, 4) in front of Misty")
    
    def _draw_puzzle(self, screen: pg.Surface, camera):
        """Draw the puzzle UI."""
        if self.puzzle_active and self.puzzle_ui:
            self.puzzle_ui.draw(screen, camera.x, camera.y)
    
    def _check_water_gym_night_trigger(self, dt: float):
        """Auto-trigger night when player is in water gym during WAIT_FOR_NIGHT quest."""
        if self.current_map_path != "water_gym.tmx":
            return
        
        if self.tutorial_manager.current_quest != TutorialQuest.WAIT_FOR_NIGHT:
            return
        
        if self.water_gym_night_triggered:
            return
        
        # Auto-skip to night after 3 seconds in the gym
        self._water_gym_wait_timer += dt
        
        if self._water_gym_wait_timer >= 3.0:
            self.water_gym_night_triggered = True
            self._water_gym_wait_timer = 0.0
            
            # Trigger night in water gym manager
            if self.water_gym_manager:
                self.water_gym_manager.set_night_mode(True)
            
            self._show_professor_dialogue([
                "...",
                "Time passes as you wait in the shadows...",
                "...",
                "Night has fallen. The corrupted trainer appears to be dormant.",
                "Now's your chance to sneak past and solve the puzzle ahead!"
            ])
            
            Logger.info("Night triggered in Water Gym")
    
    def _check_misty_rescue(self):
        """Check if player reached Misty's location after puzzle."""
        if self.current_map_path != "water_gym.tmx":
            return
        
        if not self.water_gym_manager:
            return
        
        # Only check after puzzle is complete
        if not self.water_gym_manager.puzzles_completed.get(1, False):
            return
        
        # Already found Misty
        if self.tutorial_manager.real_leader_found:
            return
        
        if not self.game_manager.player:
            return
        
        player_tile_y = int(self.game_manager.player.position.y // GameSettings.TILE_SIZE)
        
        # Player reached top area (y <= 6) where Misty is
        if player_tile_y <= 6:
            self.tutorial_manager.on_found_real_leader()
            Logger.info("Player found Misty!")
    
    # ============== HOSPITAL REST METHODS ==============
    
    def _check_hospital_entry(self):
        """Check if player just entered the hospital during GO_TO_HOSPITAL quest."""
        if self.current_map_path != "hospital.tmx":
            return
        
        if self.tutorial_manager.current_quest != TutorialQuest.GO_TO_HOSPITAL:
            return
        
        if self.hospital_rest_started:
            return
        
        # Start the hospital rest sequence
        self.hospital_rest_started = True
        self.hospital_rest_phase = 1  # Waiting phase
        self.hospital_rest_timer = 0.0
        
        Logger.info("Hospital rest sequence started")
    
    def _update_hospital_rest(self, dt: float):
        """Update hospital rest sequence."""
        if self.hospital_rest_phase == 0:
            return
        
        # Don't update during dialogue
        if self.professor_dialog.is_active:
            return
        
        self.hospital_rest_timer += dt
        
        if self.hospital_rest_phase == 1:  # Waiting phase (3 seconds)
            if self.hospital_rest_timer >= 3.0:
                self.hospital_rest_phase = 2  # Show rest dialogue then start blackout
                self.hospital_rest_timer = 0.0
                self._show_professor_dialogue([
                    "Misty: We made it to the hospital safely.",
                    "Misty: My Wartortle and your Pokemon need rest.",
                    "Misty: Let's take a good rest..."
                ])
        
        elif self.hospital_rest_phase == 2:  # Start fade to black (after dialogue)
            self.hospital_blackout_alpha = min(255, self.hospital_blackout_alpha + 150 * dt)
            if self.hospital_blackout_alpha >= 255:
                self.hospital_rest_timer = 0.0
                self.hospital_rest_phase = 3
        
        elif self.hospital_rest_phase == 3:  # Hold black (2 seconds)
            if self.hospital_rest_timer >= 2.0:
                self.hospital_rest_phase = 4
                self.hospital_rest_timer = 0.0
        
        elif self.hospital_rest_phase == 4:  # Fade out
            self.hospital_blackout_alpha = max(0, self.hospital_blackout_alpha - 150 * dt)
            if self.hospital_blackout_alpha <= 0:
                self.hospital_rest_phase = 5
                self.hospital_rest_timer = 0.0
                self._on_hospital_rest_complete()
        
        elif self.hospital_rest_phase == 5:  # Complete - do nothing
            pass
    
    def _on_hospital_rest_complete(self):
        """Called when hospital rest is complete - Misty finds evolution stone."""
        self._show_professor_dialogue([
            "Misty: *wakes up* Ah, that was a great rest!",
            "Misty: We're all healed up now!",
            "Misty: Wait... what's this glowing thing I found?",
            "Misty: It's... an Evolution Stone!",
            "Misty: This is perfect! With this, my Wartortle can evolve!",
            "*The Evolution Stone glows brilliantly*",
            "*Wartortle is engulfed in light...*",
            "Misty: Amazing! Wartortle evolved into BLASTOISE!",
            "Misty: Now we're ready to take on that corrupted shadow!",
            "Misty: Let's head back to the gym and finish this!"
        ])
        
        # Notify tutorial that hospital quest is done (on_reached_hospital already called in transition)
        self.tutorial_manager.on_hospital_quest_complete()
        
        # Set up corrupted battle when returning to water gym
        self.corrupted_battle_pending = True
        
        Logger.info("Hospital rest complete - Misty's Wartortle evolved to Blastoise!")
    
    def _update_hospital_transition(self, dt: float):
        """Update the transition from gym to hospital after Misty's dialogue."""
        if not self._pending_hospital_transition:
            return
        
        # Phase 0: Wait for dialogue to finish
        if self._hospital_transition_phase == 0:
            if not self.professor_dialog.is_active:
                # Dialogue finished, start fade to black
                self._hospital_transition_phase = 1
                Logger.info("Misty dialogue finished, starting hospital transition")
        
        # Phase 1: Fade to black
        elif self._hospital_transition_phase == 1:
            self._hospital_transition_alpha += 200 * dt
            if self._hospital_transition_alpha >= 255:
                self._hospital_transition_alpha = 255
                self._hospital_transition_phase = 2
        
        # Phase 2: Teleport to hospital
        elif self._hospital_transition_phase == 2:
            # Switch to hospital map
            self.game_manager.switch_map("hospital.tmx")
            self.game_manager.try_switch_map()
            self.current_map_path = "hospital.tmx"
            
            # Position player in hospital
            if self.game_manager.player:
                self.game_manager.player.position.x = 10 * GameSettings.TILE_SIZE
                self.game_manager.player.position.y = 10 * GameSettings.TILE_SIZE
                
                if hasattr(self.game_manager.player, 'animation'):
                    self.game_manager.player.animation.update_pos(Position(
                        10 * GameSettings.TILE_SIZE, 
                        10 * GameSettings.TILE_SIZE
                    ))
            
            self._hospital_transition_phase = 3
            Logger.info("Teleported to hospital")
        
        # Phase 3: Fade in
        elif self._hospital_transition_phase == 3:
            self._hospital_transition_alpha -= 200 * dt
            if self._hospital_transition_alpha <= 0:
                self._hospital_transition_alpha = 0
                self._hospital_transition_phase = 0
                self._pending_hospital_transition = False
                
                # Start hospital rest sequence
                self.hospital_rest_started = True
                self.hospital_rest_phase = 1
                self.hospital_rest_timer = 0.0
                
                # Mark as reached hospital
                self.tutorial_manager.on_reached_hospital()
                
                Logger.info("Hospital transition complete, starting rest sequence")
    
    def _draw_hospital_transition(self, screen: pg.Surface):
        """Draw the hospital transition blackout overlay."""
        if self._hospital_transition_alpha > 0:
            blackout = pg.Surface((GameSettings.SCREEN_WIDTH, GameSettings.SCREEN_HEIGHT))
            blackout.fill((0, 0, 0))
            blackout.set_alpha(int(self._hospital_transition_alpha))
            screen.blit(blackout, (0, 0))
    
    def _draw_hospital_blackout(self, screen: pg.Surface):
        """Draw hospital blackout overlay."""
        if self.hospital_blackout_alpha > 0:
            blackout = pg.Surface((GameSettings.SCREEN_WIDTH, GameSettings.SCREEN_HEIGHT))
            blackout.fill((0, 0, 0))
            blackout.set_alpha(int(self.hospital_blackout_alpha))
            screen.blit(blackout, (0, 0))
    
    # ============== CORRUPTED BATTLE SYSTEM ==============
    
    def _setup_corrupted_battle(self):
        """Set up the corrupted trainer battle in water gym."""
        self.corrupted_trainer_moved = True
        
        # Find the corrupted trainer and move to position (13, 39)
        for trainer in self.game_manager.current_enemy_trainers:
            if hasattr(trainer, 'is_corrupted') and trainer.is_corrupted:
                # Move trainer to (13, 39) in the gym
                trainer.position.x = 13 * GameSettings.TILE_SIZE
                trainer.position.y = 39 * GameSettings.TILE_SIZE
                # Reset cooldown so we can battle
                trainer.on_cooldown = False
                trainer.cooldown_timer = 0
                Logger.info(f"Moved corrupted trainer to (13, 39)")
                break
        
        # Show dialogue
        self._show_professor_dialogue([
            "Misty: The corrupted shadow is waiting for us deeper in the gym!",
            "Misty: With my new Blastoise, I can protect myself now.",
            "Misty: But you're the one who must defeat this darkness!",
            "Misty: Go forth and free this gym from corruption!"
        ])
    
    def _on_corrupted_battle_won(self):
        """Called when player wins against the corrupted trainer."""
        self.water_badge_received = True
        
        # Give water badge (add to inventory or just mark as received)
        if self.game_manager.bag:
            self.game_manager.bag.add_item("Water Badge", 1, "ingame_ui/badge_water.png")
        
        # Show victory dialogue
        self._show_professor_dialogue([
            "The dark corruption disperses into nothing!",
            "Misty: You did it! The gym is finally free!",
            "Misty: As thanks for saving me and my gym...",
            "Misty: Please accept this Water Badge!",
            "*Obtained the WATER BADGE!*",
            "Misty: Thank you so much! You're a true hero!",
            "Misty: Come visit again sometime!",
            "..."
        ])
        
        # Mark tutorial complete
        self.tutorial_manager.on_corrupted_battle_won()
        
        Logger.info("Corrupted trainer defeated! Water badge received!")
        
        # Start ending sequence after dialogue
        self.ending_sequence_active = True
        self.ending_phase = 1
    
    def _update_ending_sequence(self, dt: float):
        """Update the ending sequence."""
        if not self.ending_sequence_active:
            return
        
        # Wait for dialogue to finish before proceeding
        if self.professor_dialog.is_active:
            return
        
        if self.ending_phase == 1:
            # Phase 1: Brief view of water world (1 second)
            if not hasattr(self, 'ending_timer'):
                self.ending_timer = 0.0
            self.ending_timer += dt
            if self.ending_timer >= 1.0:
                self.ending_phase = 2
                self.ending_timer = 0.0
                Logger.info("Ending: Brief view complete, starting fade")
        
        elif self.ending_phase == 2:
            # Fade to black
            self.ending_blackout_alpha += 150 * dt
            if self.ending_blackout_alpha >= 255:
                self.ending_blackout_alpha = 255
                self.ending_phase = 3
                self.ending_timer = 0.0
                Logger.info("Ending: Faded to black")
        
        elif self.ending_phase == 3:
            # Show "To.. Be.. Continued.." for 3 seconds, then go to menu
            self.ending_text_shown = True
            if not hasattr(self, 'ending_timer'):
                self.ending_timer = 0.0
            self.ending_timer += dt
            if self.ending_timer >= 3.0:
                self.ending_phase = 4
                Logger.info("Ending: Text shown, returning to menu")
        
        elif self.ending_phase == 4:
            # Return to menu scene
            self.ending_sequence_active = False
            self.ending_text_shown = False
            scene_manager.change_scene("menu")
            Logger.info("Ending: Returned to MenuScene")
    
    def _draw_ending(self, screen: pg.Surface):
        """Draw the ending sequence."""
        if not self.ending_sequence_active:
            return
        
        # Draw blackout
        if self.ending_blackout_alpha > 0:
            blackout = pg.Surface((GameSettings.SCREEN_WIDTH, GameSettings.SCREEN_HEIGHT))
            blackout.fill((0, 0, 0))
            blackout.set_alpha(int(min(255, self.ending_blackout_alpha)))
            screen.blit(blackout, (0, 0))
        
        # Draw "To Be Continued..." text
        if self.ending_text_shown:
            try:
                ending_font = pg.font.Font("assets/fonts/Pokemon Solid.ttf", 48)
            except:
                ending_font = pg.font.Font(None, 48)
            
            text = ending_font.render("To Be Continued...", True, (255, 255, 255))
            text_x = (GameSettings.SCREEN_WIDTH - text.get_width()) // 2
            text_y = (GameSettings.SCREEN_HEIGHT - text.get_height()) // 2
            screen.blit(text, (text_x, text_y))
    
    def _check_water_world_walk(self):
        """Check if player walked away from spawn in Water World to trigger next quest."""
        if self.current_map_path != "water_map.tmx":
            return
        
        if self.water_world_walk_triggered:
            return
        
        if self.tutorial_manager.current_quest != TutorialQuest.ENTER_WATER_WORLD:
            return
        
        if not self.water_world_spawn_pos or not self.game_manager.player:
            return
        
        # Check distance from spawn (3 tiles)
        dx = self.game_manager.player.position.x - self.water_world_spawn_pos.x
        dy = self.game_manager.player.position.y - self.water_world_spawn_pos.y
        distance = (dx * dx + dy * dy) ** 0.5
        
        if distance >= 3 * GameSettings.TILE_SIZE:
            self.water_world_walk_triggered = True
            self.tutorial_manager.on_water_world_walk()
            Logger.info("Player walked away from Water World spawn - triggering next quest")
    
    def _check_water_gym_entry_dialogue(self):
        """Check if player walked away from water gym entrance to show corrupted trainer dialogue."""
        if self.current_map_path != "water_gym.tmx":
            return
        
        if self.water_gym_entry_dialogue_shown:
            return
        
        if self.tutorial_manager.current_quest != TutorialQuest.VISIT_WATER_GYM:
            return
        
        if not self.water_gym_spawn_pos or not self.game_manager.player:
            return
        
        # Check distance from spawn (2 tiles)
        dx = self.game_manager.player.position.x - self.water_gym_spawn_pos.x
        dy = self.game_manager.player.position.y - self.water_gym_spawn_pos.y
        distance = (dx * dx + dy * dy) ** 0.5
        
        if distance >= 2 * GameSettings.TILE_SIZE:
            self.water_gym_entry_dialogue_shown = True
            self.tutorial_manager.on_entered_water_gym()
            Logger.info("Player walked away from Water Gym entrance - showing corrupted trainer dialogue")

    def _open_pc(self):
        """Open the PC storage interface."""
        if not hasattr(self.game_manager, 'pc_storage') or self.game_manager.pc_storage is None:
            # Create PC storage if it doesn't exist
            from src.core.managers.pc_storage import PCStorage
            self.game_manager.pc_storage = PCStorage()
        
        self.pc_ui.open(
            party=self.game_manager.bag.monsters,
            pc_pokemon=self.game_manager.pc_storage.pokemon,
            on_deposit=self._on_pc_deposit,
            on_withdraw=self._on_pc_withdraw
        )
        Logger.info("PC opened")
    
    def _on_pc_deposit(self, monster) -> bool:
        """Handle depositing a Pokemon to PC."""
        if hasattr(self.game_manager, 'pc_storage') and self.game_manager.pc_storage:
            return self.game_manager.pc_storage.deposit(monster)
        return False
    
    def _on_pc_withdraw(self, index: int):
        """Handle withdrawing a Pokemon from PC."""
        if hasattr(self.game_manager, 'pc_storage') and self.game_manager.pc_storage:
            return self.game_manager.pc_storage.withdraw(index)
        return None

    def _setup_professor_npc(self):
        """Setup the professor NPC on the main map."""
        # Professor is on the main map (map.tmx), to the left of the house
        self.professor_npc = ProfessorNPC(x=10, y=23)
        Logger.info("Professor NPC created at (10, 23)")
    
    def _on_quiz_complete(self, coins_earned: int):
        """Called when coding quiz is completed."""
        if coins_earned > 0:
            self.game_manager.bag.add_item("Coins", coins_earned, "ingame_ui/coin.png")
            self._show_professor_dialogue([
                f"Great job! You earned {coins_earned} coins!",
                "Come back anytime if you need more coins!"
            ])
        else:
            self._show_professor_dialogue([
                "Don't worry, coding takes practice!",
                "Come back and try again anytime!"
            ])
    
    def _check_no_alive_pokemon_dialog(self):
        """Check if we need to show the professor dialog about no alive Pokemon."""
        # Check both wild pokemon scene and battle scene flags
        need_dialog = get_need_professor_heal_dialog() or get_need_professor_heal_dialog_battle()
        
        if need_dialog:
            self._show_professor_dialogue([
                "Oh no! All your Pokemon have fainted!",
                "You can buy Potions at P'Anan's shop at the top right of the map.",
                "If you don't have enough coins, come talk to me!",
                "I'm standing to the left of your house.",
                "Answer my coding quiz questions to earn some coins!"
            ])
            Logger.info("Showed professor heal dialog")

    # ============== ORIGINAL METHODS ==============

    def _send_chat_message(self, text: str) -> bool:
        """Send a chat message via online manager."""
        if self.online_manager:
            return self.online_manager.send_chat(text)
        return False

    def _get_chat_messages(self, count: int) -> list[dict]:
        """Get chat messages from online manager."""
        if self.online_manager:
            return self.online_manager.get_chat_messages(count)
        return []

    def _init_minimap(self):
        """Initialize the minimap with current map dimensions"""
        if self.game_manager.current_map:
            world_width = self.game_manager.current_map.tmxdata.width * GameSettings.TILE_SIZE
            world_height = self.game_manager.current_map.tmxdata.height * GameSettings.TILE_SIZE
            map_surface = self.game_manager.current_map._surface
            self.minimap = Minimap(world_width, world_height, map_surface, size=150)
    
    def _handle_map_change(self):
        """Handle map changes - update minimap and BGM"""
        self._init_minimap()
        self.navigation_ui.stop_navigation()
        
        map_path = self.game_manager.current_map.path_name
        
        if "town" in map_path.lower() or "pallet" in map_path.lower():
            sound_manager.play_bgm("RBY 103 Pallet Town.ogg")
        elif "route" in map_path.lower():
            sound_manager.play_bgm("RBY 103 Pallet Town.ogg")
        elif "house" in map_path.lower() or "building" in map_path.lower():
            sound_manager.play_bgm("RBY 103 Pallet Town.ogg")
        elif "gym" in map_path.lower():
            sound_manager.play_bgm("RBY 103 Pallet Town.ogg")
        elif "water_map" in map_path.lower() or "water_world" in map_path.lower():
            sound_manager.play_bgm("RBY 103 Pallet Town.ogg")  # Can change to water world BGM
        elif "hospital" in map_path.lower():
            sound_manager.play_bgm("RBY 103 Pallet Town.ogg")  # Can change to hospital BGM
        
        Logger.info(f"Map changed to: {map_path}")
        
        # Initialize Water Gym manager when entering water gym
        if map_path == "water_gym.tmx":
            self._init_water_gym_manager()
            if self.water_gym_manager:
                self.water_gym_manager.enter_gym()
            
            # Track spawn position for delayed dialogue
            if self.game_manager.player:
                self.water_gym_spawn_pos = Position(
                    self.game_manager.player.position.x,
                    self.game_manager.player.position.y
                )
            self.water_gym_entry_dialogue_shown = False
            
            # Check if returning for corrupted battle
            if self.corrupted_battle_pending and not self.corrupted_trainer_moved:
                self._setup_corrupted_battle()
        
        # Check hospital entry for rest sequence
        if map_path == "hospital.tmx":
            self._check_hospital_entry()
        
        # Check if we should show the tree dialogue (returning to main map after Fire Gym WIN)
        if map_path == "map.tmx" and self.pending_tree_dialogue:
            self.pending_tree_dialogue = False
            self.water_world_teleport_active = True
            self._show_professor_dialogue([
                "Incredible! You defeated the Fire Gym Leader!",
                "Wait... what's happening?!",
                "A magical ruin portal has appeared on the southeast corner of the map!",
                "The power released from your battle must have unsealed something ancient!",
                "You must go investigate this mysterious phenomenon!",
                "Be careful - we don't know what lies on the other side..."
            ])
        
        # Check tutorial triggers
        self._check_map_transition_tutorial()

    def get_closest_enemy(self) -> EnemyTrainer | None:
        closest = None
        min_dist = float('inf')
        for enemy in self.game_manager.current_enemy_trainers:
            dist = enemy._distance_to_player()
            if dist < min_dist:
                min_dist = dist
                closest = enemy
        return closest

    @override
    def enter(self, data: Any = None) -> None:
        sound_manager.play_bgm("RBY 103 Pallet Town.ogg")
        if self.online_manager:
            self.online_manager.enter()
        self._init_minimap()
        
        # Set player name if provided from intro scene
        if data and isinstance(data, dict) and "player_name" in data:
            self.player_name = data["player_name"]
            Logger.info(f"Player name set to: {self.player_name}")
        
        # Start tutorial if not already started (first time entering)
        if not self.tutorial_started:
            self.tutorial_started = True
            self.tutorial_manager.start_tutorial()
            # Only set monster count on FIRST entry
            self.last_monster_count = len(self.game_manager.bag._monsters_data)
            Logger.info(f"Tutorial started, initial monster count: {self.last_monster_count}")
        else:
            # Returning from battle - check for new Pokemon
            Logger.info(f"Returning to game scene, checking for updates...")
            self._check_new_pokemon_caught()
            
            # Check if player won a trainer battle
            self._check_trainer_battle_result()
            
            # Check if we need to show the "no alive pokemon" dialog
            self._check_no_alive_pokemon_dialog()
            
            # Resume puzzle if it was paused for wild encounter
            if self._puzzle_paused and self.puzzle_ui:
                self._puzzle_paused = False
                self.puzzle_active = True
                # Restore player position in puzzle
                self.puzzle_ui.player_x = self._puzzle_resume_x
                self.puzzle_ui.player_y = self._puzzle_resume_y
                self.puzzle_ui.active = True
                # Sync player world position
                self.puzzle_ui._sync_player_position()
                Logger.info(f"Resumed puzzle at ({self._puzzle_resume_x}, {self._puzzle_resume_y})")

    @override
    def exit(self) -> None:
        if self.online_manager:
            self.online_manager.exit()

    def _any_overlay_open(self) -> bool:
        """Check if any overlay is currently open."""
        return (
            self.game_manager.bag.overlay_show or 
            self.setting.overlay_show or 
            self.shop_ui.overlay_show or
            self.navigation_ui.overlay_show or
            (self.chat_overlay and self.chat_overlay.is_open) or
            self.professor_dialog.is_active or
            self.pc_ui.overlay_show or
            self.coding_quiz_ui.overlay_show or
            self.game_menu_ui.overlay_show or
            self.pokedex_ui.overlay_show or
            self.achievements_ui.overlay_show or
            self.evolution_ui.overlay_show or
            self.puzzle_active or
            self.hospital_rest_phase > 0 or
            self.ending_sequence_active
        )
    
    def _on_evolution_complete(self):
        """Called when evolution animation finishes."""
        # Actually apply the evolution to the monster
        if self._pending_evolution_monster:
            evolve_monster(self._pending_evolution_monster)
            Logger.info(f"Evolution applied: {self._pending_evolution_monster.get('name')}")
            self._pending_evolution_monster = None
    
    def _check_pending_evolution(self):
        """Check if there's a pending evolution from battle and trigger animation."""
        evolution_data = get_pending_evolution()
        if evolution_data:
            monster, old_name, new_name, old_sprite, new_sprite = evolution_data
            self._pending_evolution_monster = monster
            self.evolution_ui.start_evolution(monster, old_name, new_name, old_sprite, new_sprite)
            Logger.info(f"Starting evolution animation: {old_name} -> {new_name}")
    
    def _get_captured_pokemon_names(self) -> list[str]:
        """Get list of all Pokemon names the player has captured (current + PC)."""
        captured = set()
        
        # Add party Pokemon
        for monster in self.game_manager.bag._monsters_data:
            name = monster.get("name", "")
            if name:
                captured.add(name)
        
        # Add PC Pokemon
        if hasattr(self.game_manager, 'pc_storage') and self.game_manager.pc_storage:
            for monster in self.game_manager.pc_storage.pokemon:
                name = monster.get("name", "")
                if name:
                    captured.add(name)
        
        return list(captured)
    
    def _get_unlocked_badges(self) -> list[str]:
        """Get list of unlocked badge IDs based on completed quests."""
        badges = []
        current_quest = self.tutorial_manager.current_quest
        
        # Fire Gym Badge - only if actually WON (not just attempted)
        if self.tutorial_manager.fire_gym_won:
            badges.append("fire_gym")
        
        # Night Survivor Badge - unlocked after SURVIVE_THE_NIGHT quest
        if current_quest.value > TutorialQuest.SURVIVE_THE_NIGHT.value:
            badges.append("night_survivor")
        
        # Water Master Badge - unlocked after WATER_WALKING quest
        if current_quest.value > TutorialQuest.CATCH_WATER_POKEMON.value:
            badges.append("water_master")
        
        return badges
    
    def _get_unlocked_achievements(self) -> list[str]:
        """Get list of unlocked achievement IDs based on player progress."""
        achievements = []
        current_quest = self.tutorial_manager.current_quest
        
        # Tutorial complete - after all quests done
        if current_quest == TutorialQuest.COMPLETED:
            achievements.append("tutorial_complete")
        
        # Count total captured Pokemon
        captured_names = self._get_captured_pokemon_names()
        total_captured = len(captured_names)
        
        # Also count PC storage
        total_in_party = len(self.game_manager.bag._monsters_data)
        total_in_pc = 0
        if hasattr(self.game_manager, 'pc_storage') and self.game_manager.pc_storage:
            total_in_pc = len(self.game_manager.pc_storage.pokemon)
        total_pokemon_owned = total_in_party + total_in_pc
        
        # First catch - have any Pokemon
        if total_pokemon_owned > 0:
            achievements.append("first_catch")
        
        # Catch 10 Pokemon
        if total_pokemon_owned >= 10:
            achievements.append("catch_10")
        
        # Catch 20 Pokemon
        if total_pokemon_owned >= 20:
            achievements.append("catch_20")
        
        # First trainer battle win
        if self.tutorial_manager.trainer_battles_won >= 1:
            achievements.append("first_battle")
        
        # Win 5 trainer battles
        if self.tutorial_manager.trainer_battles_won >= 5:
            achievements.append("win_5_battles")
        
        # First evolution - check if any Pokemon has evolved forms
        evolved_pokemon = {"Ivysaur", "Venusaur", "Charmeleon", "Charizard", 
                          "Wartortle", "Blastoise", "Raichu", "Haunter", "Gengar",
                          "Dragonair", "Dragonite"}
        if any(name in evolved_pokemon for name in captured_names):
            achievements.append("first_evolution")
        
        # Coin achievements - find coins in bag items
        coins = 0
        for item in self.game_manager.bag.items:
            if item.get("name") == "Coins":
                coins = item.get("count", 0)
                break
        
        if coins >= 100:
            achievements.append("earn_100_coins")
        if coins >= 500:
            achievements.append("earn_500_coins")
        
        # Quiz master - check quiz stats (use coding_quiz_ui if it tracks this)
        if hasattr(self.coding_quiz_ui, 'total_correct') and self.coding_quiz_ui.total_correct >= 10:
            achievements.append("quiz_master")
        
        # Pokedex 50% - 14 out of 28 unique Pokemon
        if len(captured_names) >= 14:
            achievements.append("pokedex_50")
        
        # Full party - 6 Pokemon in party
        if total_in_party >= 6:
            achievements.append("full_party")
        
        return achievements

    def _get_player_direction_string(self) -> str:
        """Get the current player direction as a string for network sync."""
        if self.game_manager.player:
            direction = self.game_manager.player.direction
            if isinstance(direction, str):
                return direction
            return str(direction).lower().replace("direction.", "")
        return "down"

    def _is_player_moving(self) -> bool:
        """Check if player is currently moving (any movement key held)."""
        return (
            input_manager.key_down(pg.K_LEFT) or input_manager.key_down(pg.K_a) or
            input_manager.key_down(pg.K_RIGHT) or input_manager.key_down(pg.K_d) or
            input_manager.key_down(pg.K_UP) or input_manager.key_down(pg.K_w) or
            input_manager.key_down(pg.K_DOWN) or input_manager.key_down(pg.K_s)
        )

    @override
    def update(self, dt: float):
        # ============== TUTORIAL UPDATES ==============
        
        # Check for pending evolution from battle (do this first)
        self._check_pending_evolution()
        
        # Update evolution UI
        self.evolution_ui.update(dt)
        self.quest_ui.update(dt)
        
        # Block other updates while evolution is playing
        if self.evolution_ui.overlay_show:
            return
        
        # Update professor dialog first (it handles its own input now)
        self.professor_dialog.update(dt)
        
        # Professor dialog handles its own input - just block other updates while active
        if self.professor_dialog.is_active:
            self.teleport_cooldown = 1.0  # Prevent teleporting right after dialogue
            return  # Don't process other input while dialog is active
        
        # Update teleport cooldown
        if self.teleport_cooldown > 0:
            self.teleport_cooldown -= dt
        
        # Check if player has walked far enough from house to trigger dialogue
        self._check_distance_from_house()
        
        # Update tutorial manager
        tutorial_events = self.tutorial_manager.update(dt)
        
        # Handle night mode from tutorial
        if tutorial_events.get("is_night"):
            self.is_night = True
            self.night_overlay_alpha = min(180, self.night_overlay_alpha + 100 * dt)
            
            # Spawn gengars if needed
            if not self.gengars:
                self._spawn_gengars()
            
            # Update gengars
            if self.game_manager.player:
                for gengar in self.gengars:
                    events = gengar.update(dt, self.game_manager.player.position, self.is_night)
                    if events.get("caught_player"):
                        self._on_gengar_caught_player()
                        break  # Only one catch per frame
                        
        elif tutorial_events.get("night_ended"):
            self.is_night = False
            self.gengars.clear()
            self.night_overlay_alpha = 0
        else:
            # Fade out night if not night time
            if not self.is_night:
                self.night_overlay_alpha = max(0, self.night_overlay_alpha - 100 * dt)
        
        # Update day/night cycle (after tutorial)
        self._update_day_night_cycle(dt)
        
        # Update gengars during day/night cycle
        if self.day_night_cycle_enabled and self.is_night and self.game_manager.player:
            for gengar in self.gengars:
                events = gengar.update(dt, self.game_manager.player.position, self.is_night)
                if events.get("caught_player"):
                    self._on_gengar_caught_player()
                    break
        
        # Update quest UI with fade support
        if not self.tutorial_manager.should_hide_quest_ui():
            quest_alpha = self.tutorial_manager.get_quest_fade_alpha()
            self.quest_ui.set_quest(self.tutorial_manager.get_quest_description(), quest_alpha)
        else:
            self.quest_ui.hide()
        
        # ============== ORIGINAL UPDATES ==============
        
        # Update online interpolation first
        if self.online_manager:
            self.online_manager.tick(dt)
        
        # Track previous map before switch
        self.previous_map_path = self.current_map_path
        
        # Only try to switch map if cooldown is done
        if self.teleport_cooldown <= 0:
            self.game_manager.try_switch_map()
        
        if self.game_manager.current_map and self.current_map_path != self.game_manager.current_map.path_name:
            self.current_map_path = self.game_manager.current_map.path_name
            self._handle_map_change()

        self.navigation_ui.update(dt)

        if self.chat_overlay:
            self.chat_overlay.update(dt)

        if self.chat_overlay and not self.game_manager.bag.overlay_show and not self.setting.overlay_show and not self.shop_ui.overlay_show:
            if input_manager.key_pressed(pg.K_t) and not self.chat_overlay.is_open:
                self.chat_overlay.open()

        if not self._any_overlay_open():
            if self.game_manager.player and not self.navigation_ui.is_navigating:
                # Pass flag to player to disable wild encounters during Gengar chase
                self.game_manager.player.update(dt, allow_wild_encounter=self._can_encounter_wild_pokemon())
                
                # Check if player just entered water (for tutorial)
                self._check_water_crossing()
                
                # Check if player steps on water world teleport (after tree removal)
                self._check_water_world_teleport()
                
                # Check if player steps on return teleport in water world
                self._check_water_world_return_teleport()
                
            elif self.game_manager.player and self.navigation_ui.is_navigating:
                self.game_manager.player.animation.update_pos(self.game_manager.player.position)
                self.game_manager.player.animation.update(dt)

            # Disable trainer battles during Gengar chase
            if not self._is_gengar_chase_active():
                for enemy in self.game_manager.current_enemy_trainers:
                    enemy.update(dt)

            for shop in self.game_manager.current_shops:
                shop.update(dt)

            if self.game_manager.player and input_manager.key_pressed(pg.K_e):
                for shop in self.game_manager.current_shops:
                    if shop.can_interact(self.game_manager.player.position):
                        shop.interact(self.game_manager.player)
                        self.shop_ui.open(shop, self.game_manager.bag)
                        break
            
            # PC interaction - press P to open PC (available in home)
            if self.game_manager.player and input_manager.key_pressed(pg.K_p):
                if self.current_map_path == "home.tmx":
                    self._open_pc()
            
            # Professor NPC interaction (only on main map)
            if self.professor_npc and self.current_map_path == "map.tmx":
                self.professor_npc.update(dt, self.game_manager.player.position if self.game_manager.player else None)
                
                if self.game_manager.player and input_manager.key_pressed(pg.K_e):
                    if self.professor_npc.can_interact(self.game_manager.player.position):
                        self.coding_quiz_ui.open()
            
            if self.navigation_ui.is_navigating:
                if input_manager.key_pressed(pg.K_ESCAPE) or input_manager.key_pressed(pg.K_q):
                    self.navigation_ui.stop_navigation()
                    Logger.info("Navigation cancelled")
            
            # DEBUG: Press F9 to test evolution animation (remove in production)
            if input_manager.key_pressed(pg.K_F9):
                # Get first Pokemon in party for test
                if self.game_manager.bag._monsters_data:
                    test_monster = self.game_manager.bag._monsters_data[0]
                    old_name = test_monster.get("name", "Pikachu")
                    old_sprite = test_monster.get("sprite_path", "menu_sprites/pikachu.png")
                    # Fake evolution data for testing (use actual sprite paths)
                    self.evolution_ui.start_evolution(
                        test_monster, 
                        old_name, 
                        "Raichu",  # Test evolution target
                        old_sprite,
                        "menu_sprites/raichu.png"  # Correct path
                    )
                    Logger.info("DEBUG: Testing evolution animation")
            
            # DEBUG: Press F10 to toggle tree removal (remove in production)
            if input_manager.key_pressed(pg.K_F10):
                self.tree_removed = not self.tree_removed
                self.water_world_teleport_active = self.tree_removed
                if self.tree_removed:
                    # Remove collision for all water tiles
                    for tile_x, tile_y in self.water_tiles:
                        self.game_manager.remove_collision_tile("map.tmx", tile_x, tile_y)
                    Logger.info(f"DEBUG: Trees removed, water tiles active, teleport active at {self.water_world_teleport_tiles}")
                else:
                    # Re-add collision (clear removed tiles)
                    if "map.tmx" in self.game_manager.removed_collision_tiles:
                        for tile_x, tile_y in self.water_tiles:
                            pos = (tile_x, tile_y)
                            if pos in self.game_manager.removed_collision_tiles["map.tmx"]:
                                self.game_manager.removed_collision_tiles["map.tmx"].remove(pos)
                    Logger.info(f"DEBUG: Trees restored, teleport inactive")

        if not self._any_overlay_open():
            self.bag_button.update(dt)
            self.settings_button.update(dt)
            self.menu_button.update(dt)

        self.game_manager.bag.update(dt)
        self.setting.update(dt)
        self.shop_ui.update(dt)
        self.pc_ui.update(dt)
        self.coding_quiz_ui.update(dt)
        self.game_menu_ui.update(dt)
        self.pokedex_ui.update(dt)
        self.achievements_ui.update(dt)

        if self.game_manager.player and self.online_manager:
            direction = self._get_player_direction_string()
            is_moving = self._is_player_moving() or self.navigation_ui.is_navigating
            
            _ = self.online_manager.update(
                self.game_manager.player.position.x,
                self.game_manager.player.position.y,
                self.game_manager.current_map.path_name,
                direction,
                is_moving
            )

        if self.online_manager:
            list_online = self.online_manager.get_list_players()
            
            for player_data in list_online:
                pid = player_data.get("id", 0)
                direction = player_data.get("direction", "down")
                is_moving = player_data.get("is_moving", False)
                pos = Position(player_data["x"], player_data["y"])
                
                if pid not in self.online_player_sprites:
                    self.online_player_sprites[pid] = OnlinePlayerSprite()
                
                self.online_player_sprites[pid].update(dt, direction, is_moving, pos)
            
            current_pids = {p.get("id", 0) for p in list_online}
            to_remove = [pid for pid in self.online_player_sprites if pid not in current_pids]
            for pid in to_remove:
                del self.online_player_sprites[pid]

        # Update water transition (runs always, even during overlays)
        self._update_water_transition(dt)
        
        # ============== WATER GYM PUZZLE UPDATES ==============
        if self.current_map_path == "water_gym.tmx":
            # Check for night trigger (auto-skip to night after waiting)
            self._check_water_gym_night_trigger(dt)
            
            # Safety check: if puzzle is completed but puzzle_active is still True, reset it
            if self.puzzle_active and self.water_gym_manager and self.water_gym_manager.puzzles_completed.get(1, False):
                Logger.info("Safety reset: puzzle completed but puzzle_active was True")
                self.puzzle_active = False
                if self.puzzle_ui:
                    self.puzzle_ui.active = False
            
            # Check for puzzle zone entry (only if not already in puzzle)
            if not self.puzzle_active:
                self._check_water_gym_puzzle_zone()
            else:
                # Update puzzle
                self._update_puzzle(dt)
            
            # Check if player reached Misty after puzzle
            self._check_misty_rescue()
        
        # ============== HOSPITAL REST UPDATES ==============
        self._update_hospital_rest(dt)
        
        # ============== PENDING HOSPITAL TRANSITION ==============
        self._update_hospital_transition(dt)
        
        # ============== ENDING SEQUENCE ==============
        self._update_ending_sequence(dt)
        
        # ============== WATER WORLD WALK DETECTION ==============
        self._check_water_world_walk()
        
        # ============== WATER GYM ENTRY DIALOGUE ==============
        self._check_water_gym_entry_dialogue()

        if self.game_manager.player:
            self.closest_enemy = self.get_closest_enemy()

    @override
    def draw(self, screen: pg.Surface):
        # 1. Draw the world (map)
        if self.game_manager.player:
            camera = self.game_manager.player.camera
            self.game_manager.current_map.draw(screen, camera)
        else:
            camera = PositionCamera(0, 0)
            self.game_manager.current_map.draw(screen, camera)
        
        # 1b. Draw water tiles if tree is removed (opening to river)
        if self.tree_removed and self.current_map_path == "map.tmx":
            # Draw water tiles (6 tiles total) to create river opening
            water_color = (64, 164, 223)  # Light blue water
            water_dark = (47, 141, 198)   # Darker blue for texture
            
            for tile_x, tile_y in self.water_tiles:
                screen_x = tile_x * GameSettings.TILE_SIZE - camera.x
                screen_y = tile_y * GameSettings.TILE_SIZE - camera.y
                
                pg.draw.rect(screen, water_color, 
                            (screen_x, screen_y, GameSettings.TILE_SIZE, GameSettings.TILE_SIZE))
                
                # Add water wave texture
                wave_offset = int((pg.time.get_ticks() / 200) % 8)
                for wy in range(0, GameSettings.TILE_SIZE, 8):
                    offset = 2 if ((wy // 8) % 2 == 0) else -2
                    pg.draw.line(screen, water_dark, 
                                (screen_x + offset + wave_offset, screen_y + wy),
                                (screen_x + GameSettings.TILE_SIZE - 1, screen_y + wy), 1)

        # 2. Draw entities in the world (enemies, shops)
        for enemy in self.game_manager.current_enemy_trainers:
            enemy.draw(screen, camera)

        for shop in self.game_manager.current_shops:
            shop.draw(screen, camera)

        # 2b. Draw Professor NPC (only on main map)
        if self.professor_npc and self.current_map_path == "map.tmx":
            self.professor_npc.draw(screen, camera)

        # 3. Draw online players (in the world, below local player and UI)
        if self.online_manager and self.game_manager.player:
            list_online = self.online_manager.get_list_players()
            for player_data in list_online:
                if player_data["map"] == self.game_manager.current_map.path_name:
                    pid = player_data.get("id", 0)
                    if pid in self.online_player_sprites:
                        self.online_player_sprites[pid].draw(screen, camera)

        # 4. Draw local player (on top of online players)
        if self.game_manager.player:
            self.game_manager.player.draw(screen, camera)

        # 5. Draw Gengars (in world space)
        for gengar in self.gengars:
            gengar.draw(screen, camera)

        # 6. Draw navigation path
        self.navigation_ui.draw(screen)

        # 7. Draw day/night overlay
        if self.day_night_cycle_enabled and self.night_overlay_alpha > 0:
            day_surface = pg.Surface((GameSettings.SCREEN_WIDTH, GameSettings.SCREEN_HEIGHT), pg.SRCALPHA)
            r, g, b = self.day_overlay_color
            day_surface.fill((r, g, b, int(self.night_overlay_alpha)))
            screen.blit(day_surface, (0, 0))
        elif self.night_overlay_alpha > 0:
            # Fallback for tutorial night (Gengar chase)
            night_surface = pg.Surface((GameSettings.SCREEN_WIDTH, GameSettings.SCREEN_HEIGHT), pg.SRCALPHA)
            night_surface.fill((20, 20, 60, int(self.night_overlay_alpha)))
            screen.blit(night_surface, (0, 0))
        
        # 7c. Draw water transition blackout overlay
        if self.water_transition_blackout > 0:
            blackout_surface = pg.Surface((GameSettings.SCREEN_WIDTH, GameSettings.SCREEN_HEIGHT), pg.SRCALPHA)
            blackout_surface.fill((0, 0, 0, int(self.water_transition_blackout)))
            screen.blit(blackout_surface, (0, 0))
        
        # 7d. Draw puzzle overlay (when in water gym puzzle)
        if self.puzzle_active and self.puzzle_ui and self.game_manager.player:
            self._draw_puzzle(screen, self.game_manager.player.camera)
        
        # 7e. Draw hospital blackout overlay
        self._draw_hospital_blackout(screen)
        
        # 7e2. Draw hospital transition overlay (from gym to hospital)
        self._draw_hospital_transition(screen)
        
        # 7f. Draw ending sequence overlay
        self._draw_ending(screen)
        
        # 7b. Draw time display (when day/night cycle is enabled)
        if self.day_night_cycle_enabled and not self._any_overlay_open():
            self._draw_time_display(screen)

        # 8. Draw UI buttons (on top of everything in the world)
        if not self._any_overlay_open():
            self.bag_button.draw(screen)
            self.settings_button.draw(screen)
            self.menu_button.draw(screen)

        # 9. Draw Minimap
        if self.minimap and self.game_manager.player and not self._any_overlay_open():
            entities = []
            
            for enemy in self.game_manager.current_enemy_trainers:
                entities.append(type('Entity', (), {'pos': enemy.position, 'color': (255, 0, 0)})())
            
            # Add Gengars to minimap (purple dots)
            for gengar in self.gengars:
                entities.append(type('Entity', (), {'pos': gengar.position, 'color': (128, 0, 128)})())
            
            if self.online_manager:
                list_online = self.online_manager.get_list_players()
                for player in list_online:
                    if player["map"] == self.game_manager.current_map.path_name:
                        entities.append(type('Entity', (), {
                            'pos': Position(player["x"], player["y"]),
                            'color': (0, 100, 255)
                        })())
            
            self.minimap.draw(screen, self.game_manager.player.position, entities)

        # 10. Draw water riding indicator
        if self.game_manager.player and hasattr(self.game_manager.player, 'is_on_water') and self.game_manager.player.is_on_water:
            font = pg.font.Font(None, 24)
            riding_text = font.render("~ Riding Water Pokemon ~", True, (100, 200, 255))
            text_rect = riding_text.get_rect(center=(GameSettings.SCREEN_WIDTH // 2, 50))
            
            # Draw background
            bg_rect = text_rect.inflate(20, 10)
            bg_surface = pg.Surface((bg_rect.width, bg_rect.height), pg.SRCALPHA)
            bg_surface.fill((0, 50, 100, 150))
            screen.blit(bg_surface, bg_rect)
            screen.blit(riding_text, text_rect)
        
        # 10b. Draw PC hint when in home
        if self.current_map_path == "home.tmx" and not self._any_overlay_open():
            font = pg.font.Font(None, 22)
            pc_hint = font.render("Press P to access PC", True, (200, 200, 255))
            hint_rect = pc_hint.get_rect(center=(GameSettings.SCREEN_WIDTH // 2, GameSettings.SCREEN_HEIGHT - 30))
            
            bg_rect = hint_rect.inflate(20, 8)
            bg_surface = pg.Surface((bg_rect.width, bg_rect.height), pg.SRCALPHA)
            bg_surface.fill((0, 0, 50, 150))
            screen.blit(bg_surface, bg_rect)
            screen.blit(pc_hint, hint_rect)

        # 11. Draw Quest UI (always visible, top center)
        if not self.professor_dialog.is_active:
            self.quest_ui.draw(screen)

        # 12. Draw overlays (on top of UI)
        self.game_manager.bag.draw(screen)
        if self.setting.overlay_show:
            self.setting.draw(screen)
        self.shop_ui.draw(screen)
        self.pc_ui.draw(screen)
        self.coding_quiz_ui.draw(screen)
        self.game_menu_ui.draw(screen)
        self.pokedex_ui.draw(screen)
        self.achievements_ui.draw(screen)
        self.evolution_ui.draw(screen)

        # 13. Draw chat overlay
        if self.chat_overlay:
            self.chat_overlay.draw(screen)

        # 14. Draw professor dialog (always on top of everything)
        self.professor_dialog.draw(screen)

    def _find_valid_spawn_point(self, max_attempts=50) -> Position | None:
        """Find a random valid spawn point on the current map."""
        if not self.game_manager.current_map:
            return None
            
        width = self.game_manager.current_map.width
        height = self.game_manager.current_map.height
        
        for _ in range(max_attempts):
            x = random.randint(5, width - 6)  # Avoid edges
            y = random.randint(5, height - 6)
            
            # Create a rect for tile checking
            rect = pg.Rect(x * GameSettings.TILE_SIZE + 4, y * GameSettings.TILE_SIZE + 4, 
                          GameSettings.TILE_SIZE - 8, GameSettings.TILE_SIZE - 8)
            
            if not self.game_manager.current_map.check_collision(rect) and \
               not self.game_manager.current_map.check_water_collision(rect):
                   return Position(x * GameSettings.TILE_SIZE, y * GameSettings.TILE_SIZE)
        return None

    def _spawn_midnight_merchant(self):
        """Spawn the Midnight Merchant at a random location."""
        # Only spawn if not already active and on main map
        if self.midnight_merchant or self.current_map_path != "map.tmx":
            return
            
        pos = self._find_valid_spawn_point()
        if not pos:
            Logger.warning("Could not find spawn point for Midnight Merchant")
            return
            
        # Create inventory
        inventory = [
            ShopItem("Master Ball", 5000, "ingame_ui/ball_master.png", "Catches any Pokemon without fail.", stock=1),
            ShopItem("Rare Candy", 2500, "ingame_ui/candy_rare.png", "Instantly raises a Pokemon's level.", stock=5),
            ShopItem("Full Restore", 1500, "ingame_ui/potion_full.png", "Fully restores HP and status.", stock=10),
            ShopItem("Max Revive", 2000, "ingame_ui/revive_max.png", "Revives and fully heals a Pokemon.", stock=3)
        ]
        
        self.midnight_merchant = ShopEntity(
            pos.x, pos.y, 
            self.game_manager, 
            name="Midnight Merchant",
            inventory=inventory,
            sprite_path="character/ow9.png" # Mysterious figure
        )
        
        # Robust addition to shop list
        current_key = self.game_manager.current_map_key
        if current_key not in self.game_manager.shops:
            self.game_manager.shops[current_key] = []
        self.game_manager.shops[current_key].append(self.midnight_merchant)
        
        Logger.info(f"Midnight Merchant spawned at {pos.x}, {pos.y}")
        
    def _despawn_midnight_merchant(self):
        """Despawn the Midnight Merchant."""
        if self.midnight_merchant:
            if self.midnight_merchant in self.game_manager.current_shops:
                self.game_manager.current_shops.remove(self.midnight_merchant)
            self.midnight_merchant = None
            Logger.info("Midnight Merchant despawned")

    def _init_time_events(self):
        """Initialize all day/night cycle events."""
        
        # 1. Midnight Merchant (00:00 - 04:00)
        def start_merchant():
            sound_manager.play_sound("RBY 117 Obtained an Item!.ogg")
            self._spawn_midnight_merchant()
            self._show_professor_dialogue(["The Midnight Merchant has appeared!", "Look for him on the map!"])
            
        self.time_event_manager.add_event(TimeEvent(
            "MidnightMerchant", 0, 4, 0.3,
            on_start=start_merchant,
            on_end=self._despawn_midnight_merchant,
            description="The Midnight Merchant is open!"
        ))
        
        # 2. Morning Blessing (06:00 - 07:00)
        def morning_heal():
            if self.game_manager.bag.monsters:
                for m in self.game_manager.bag.monsters:
                    m["hp"] = m["max_hp"]
                sound_manager.play_sound("RBY 114 Pokemon Recovery.ogg")
                Logger.info("Morning Healing Applied")
        
        self.time_event_manager.add_event(TimeEvent(
            "MorningBlessing", 6, 7, 0.5,
            on_start=morning_heal,
            description="The morning sun energizes your Pokemon! (Full Heal)"
        ))
        
        # 3. Dusk Swarm (18:00 - 20:00)
        def start_dusk_swarm():
            if not self.game_manager.bag.has_item("Gengar Repeller"):
                self.gengars.clear() 
                self._spawn_gengars()
                
        self.time_event_manager.add_event(TimeEvent(
            "DuskSwarm", 18, 20, 0.4,
            on_start=start_dusk_swarm,
            description="The shadows are lengthening... (High Danger)"
        ))
        
        # 4. Golden Hour (12:00 - 13:00)
        self.time_event_manager.add_event(TimeEvent(
            "GoldenHour", 12, 13, 0.2,
            on_start=lambda: None,
            description="It's Golden Hour! (Double Coins from battles)"
        ))
        
        # 5. Mysterious Gift (03:00 - 04:00)
        def give_gift():
            items = ["Potion", "Pokeball", "Super Potion", "Great Ball"]
            item = random.choice(items)
            self.game_manager.bag.add_item(item, 1)
            self._show_professor_dialogue([f"You found a {item} dropped by a mysterious stranger!"])
            
        self.time_event_manager.add_event(TimeEvent(
            "MysteriousGift", 3, 4, 0.1,
            on_start=give_gift,
            description="You hear a strange noise..."
        ))
        
        # 6. Rainy Afternoon (14:00 - 16:00)
        def start_rain():
            self.day_overlay_color = (0, 0, 50)
            self.night_overlay_alpha = 50
            
        self.time_event_manager.add_event(TimeEvent(
            "RainyAfternoon", 14, 16, 0.3,
            on_start=start_rain,
            on_end=lambda: setattr(self, 'night_overlay_alpha', 0),
            description="It started raining heavily!"
        ))
        
        # 7. Starfall (22:00 - 23:00)
        def starfall_event():
            sound_manager.play_sound("RBY 117 Obtained an Item!.ogg")
            self.game_manager.bag.add_item("Nugget", 1)
            
        self.time_event_manager.add_event(TimeEvent(
            "Starfall", 22, 23, 0.2,
            on_start=starfall_event,
            description="A shooting star fell nearby! You found a Nugget!"
        ))
        
        # 8. Training Montage (08:00 - 10:00)
        self.time_event_manager.add_event(TimeEvent(
            "TrainingMontage", 8, 10, 0.3,
            on_start=lambda: None,
            description="You feel pumped! (XP Gain increased)"
        ))
        
        # 9. Ghostly Whisper (01:00 - 02:00)
        self.time_event_manager.add_event(TimeEvent(
            "GhostlyWhisper", 1, 2, 0.1,
            on_start=lambda: sound_manager.play_sound("RBY 131 Trainers_ Eyes Meet (Bad Guy).ogg"),
            description="You hear a chilling whisper: 'Get out...'"
        ))
        
        # 10. Market Day (10:00 - 12:00)
        def start_market():
            if hasattr(self.shop_ui, 'discount_active'):
                self.shop_ui.discount_active = True
                
        def end_market():
            if hasattr(self.shop_ui, 'discount_active'):
                self.shop_ui.discount_active = False
                
        self.time_event_manager.add_event(TimeEvent(
            "MarketDay", 10, 12, 0.4,
            on_start=start_market,
            on_end=end_market,
            description="Market Day! 20% Discount at all shops!"
        ))
        
        # 11. Lucky Find (17:00 - 18:00)
        self.time_event_manager.add_event(TimeEvent(
            "LuckyFind", 17, 18, 0.05,
            on_start=lambda: self.game_manager.bag.add_item("Nugget", 1),
            description="You tripped over a growing Nugget!"
        ))
        
        # 12. Professor's Broadcast (09:00 - 10:00)
        tips = [
            "Tip: Water beats Fire, but is weak to Electric!",
            "Tip: You can rest at home to heal your Pokemon.",
            "Tip: Press M to view the map.",
            "Tip: Catching Pokemon gives you EXP too!",
            "Tip: Rare Pokemon appear more often in tall grass."
        ]
        self.time_event_manager.add_event(TimeEvent(
            "ProfBroadcast", 9, 10, 0.5,
            on_start=lambda: self._show_professor_dialogue(["[Broadcast] " + random.choice(tips)]),
            description="Incoming transmission from Professor Oak..."
        ))



class Settings:
    def __init__(self, game_manager: GameManager):
        self.game_manager = game_manager
        self.overlay_show = False
        
        # Panel dimensions
        self.panel_width = 500
        self.panel_height = 450
        self.panel_x = (GameSettings.SCREEN_WIDTH - self.panel_width) // 2
        self.panel_y = (GameSettings.SCREEN_HEIGHT - self.panel_height) // 2
        
        # Darken background
        self.darken = pg.Surface((GameSettings.SCREEN_WIDTH, GameSettings.SCREEN_HEIGHT))
        self.darken.fill((0, 0, 0))
        self.darken.set_alpha(180)
        
        # Fonts
        try:
            self.title_font = pg.font.Font("assets/fonts/Minecraft.ttf", 28)
            self.label_font = pg.font.Font("assets/fonts/Minecraft.ttf", 18)
            self.small_font = pg.font.Font("assets/fonts/Minecraft.ttf", 14)
        except:
            self.title_font = pg.font.Font(None, 32)
            self.label_font = pg.font.Font(None, 22)
            self.small_font = pg.font.Font(None, 18)
        
        # Audio settings
        self.volume = GameSettings.AUDIO_VOLUME
        self.is_muted = False
        
        # Slider dragging
        self.dragging_slider = False
        
        # Message display
        self.message = ""
        self.message_timer = 0.0
        
    def _on_load(self):
        """Handle load button press"""
        if self.game_manager.reload_from_file("saves/game0.json"):
            Logger.info("Game loaded successfully!")
            self.game_manager.bag.reload_bag()
            self.message = "Game loaded successfully!"
            self.message_timer = 2.0
        else:
            Logger.warning("Failed to load game")
            self.message = "Failed to load game!"
            self.message_timer = 2.0
    
    def _on_save(self):
        """Handle save button press"""
        self.game_manager.save("saves/game0.json")
        self.message = "Game saved successfully!"
        self.message_timer = 2.0
        Logger.info("Game saved!")
            
    def open(self): 
        self.overlay_show = True
        self.message = ""
        
    def close(self): 
        self.overlay_show = False
        self.dragging_slider = False
        
    def update(self, dt: float):
        if not self.overlay_show:
            return
        
        # Update message timer
        if self.message_timer > 0:
            self.message_timer -= dt
            if self.message_timer <= 0:
                self.message = ""
        
        mouse_pos = pg.mouse.get_pos()
        mouse_pressed = pg.mouse.get_pressed()[0]
        
        # Handle slider dragging
        slider_x = self.panel_x + 50
        slider_y = self.panel_y + 130
        slider_width = 300
        slider_height = 20
        slider_rect = pg.Rect(slider_x, slider_y, slider_width, slider_height)
        
        if mouse_pressed:
            if slider_rect.collidepoint(mouse_pos) or self.dragging_slider:
                self.dragging_slider = True
                # Calculate new volume
                rel_x = mouse_pos[0] - slider_x
                self.volume = max(0.0, min(1.0, rel_x / slider_width))
                sound_manager.set_master_volume(self.volume)
        else:
            self.dragging_slider = False
        
        # Handle clicks
        if input_manager.mouse_pressed(1):
            # Close button
            close_btn_rect = pg.Rect(self.panel_x + self.panel_width - 40, self.panel_y + 10, 30, 30)
            if close_btn_rect.collidepoint(mouse_pos):
                self.close()
                return
            
            # Mute toggle
            mute_btn_rect = pg.Rect(self.panel_x + 420, self.panel_y + 125, 60, 30)
            if mute_btn_rect.collidepoint(mouse_pos):
                self.is_muted = not self.is_muted
                if self.is_muted:
                    sound_manager.pause_all()
                else:
                    sound_manager.resume_all()
                return
            
            # Save button
            save_btn_rect = pg.Rect(self.panel_x + 50, self.panel_y + 280, 180, 50)
            if save_btn_rect.collidepoint(mouse_pos):
                self._on_save()
                return
            
            # Load button
            load_btn_rect = pg.Rect(self.panel_x + 270, self.panel_y + 280, 180, 50)
            if load_btn_rect.collidepoint(mouse_pos):
                self._on_load()
                return
        
        # Handle escape
        if input_manager.key_pressed(pg.K_ESCAPE):
            self.close()
            
    def draw(self, screen: pg.Surface):
        if not self.overlay_show:
            return
        
        mouse_pos = pg.mouse.get_pos()
        
        # Darken background
        screen.blit(self.darken, (0, 0))
        
        # Main panel
        panel_rect = pg.Rect(self.panel_x, self.panel_y, self.panel_width, self.panel_height)
        
        # Panel shadow
        shadow_rect = panel_rect.copy()
        shadow_rect.x += 5
        shadow_rect.y += 5
        pg.draw.rect(screen, (20, 20, 30), shadow_rect, border_radius=15)
        
        # Panel background
        pg.draw.rect(screen, (40, 45, 60), panel_rect, border_radius=12)
        
        # Panel border
        pg.draw.rect(screen, (80, 90, 110), panel_rect, 3, border_radius=12)
        
        # Title bar
        title_bar = pg.Rect(self.panel_x, self.panel_y, self.panel_width, 50)
        pg.draw.rect(screen, (60, 70, 90), title_bar, 
                     border_top_left_radius=12, border_top_right_radius=12)
        
        # Title
        title_text = self.title_font.render("SETTINGS", True, (255, 255, 255))
        screen.blit(title_text, (self.panel_x + 20, self.panel_y + 12))
        
        # Close button
        close_btn_rect = pg.Rect(self.panel_x + self.panel_width - 40, self.panel_y + 10, 30, 30)
        close_color = (200, 80, 80) if close_btn_rect.collidepoint(mouse_pos) else (150, 60, 60)
        pg.draw.rect(screen, close_color, close_btn_rect, border_radius=5)
        x_text = self.label_font.render("X", True, (255, 255, 255))
        screen.blit(x_text, (close_btn_rect.centerx - x_text.get_width() // 2, 
                            close_btn_rect.centery - x_text.get_height() // 2))
        
        # === AUDIO SECTION ===
        section_y = self.panel_y + 70
        
        # Section header
        audio_header = self.label_font.render("AUDIO", True, (150, 200, 255))
        screen.blit(audio_header, (self.panel_x + 20, section_y))
        
        # Divider
        pg.draw.line(screen, (80, 90, 110), 
                     (self.panel_x + 20, section_y + 25), 
                     (self.panel_x + self.panel_width - 20, section_y + 25), 2)
        
        # Volume label
        vol_label = self.small_font.render("Master Volume", True, (180, 180, 180))
        screen.blit(vol_label, (self.panel_x + 50, section_y + 40))
        
        # Volume slider background
        slider_x = self.panel_x + 50
        slider_y = section_y + 60
        slider_width = 300
        slider_height = 20
        
        pg.draw.rect(screen, (30, 30, 35), (slider_x, slider_y, slider_width, slider_height), border_radius=5)
        
        # Volume slider fill
        fill_width = int(slider_width * self.volume)
        if fill_width > 0:
            pg.draw.rect(screen, (80, 150, 220), (slider_x, slider_y, fill_width, slider_height), border_radius=5)
        
        # Slider handle
        handle_x = slider_x + fill_width - 8
        handle_rect = pg.Rect(handle_x, slider_y - 3, 16, slider_height + 6)
        handle_color = (120, 180, 255) if self.dragging_slider else (100, 160, 230)
        pg.draw.rect(screen, handle_color, handle_rect, border_radius=3)
        pg.draw.rect(screen, (150, 200, 255), handle_rect, 2, border_radius=3)
        
        # Volume percentage
        vol_pct = self.small_font.render(f"{int(self.volume * 100)}%", True, (255, 255, 255))
        screen.blit(vol_pct, (slider_x + slider_width + 15, slider_y + 2))
        
        # Mute button (moved further right)
        mute_btn_rect = pg.Rect(self.panel_x + 420, section_y + 55, 60, 30)
        mute_hovered = mute_btn_rect.collidepoint(mouse_pos)
        
        if self.is_muted:
            mute_color = (180, 80, 80) if mute_hovered else (150, 60, 60)
            mute_text = "MUTED"
        else:
            mute_color = (80, 140, 80) if mute_hovered else (60, 110, 60)
            mute_text = "SOUND"
        
        pg.draw.rect(screen, mute_color, mute_btn_rect, border_radius=5)
        pg.draw.rect(screen, (100, 100, 120), mute_btn_rect, 2, border_radius=5)
        
        mute_label = self.small_font.render(mute_text, True, (255, 255, 255))
        screen.blit(mute_label, (mute_btn_rect.centerx - mute_label.get_width() // 2,
                                 mute_btn_rect.centery - mute_label.get_height() // 2))
        
        # === GAME DATA SECTION ===
        data_section_y = self.panel_y + 200
        
        # Section header
        data_header = self.label_font.render("GAME DATA", True, (255, 200, 150))
        screen.blit(data_header, (self.panel_x + 20, data_section_y))
        
        # Divider
        pg.draw.line(screen, (80, 90, 110), 
                     (self.panel_x + 20, data_section_y + 25), 
                     (self.panel_x + self.panel_width - 20, data_section_y + 25), 2)
        
        # Save description
        save_desc = self.small_font.render("Save your progress or load a previous save", True, (140, 140, 140))
        screen.blit(save_desc, (self.panel_x + 50, data_section_y + 40))
        
        # Save button
        save_btn_rect = pg.Rect(self.panel_x + 50, data_section_y + 70, 180, 50)
        save_hovered = save_btn_rect.collidepoint(mouse_pos)
        save_color = (60, 130, 60) if save_hovered else (50, 100, 50)
        
        pg.draw.rect(screen, save_color, save_btn_rect, border_radius=8)
        pg.draw.rect(screen, (80, 160, 80), save_btn_rect, 2, border_radius=8)
        
        save_icon = self.label_font.render("SAVE", True, (255, 255, 255))
        screen.blit(save_icon, (save_btn_rect.centerx - save_icon.get_width() // 2,
                               save_btn_rect.centery - save_icon.get_height() // 2))
        
        # Load button
        load_btn_rect = pg.Rect(self.panel_x + 270, data_section_y + 70, 180, 50)
        load_hovered = load_btn_rect.collidepoint(mouse_pos)
        load_color = (60, 100, 140) if load_hovered else (50, 80, 110)
        
        pg.draw.rect(screen, load_color, load_btn_rect, border_radius=8)
        pg.draw.rect(screen, (80, 130, 180), load_btn_rect, 2, border_radius=8)
        
        load_icon = self.label_font.render("LOAD", True, (255, 255, 255))
        screen.blit(load_icon, (load_btn_rect.centerx - load_icon.get_width() // 2,
                               load_btn_rect.centery - load_icon.get_height() // 2))
        
        # === MESSAGE ===
        if self.message:
            msg_rect = pg.Rect(self.panel_x + 20, self.panel_y + self.panel_height - 50, 
                              self.panel_width - 40, 35)
            
            # Message background
            if "success" in self.message.lower():
                bg_color = (50, 80, 50)
                border_color = (100, 150, 100)
            else:
                bg_color = (80, 50, 50)
                border_color = (150, 100, 100)
            
            pg.draw.rect(screen, bg_color, msg_rect, border_radius=5)
            pg.draw.rect(screen, border_color, msg_rect, 2, border_radius=5)
            
            msg_text = self.small_font.render(self.message, True, (255, 255, 255))
            screen.blit(msg_text, (msg_rect.centerx - msg_text.get_width() // 2,
                                  msg_rect.centery - msg_text.get_height() // 2))
        
        # === FOOTER INFO ===
        footer_text = self.small_font.render("Press ESC to close", True, (100, 100, 110))
        screen.blit(footer_text, (self.panel_x + self.panel_width // 2 - footer_text.get_width() // 2,
                                  self.panel_y + self.panel_height - 25))