import pygame as pg
from typing import override, Any
import random

from src.utils import GameSettings, Logger
from src.sprites import BackgroundSprite, Sprite
from src.scenes.scene import Scene
from src.interface.components import Button
from src.core.services import scene_manager, sound_manager, input_manager
from src.sprites.sprite import Text
from src.utils.definition import (
    Monster, get_type_multiplier, get_effectiveness_message,
    get_pokemon_moves, MOVE_DATABASE, Move,
    check_evolution, evolve_monster
)
from src.interface.switch_pokemon_ui import SwitchPokemonUI
from src.scenes.battle_scene import set_pending_evolution
from src.interface.battle_ui import BattleUI


# Element type colors for display
ELEMENT_COLORS_DISPLAY = {
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

# Track encounters for guaranteed spawns
encounter_tracker = {
    "encounters_since_water": 0,
    "need_water_pokemon": False,
    "water_pokemon_blocked": True  # Block water Pokemon until CATCH_WATER_POKEMON quest
}

# Flag to trigger professor "no alive pokemon" dialog
need_professor_heal_dialog = False


def get_need_professor_heal_dialog() -> bool:
    """Get and reset the professor heal dialog flag."""
    global need_professor_heal_dialog
    result = need_professor_heal_dialog
    need_professor_heal_dialog = False
    return result


def set_water_pokemon_blocked(blocked: bool):
    """Set whether water Pokemon spawns are blocked."""
    encounter_tracker["water_pokemon_blocked"] = blocked
    Logger.info(f"Water Pokemon blocked: {blocked}")


def calculate_coin_reward(defeated_pokemon: Monster, is_trainer: bool = False) -> int:
    """Calculate coin reward from defeating a Pokemon."""
    base_coins = 10
    level_bonus = defeated_pokemon.get("level", 1) * 5
    
    # Bonus for rarer types
    element = defeated_pokemon.get("element", "Normal")
    type_bonus = {
        "Dragon": 20,
        "Ghost": 15,
        "Psychic": 10,
        "Electric": 5,
    }.get(element, 0)
    
    total = base_coins + level_bonus + type_bonus
    
    # Trainer battles give more coins
    if is_trainer:
        total = int(total * 1.5)
    
    return total


# ============== XP SYSTEM ==============

def calculate_xp_reward(defeated_pokemon: Monster) -> int:
    """Calculate XP reward from defeating a Pokemon."""
    base_xp = 50
    level_bonus = defeated_pokemon.get("level", 1) * 10
    
    # Bonus XP for stronger Pokemon types
    element = defeated_pokemon.get("element", "Normal")
    type_bonus = {
        "Dragon": 30,
        "Ghost": 20,
        "Psychic": 15,
        "Electric": 10,
    }.get(element, 0)
    
    return base_xp + level_bonus + type_bonus


def calculate_xp_for_level(level: int) -> int:
    """Calculate total XP needed to reach a level."""
    # Simple quadratic formula: XP = 100 * level^1.5
    return int(100 * (level ** 1.5))


def calculate_xp_to_next_level(current_level: int) -> int:
    """Calculate XP needed to go from current level to next."""
    return calculate_xp_for_level(current_level + 1) - calculate_xp_for_level(current_level)


def apply_stat_scaling(monster: Monster, levels_gained: int = 1):
    """Apply stat increases when leveling up."""
    for _ in range(levels_gained):
        # HP increases by 2-4 per level
        hp_gain = random.randint(2, 4)
        monster["max_hp"] = monster.get("max_hp", 20) + hp_gain
        monster["hp"] = monster.get("hp", 20) + hp_gain  # Heal by the amount gained
        
        # Attack increases by 1-2 per level
        if random.random() < 0.7:  # 70% chance to gain attack
            monster["attack"] = monster.get("attack", 10) + random.randint(1, 2)
        
        # Defense increases by 1-2 per level
        if random.random() < 0.7:  # 70% chance to gain defense
            monster["defense"] = monster.get("defense", 10) + random.randint(1, 2)


# ============== END XP SYSTEM ==============


class HealthBar:
    """A visual health bar for battle monsters."""
    
    def __init__(self, x: int, y: int, width: int = 200, height: int = 20):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.current_hp = 100
        self.max_hp = 100
        
    def set_hp(self, current: int, maximum: int):
        """Set the current and max HP values."""
        self.current_hp = max(0, current)
        self.max_hp = max(1, maximum)
        
    def draw(self, screen: pg.Surface):
        """Draw the health bar."""
        pg.draw.rect(screen, (0, 0, 0), (self.x - 2, self.y - 2, self.width + 4, self.height + 4))
        pg.draw.rect(screen, (128, 128, 128), (self.x, self.y, self.width, self.height))
        
        hp_percentage = self.current_hp / self.max_hp
        current_width = int(self.width * hp_percentage)
        
        if hp_percentage > 0.5:
            color = (0, 255, 0)
        elif hp_percentage > 0.25:
            color = (255, 255, 0)
        else:
            color = (255, 0, 0)
            
        if current_width > 0:
            pg.draw.rect(screen, color, (self.x, self.y, current_width, self.height))


class MoveButton:
    """A button for selecting a move in battle."""
    
    def __init__(self, x: int, y: int, width: int, height: int, move: Move | None, callback):
        self.rect = pg.Rect(x, y, width, height)
        self.move = move
        self.callback = callback
        self.hovered = False
        self.enabled = True
        
    def update_move(self, move: Move | None):
        """Update the move this button represents."""
        self.move = move
        self.enabled = move is not None and move.get("pp", 0) > 0
        
    def update(self, dt: float):
        """Update button state."""
        mouse_pos = input_manager.mouse_pos
        self.hovered = self.rect.collidepoint(mouse_pos) and self.enabled
        
        # Trigger on mouse pressed (same as Button class)
        if self.hovered and input_manager.mouse_pressed(1):
            if self.move and self.enabled:
                self.callback(self.move)
    
    def draw(self, screen: pg.Surface):
        """Draw the move button."""
        if not self.move:
            return
            
        move_type = self.move.get("type", "Normal")
        base_color = ELEMENT_COLORS_DISPLAY.get(move_type, (168, 168, 120))
        
        if not self.enabled:
            color = (100, 100, 100)
        elif self.hovered:
            color = tuple(min(255, c + 40) for c in base_color)
        else:
            color = base_color
        
        pg.draw.rect(screen, color, self.rect, border_radius=8)
        pg.draw.rect(screen, (0, 0, 0), self.rect, 2, border_radius=8)
        
        font = pg.font.Font(None, 24)
        name_text = font.render(self.move.get("name", "???"), True, (255, 255, 255))
        name_rect = name_text.get_rect(center=(self.rect.centerx, self.rect.y + 20))
        screen.blit(name_text, name_rect)
        
        pp = self.move.get("pp", 0)
        max_pp = self.move.get("max_pp", 0)
        pp_font = pg.font.Font(None, 18)
        pp_text = pp_font.render(f"PP: {pp}/{max_pp}", True, (255, 255, 255))
        pp_rect = pp_text.get_rect(center=(self.rect.centerx, self.rect.y + 40))
        screen.blit(pp_text, pp_rect)
        
        power = self.move.get("power", 0)
        if power > 0:
            power_text = pp_font.render(f"Power: {power}", True, (255, 255, 255))
            power_rect = power_text.get_rect(center=(self.rect.centerx, self.rect.y + 55))
            screen.blit(power_text, power_rect)


class WildPokemonScene(Scene):
    """Scene for encountering and catching wild Pokemon."""
    
    def __init__(self):
        super().__init__()
        self.background = BackgroundSprite("backgrounds/background2.png")
        self.wild_pokemon = None
        self.player_monster = None
        self.wild_pokemon_sprite = None
        self.player_monster_sprite = None
        self.game_manager = None
        
        self.is_player_turn = True
        self.battle_over = False
        self.pokemon_caught = False
        self.battle_message = "A wild Pokemon appeared!"
        self.wild_attack_timer = 0
        self.escape_timer = 0
        self.message_delay_timer = 0
        self.victory_timer = 0
        
        # Victory/Defeat screen state
        self.show_defeat_screen = False
        self.show_victory_screen = False
        self.victory_screen_timer = 0
        
        # Evolution animation state
        self.evolution_pending = False
        self.evolution_timer = 0
        self.evolution_new_name = ""
        
        # XP/Level tracking for victory screen
        self.xp_gained = 0
        self.leveled_up = False
        self.coins_gained = 0
        self.effectiveness_message = ""

        # Move selection state
        self.show_moves = False
        self.move_buttons: list[MoveButton] = []
        self.selected_move: Move | None = None

        # Health bars (legacy)
        self.wild_health_bar = HealthBar(GameSettings.SCREEN_WIDTH * 3 // 4 - 100, 100)
        self.player_health_bar = HealthBar(GameSettings.SCREEN_WIDTH // 4 - 100, GameSettings.SCREEN_HEIGHT - 75)

        # Banner (legacy)
        self.game_announcement_banner_sprite = Sprite("UI/raw/UI_Flat_Banner04a.png", (400, 200))
        self.game_announcement_banner_sprite.rect.topleft = (20, 20)
        
        self.battle_text = Text(self.battle_message, 24, "black")
        self.battle_text.rect.topleft = (30, 30)
        
        # Effectiveness text
        self.effectiveness_text = Text("", 18, "black")
        self.effectiveness_text.rect.topleft = (50, 85)

        # Text attributes (legacy)
        self.wild_name_text = None
        self.wild_level_text = None
        self.wild_hp_text = None
        self.wild_element_text = None
        self.player_name_text = None
        self.player_level_text = None
        self.player_hp_text = None
        self.player_element_text = None

        px, py = GameSettings.SCREEN_WIDTH // 2, GameSettings.SCREEN_HEIGHT * 3 // 4
        
        # Switch Pokemon UI
        self.switch_pokemon_ui = SwitchPokemonUI(
            on_switch=self._on_pokemon_switched,
            on_cancel=self._on_switch_cancelled
        )
        
        # === NEW MODERN BATTLE UI ===
        self.battle_ui = BattleUI(is_trainer_battle=False)
        self.battle_ui.set_callbacks(
            fight_cb=self._on_attack,
            run_cb=self._on_run,
            switch_cb=self._on_switch,
            catch_cb=self._on_catch,
            back_cb=self._on_back,
            move_cb=self._on_move_selected
        )
        
        # Legacy buttons (kept for reference)
        self.attack_button = Button(
            "UI/raw/UI_Flat_Button02a_3.png", "UI/raw/UI_Flat_Button02a_2.png",
            px + 50, py - 50, 200, 100,
            self._on_attack
        )
        self.attack_text = Text("Fight", 30, "black")
        self.attack_text.rect.center = (px + 150, py)

        self.catch_button = Button(
            "UI/raw/UI_Flat_Button02a_3.png", "UI/raw/UI_Flat_Button02a_2.png",
            px + 250, py - 50, 200, 100,
            self._on_catch
        )
        self.catch_text = Text("Catch", 30, "black")
        self.catch_text.rect.center = (px + 350, py)

        self.switch_button = Button(
            "UI/raw/UI_Flat_Button02a_3.png", "UI/raw/UI_Flat_Button02a_2.png",
            px + 50, py + 45, 200, 100,
            self._on_switch
        )
        self.switch_text = Text("Switch", 30, "black")
        self.switch_text.rect.center = (px + 150, py + 95)

        self.run_button = Button(
            "UI/raw/UI_Flat_Button02a_3.png", "UI/raw/UI_Flat_Button02a_2.png",
            px + 250, py + 45, 200, 100,
            self._on_run
        )
        self.run_text = Text("Run", 30, "black")
        self.run_text.rect.center = (px + 350, py + 95)
        
        self.back_button = Button(
            "UI/raw/UI_Flat_Button02a_3.png", "UI/raw/UI_Flat_Button02a_2.png",
            px + 320, py + 80, 120, 60,
            self._on_back
        )
        self.back_text = Text("Back", 24, "black")
        self.back_text.rect.center = (px + 380, py + 110)

    def _setup_move_buttons(self):
        """Setup move buttons based on player's Pokemon moves."""
        if not self.player_monster:
            return
            
        moves = get_pokemon_moves(self.player_monster)
        self.battle_ui.setup_moves(moves)

    def _on_move_selected(self, move: Move):
        """Handle when a move is selected."""
        if move.get("pp", 0) <= 0:
            self.battle_message = "No PP left for this move!"
            self._update_battle_text()
            return
            
        self.selected_move = move
        self.show_moves = False
        self.battle_ui.show_moves = False
        self._player_attack_with_move(move)

    def _on_back(self):
        """Go back from move selection to main menu."""
        self.show_moves = False
        self.battle_ui.show_moves = False

    def _get_water_pokemon(self) -> Monster:
        """Get a guaranteed water type Pokemon."""
        water_pool = [
            {"name": "Magikarp", "max_hp": 20, "level": random.randint(2, 5), "sprite_path": "menu_sprites/magikarp.png", "attack": 3, "defense": 3, "element": "Water", "xp": 0},
            {"name": "Psyduck", "max_hp": 40, "level": random.randint(3, 6), "sprite_path": "menu_sprites/psyduck.png", "attack": 8, "defense": 6, "element": "Water", "xp": 0},
            {"name": "Squirtle", "max_hp": 44, "level": random.randint(3, 6), "sprite_path": "menu_sprites/squirtle.png", "attack": 8, "defense": 10, "element": "Water", "xp": 0},
            {"name": "Poliwag", "max_hp": 40, "level": random.randint(3, 5), "sprite_path": "menu_sprites/poliwag.png", "attack": 7, "defense": 5, "element": "Water", "xp": 0},
        ]
        
        pokemon = random.choice(water_pool).copy()
        pokemon["hp"] = pokemon["max_hp"]
        get_pokemon_moves(pokemon)
        return pokemon

    def _generate_wild_pokemon(self) -> Monster:
        """Generate a random wild Pokemon with element types."""
        global encounter_tracker
        
        # Check if we need to guarantee a water Pokemon (only if not blocked)
        if encounter_tracker["need_water_pokemon"] and not encounter_tracker["water_pokemon_blocked"]:
            encounter_tracker["encounters_since_water"] += 1
            
            # Every 3rd encounter is guaranteed water type
            if encounter_tracker["encounters_since_water"] >= 3:
                encounter_tracker["encounters_since_water"] = 0
                Logger.info("Guaranteed water Pokemon spawn!")
                return self._get_water_pokemon()
        
        wild_pool = [
            {"name": "Pidgey", "max_hp": 35, "level": random.randint(2, 5), "sprite_path": "menu_sprites/pidgey.png", "attack": 7, "defense": 5, "element": "Flying", "xp": 0},
            {"name": "Rattata", "max_hp": 30, "level": random.randint(2, 4), "sprite_path": "menu_sprites/rattata.png", "attack": 8, "defense": 4, "element": "Normal", "xp": 0},
            {"name": "Caterpie", "max_hp": 25, "level": random.randint(2, 4), "sprite_path": "menu_sprites/caterpie.png", "attack": 5, "defense": 5, "element": "Bug", "xp": 0},
            {"name": "Weedle", "max_hp": 25, "level": random.randint(2, 4), "sprite_path": "menu_sprites/weedle.png", "attack": 6, "defense": 4, "element": "Bug", "xp": 0},
            {"name": "Pikachu", "max_hp": 40, "level": random.randint(3, 6), "sprite_path": "menu_sprites/pikachu.png", "attack": 10, "defense": 6, "element": "Electric", "xp": 0},
            {"name": "Geodude", "max_hp": 45, "level": random.randint(3, 6), "sprite_path": "menu_sprites/geodude.png", "attack": 9, "defense": 10, "element": "Rock", "xp": 0},
            {"name": "Zubat", "max_hp": 35, "level": random.randint(3, 5), "sprite_path": "menu_sprites/zubat.png", "attack": 7, "defense": 5, "element": "Poison", "xp": 0},
            {"name": "Magikarp", "max_hp": 20, "level": random.randint(2, 5), "sprite_path": "menu_sprites/magikarp.png", "attack": 3, "defense": 3, "element": "Water", "xp": 0},
            {"name": "Psyduck", "max_hp": 40, "level": random.randint(3, 6), "sprite_path": "menu_sprites/psyduck.png", "attack": 8, "defense": 6, "element": "Water", "xp": 0},
            {"name": "Oddish", "max_hp": 38, "level": random.randint(3, 5), "sprite_path": "menu_sprites/oddish.png", "attack": 7, "defense": 6, "element": "Grass", "xp": 0},
            {"name": "Bellsprout", "max_hp": 35, "level": random.randint(3, 5), "sprite_path": "menu_sprites/bellsprout.png", "attack": 8, "defense": 5, "element": "Grass", "xp": 0},
            {"name": "Gastly", "max_hp": 35, "level": random.randint(4, 7), "sprite_path": "menu_sprites/gastly.png", "attack": 10, "defense": 4, "element": "Ghost", "xp": 0},
            {"name": "Dratini", "max_hp": 45, "level": random.randint(5, 8), "sprite_path": "menu_sprites/dratini.png", "attack": 10, "defense": 7, "element": "Dragon", "xp": 0},
            {"name": "Bulbasaur", "max_hp": 45, "level": random.randint(4, 7), "sprite_path": "menu_sprites/bulbasaur.png", "attack": 7, "defense": 7, "element": "Grass", "xp": 0},
            {"name": "Charmander", "max_hp": 39, "level": random.randint(4, 7), "sprite_path": "menu_sprites/charmander.png", "attack": 8, "defense": 6, "element": "Fire", "xp": 0},
        ]
        
        # Filter out water Pokemon if blocked
        if encounter_tracker["water_pokemon_blocked"]:
            wild_pool = [p for p in wild_pool if p.get("element") != "Water"]
        
        pokemon = random.choice(wild_pool).copy()
        pokemon["hp"] = pokemon["max_hp"]
        
        # Initialize moves for wild Pokemon
        get_pokemon_moves(pokemon)
        
        # Track if this is a water type
        if encounter_tracker["need_water_pokemon"] and pokemon.get("element") == "Water":
            encounter_tracker["encounters_since_water"] = 0
        
        return pokemon

    def _calculate_damage_with_move(self, attacker: Monster, defender: Monster, move: Move) -> tuple[int, float]:
        """Calculate damage based on monster stats, move power, and element types."""
        attack_stat = attacker.get("attack", 10)
        defense_stat = defender.get("defense", 5)
        level = attacker.get("level", 1)
        
        move_power = move.get("power", 40)
        move_type = move.get("type", "Normal")
        accuracy = move.get("accuracy", 100)
        
        # Check if move hits
        if random.randint(1, 100) > accuracy:
            return 0, 1.0  # Miss
        
        # Get type multiplier
        defender_type = defender.get("element", "Normal")
        type_multiplier = get_type_multiplier(move_type, defender_type)
        
        # STAB bonus
        attacker_type = attacker.get("element", "Normal")
        stab = 1.5 if move_type == attacker_type else 1.0
        
        # Random factor
        random_factor = random.uniform(0.85, 1.0)
        
        # Damage formula
        base = ((2 * level / 5 + 2) * move_power * attack_stat / defense_stat / 50 + 2)
        damage = int(base * type_multiplier * stab * random_factor)
        
        return max(1, damage), type_multiplier

    def _player_attack_with_move(self, move: Move):
        """Player attacks with a specific move."""
        if not self.player_monster or not self.wild_pokemon or self.battle_over:
            return
        
        # Reduce PP
        move["pp"] = max(0, move.get("pp", 0) - 1)
        
        move_name = move.get("name", "Attack")
        damage, type_mult = self._calculate_damage_with_move(self.player_monster, self.wild_pokemon, move)
        
        if damage == 0:
            self.battle_message = f"{self.player_monster['name']} used {move_name}! But it missed!"
            self._update_battle_text()
            self.effectiveness_text = Text("", 18, "black")
        else:
            self.wild_pokemon["hp"] = max(0, self.wild_pokemon["hp"] - damage)
            self.battle_message = f"{self.player_monster['name']} used {move_name}! Dealt {damage} damage!"
            self._update_battle_text()
            
            eff_msg = get_effectiveness_message(type_mult)
            if eff_msg:
                self.effectiveness_text = Text(eff_msg, 18, "black")
                self.effectiveness_text.rect.topleft = (50, 85)
            else:
                self.effectiveness_text = Text("", 18, "black")
        
        self.wild_health_bar.set_hp(self.wild_pokemon["hp"], self.wild_pokemon["max_hp"])
        self._update_hp_text()
        
        if self.wild_pokemon["hp"] <= 0:
            self.battle_message = f"Wild {self.wild_pokemon['name']} fainted!"
            self._update_battle_text()
            self._on_wild_defeated()
            return
            
        self.is_player_turn = False
        self.wild_attack_timer = 2.0

    def _on_wild_defeated(self):
        """Handle wild Pokemon defeat - award XP, coins, level up, check evolution."""
        if not self.player_monster:
            self.battle_over = True
            self.victory_timer = 2.0
            return
        
        # Calculate and award XP
        xp_gained = calculate_xp_reward(self.wild_pokemon)
        current_xp = self.player_monster.get("xp", 0)
        current_level = self.player_monster.get("level", 1)
        
        # Calculate and award coins
        coins_gained = calculate_coin_reward(self.wild_pokemon, is_trainer=False)
        if self.game_manager:
            self.game_manager.bag.add_item("Coins", coins_gained, "ingame_ui/coin.png")
            Logger.info(f"Awarded {coins_gained} coins!")
        
        # Store for victory screen
        self.xp_gained = xp_gained
        self.coins_gained = coins_gained
        
        # Initialize XP if not present
        if "xp" not in self.player_monster:
            self.player_monster["xp"] = calculate_xp_for_level(current_level)
        
        self.player_monster["xp"] = self.player_monster.get("xp", 0) + xp_gained
        
        # Check for level ups
        levels_gained = 0
        xp_needed = calculate_xp_for_level(current_level + 1)
        
        while self.player_monster["xp"] >= xp_needed and current_level < 100:
            levels_gained += 1
            current_level += 1
            xp_needed = calculate_xp_for_level(current_level + 1)
        
        if levels_gained > 0:
            self.leveled_up = True
            old_level = self.player_monster["level"]
            self.player_monster["level"] = current_level
            
            # Apply stat scaling for each level gained
            apply_stat_scaling(self.player_monster, levels_gained)
            
            # Update health bar to reflect new max HP
            self.player_health_bar.set_hp(
                self.player_monster["hp"],
                self.player_monster["max_hp"]
            )
            
            self.battle_message = f"{self.player_monster['name']} gained {xp_gained} XP, {coins_gained} coins and leveled up to Lv.{current_level}!"
            self._update_battle_text()
            self._update_hp_text()
            self._update_player_level_text()
            
            Logger.info(f"{self.player_monster['name']} leveled up! {old_level} -> {current_level}")
            Logger.info(f"  Stats: HP={self.player_monster['max_hp']}, ATK={self.player_monster.get('attack', 10)}, DEF={self.player_monster.get('defense', 10)}")
            
            # Check for evolution after level up - store for game scene to handle with animation
            evolution = check_evolution(self.player_monster)
            if evolution:
                new_name, new_sprite = evolution
                old_name = self.player_monster['name']
                old_sprite = self.player_monster.get('sprite_path', '')
                set_pending_evolution(self.player_monster, old_name, new_name, old_sprite, new_sprite)
                Logger.info(f"Evolution pending: {old_name} -> {new_name}")
        else:
            self.leveled_up = False
            # Just show XP and coins gained
            xp_to_next = calculate_xp_for_level(current_level + 1) - self.player_monster["xp"]
            self.battle_message = f"{self.player_monster['name']} gained {xp_gained} XP and {coins_gained} coins!"
            self._update_battle_text()
        
        self.battle_over = True
        self.show_victory_screen = True
        self.victory_screen_timer = 3.0

    def _reload_player_sprite(self):
        """Reload player's Pokemon sprite after evolution."""
        if not self.player_monster:
            return
            
        sprite_path = self.player_monster.get("sprite") or self.player_monster.get("sprite_path")
        if sprite_path:
            try:
                self.player_monster_sprite = Sprite(
                    sprite_path,
                    (GameSettings.TILE_SIZE * 9, GameSettings.TILE_SIZE * 9)
                )
                
                self.player_monster_sprite.image = pg.transform.flip(
                    self.player_monster_sprite.image, 
                    True,
                    False
                )
                
                player_x = GameSettings.SCREEN_WIDTH // 4 + 80
                player_y = GameSettings.SCREEN_HEIGHT // 2 + 50
                self.player_monster_sprite.rect.center = (player_x, player_y)
                
                # Update name text
                self.player_name_text = Text(self.player_monster["name"], 20, "black")
                self.player_name_text.rect.topleft = (GameSettings.SCREEN_WIDTH // 4 - 100, GameSettings.SCREEN_HEIGHT - 125)
                
                # Update element display
                element = self.player_monster.get("element", "Normal")
                color = ELEMENT_COLORS_DISPLAY.get(element, (128, 128, 128))
                self.player_element_text = Text(element, 16, color)
                self.player_element_text.rect.topleft = (GameSettings.SCREEN_WIDTH // 4 - 100, GameSettings.SCREEN_HEIGHT - 145)
                
                # Update battle UI
                self.battle_ui.set_player_pokemon(self.player_monster)
                
            except Exception as e:
                Logger.error(f"Failed to reload player Pokemon sprite: {e}")

    def _update_player_level_text(self):
        """Update player level text display."""
        if self.player_monster:
            self.player_level_text = Text(f"Lv. {self.player_monster['level']}", 18, "black")
            self.player_level_text.rect.topright = (GameSettings.SCREEN_WIDTH // 4 + 100, GameSettings.SCREEN_HEIGHT - 125)

    def _wild_attack(self):
        """Wild Pokemon attacks the player with a random move."""
        if not self.player_monster or not self.wild_pokemon or self.battle_over:
            return
        
        # Get wild Pokemon moves
        wild_moves = get_pokemon_moves(self.wild_pokemon)
        available_moves = [m for m in wild_moves if m.get("pp", 0) > 0]
        
        if not available_moves:
            move = {"name": "Struggle", "type": "Normal", "power": 50, "accuracy": 100, "pp": 999, "max_pp": 999, "category": "physical"}
        else:
            move = random.choice(available_moves)
        
        move_name = move.get("name", "Attack")
        move["pp"] = max(0, move.get("pp", 0) - 1)
        
        damage, type_mult = self._calculate_damage_with_move(self.wild_pokemon, self.player_monster, move)
        
        if damage == 0:
            self.battle_message = f"Wild {self.wild_pokemon['name']}'s {move_name} missed!"
            self._update_battle_text()
            self.effectiveness_text = Text("", 18, "black")
        else:
            self.player_monster["hp"] = max(0, self.player_monster["hp"] - damage)
            self.battle_message = f"Wild {self.wild_pokemon['name']} used {move_name}! {damage} damage!"
            self._update_battle_text()
            
            eff_msg = get_effectiveness_message(type_mult)
            if eff_msg:
                self.effectiveness_text = Text(eff_msg, 18, "black")
                self.effectiveness_text.rect.topleft = (50, 85)
            else:
                self.effectiveness_text = Text("", 18, "black")
        
        self.player_health_bar.set_hp(self.player_monster["hp"], self.player_monster["max_hp"])
        self._update_hp_text()
        
        if self.player_monster["hp"] <= 0:
            self.battle_message = f"{self.player_monster['name']} fainted!"
            self._update_battle_text()
            
            # Check if player has other alive Pokemon
            if self.game_manager:
                all_monsters = self.game_manager.bag.monsters
                alive_monsters = [m for m in all_monsters if m.get("hp", 0) > 0]
                
                if alive_monsters:
                    # Force switch to another Pokemon
                    self.message_delay_timer = 1.5
                    self._force_switch_pokemon()
                    return
            
            # No alive Pokemon left - battle lost
            self.battle_over = True
            self.show_defeat_screen = True
            self.victory_screen_timer = 3.0
            return
            
        self.is_player_turn = True
        self.message_delay_timer = 2.0

    def _calculate_catch_chance(self) -> float:
        """Calculate catch chance based on wild Pokemon's HP."""
        if not self.wild_pokemon:
            return 0.0
        
        hp_percentage = self.wild_pokemon["hp"] / self.wild_pokemon["max_hp"]
        base_rate = 0.3
        hp_bonus = (1 - hp_percentage) * 0.6
        
        return min(base_rate + hp_bonus, 0.95)

    def _attempt_catch(self):
        """Attempt to catch the wild Pokemon."""
        if not self.wild_pokemon or self.battle_over:
            return
        
        # Check if player has Pokeballs
        pokeball_count = self.game_manager.bag.get_item_count("Pokeball")
        
        if pokeball_count <= 0:
            self.battle_message = "No Pokeballs left!"
            self._update_battle_text()
            return
        
        # Use a Pokeball
        self.game_manager.bag.remove_item("Pokeball")
        
        # Calculate catch chance
        catch_chance = self._calculate_catch_chance()
        roll = random.random()
        
        Logger.info(f"Catch attempt: {catch_chance:.2%} chance, rolled {roll:.2f}")
        
        if roll < catch_chance:
            # Success!
            # Add to bag with full Pokemon data including element and XP
            caught_pokemon = {
                "name": self.wild_pokemon["name"],
                "max_hp": self.wild_pokemon["max_hp"],
                "hp": self.wild_pokemon["hp"],
                "level": self.wild_pokemon["level"],
                "sprite_path": self.wild_pokemon.get("sprite_path", "menu_sprites/unknown.png"),
                "attack": self.wild_pokemon.get("attack", 10),
                "defense": self.wild_pokemon.get("defense", 10),
                "element": self.wild_pokemon.get("element", "Normal"),
                "xp": calculate_xp_for_level(self.wild_pokemon["level"]),  # Initialize XP for caught Pokemon
            }
            
            # Check if party is full
            if self.game_manager.bag.is_party_full():
                # Try to send to PC
                if hasattr(self.game_manager, 'pc_storage') and self.game_manager.pc_storage:
                    if self.game_manager.pc_storage.deposit(caught_pokemon):
                        self.battle_message = f"Gotcha! {self.wild_pokemon['name']} was sent to the PC!"
                        Logger.info(f"Caught {caught_pokemon['name']} - sent to PC (party full)")
                    else:
                        self.battle_message = f"Caught {self.wild_pokemon['name']}! But PC is full... it ran away!"
                        Logger.warning(f"Caught {caught_pokemon['name']} but PC is full!")
                else:
                    # No PC storage available, just add to party anyway (shouldn't happen)
                    self.game_manager.bag.add_monster(caught_pokemon)
                    self.battle_message = f"Gotcha! {self.wild_pokemon['name']} was caught!"
            else:
                # Party has room
                self.game_manager.bag.add_monster(caught_pokemon)
                self.battle_message = f"Gotcha! {self.wild_pokemon['name']} was caught!"
                Logger.info(f"Caught {caught_pokemon['name']} ({caught_pokemon['element']})!")
            
            self._update_battle_text()
            self.pokemon_caught = True
            self.battle_over = True
            self.victory_timer = 2.0
        else:
            # Failed
            self.battle_message = f"{self.wild_pokemon['name']} broke free!"
            self._update_battle_text()
            
            self.is_player_turn = False
            self.wild_attack_timer = 2.0

    def _on_attack(self):
        """Handle attack button press - show move selection."""
        if self.show_moves or self.switch_pokemon_ui.overlay_show:
            return
        if self.is_player_turn and not self.battle_over:
            self.show_moves = True
            self.battle_ui.show_moves = True
            self._setup_move_buttons()
            
            # Reset input to prevent carried clicks
            input_manager.reset()

    def _on_catch(self):
        """Handle catch button press."""
        if self.show_moves or self.switch_pokemon_ui.overlay_show:
            return
        if self.is_player_turn and not self.battle_over:
            self._attempt_catch()

    def _on_run(self):
        """Handle run button press."""
        if self.show_moves or self.switch_pokemon_ui.overlay_show:
            return
        if self.battle_over:
            return
            
        if self.is_player_turn:
            if random.random() < 0.75:
                self.battle_message = "Got away safely!"
                self._update_battle_text()
                self.escape_timer = 1.5
            else:
                self.battle_message = "Can't escape!"
                self._update_battle_text()
                self.is_player_turn = False
                self.wild_attack_timer = 2.0

    def _on_switch(self):
        """Handle switch button press - open switch Pokemon UI."""
        if self.show_moves or self.switch_pokemon_ui.overlay_show:
            return
        if self.battle_over:
            return
        if not self.is_player_turn:
            return
            
        if self.game_manager:
            try:
                all_monsters = self.game_manager.bag.monsters
                Logger.info(f"Switch button pressed, monsters in party: {len(all_monsters) if all_monsters else 0}")
                if all_monsters and len(all_monsters) > 0:
                    self.switch_pokemon_ui.open(
                        monsters=all_monsters,
                        current_monster=self.player_monster,
                        force_switch=False
                    )
                else:
                    Logger.warning("No monsters in party to switch!")
            except Exception as e:
                Logger.error(f"Error opening switch UI: {e}")
        else:
            Logger.warning("No game_manager when trying to switch!")

    def _on_pokemon_switched(self, new_monster: Monster):
        """Called when a Pokemon is selected from the switch UI."""
        if new_monster == self.player_monster:
            return
            
        self.player_monster = new_monster
        self._reload_player_sprite()
        self._setup_move_buttons()
        
        # Initialize XP if not present
        if "xp" not in self.player_monster:
            self.player_monster["xp"] = calculate_xp_for_level(self.player_monster.get("level", 1))
        
        self.battle_message = f"Go, {self.player_monster['name']}!"
        self._update_battle_text()
        
        # If this was a forced switch (Pokemon fainted), don't skip turn
        if not self.switch_pokemon_ui.force_switch:
            self.is_player_turn = False
            self.wild_attack_timer = 1.5
        else:
            # After forced switch, it's still player's turn
            self.message_delay_timer = 1.5

    def _on_switch_cancelled(self):
        """Called when switch is cancelled."""
        pass  # Just close the UI, handled by SwitchPokemonUI

    def _force_switch_pokemon(self):
        """Force open the switch UI when current Pokemon faints."""
        if self.game_manager:
            all_monsters = self.game_manager.bag.monsters
            if all_monsters:
                self.switch_pokemon_ui.open(
                    monsters=all_monsters,
                    current_monster=self.player_monster,
                    force_switch=True
                )

    def _update_battle_text(self):
        """Update the battle message text."""
        self.battle_text = Text(self.battle_message, 20, "black")
        self.battle_text.rect.topleft = (50, 55)
        # Update battle UI message
        self.battle_ui.set_message(self.battle_message, self.effectiveness_message)

    def _update_hp_text(self):
        """Update HP display text."""
        if self.wild_pokemon:
            self.wild_hp_text = Text(
                f"HP: {self.wild_pokemon['hp']}/{self.wild_pokemon['max_hp']}", 
                18, "black"
            )
            self.wild_hp_text.rect.topleft = (GameSettings.SCREEN_WIDTH * 3 // 4 - 100, 75)
            # Update battle UI
            self.battle_ui.update_enemy_hp(self.wild_pokemon['hp'], self.wild_pokemon['max_hp'])
            
        if self.player_monster:
            self.player_hp_text = Text(
                f"HP: {self.player_monster['hp']}/{self.player_monster['max_hp']}", 
                18, "black"
            )
            self.player_hp_text.rect.topleft = (GameSettings.SCREEN_WIDTH // 4 - 100, GameSettings.SCREEN_HEIGHT - 100)
            # Update battle UI
            self.battle_ui.update_player_hp(self.player_monster['hp'], self.player_monster['max_hp'])

    def _load_sprites(self):
        """Load Pokemon sprites."""
        Logger.info("Loading battle sprites...")
        
        if not self.wild_pokemon:
            Logger.error("No wild Pokemon to load!")
            return
        
        sprite_path = self.wild_pokemon.get("sprite") or self.wild_pokemon.get("sprite_path")
        Logger.info(f"Wild Pokemon: {self.wild_pokemon.get('name')}, sprite: {sprite_path}")
        
        if sprite_path:
            try:
                self.wild_pokemon_sprite = Sprite(
                    sprite_path, 
                    (GameSettings.TILE_SIZE * 9, GameSettings.TILE_SIZE * 9)
                )
                # Position wild sprite below its info card
                wild_x = GameSettings.SCREEN_WIDTH - 150  # Center aligned with card
                wild_y = 250  # Just below info card
                self.wild_pokemon_sprite.rect.center = (wild_x, wild_y)
                
                self.wild_health_bar.set_hp(
                    self.wild_pokemon["hp"],
                    self.wild_pokemon["max_hp"]
                )
                
                self.wild_name_text = Text(self.wild_pokemon["name"], 20, "black")
                self.wild_name_text.rect.topleft = (GameSettings.SCREEN_WIDTH * 3 // 4 - 100, 50)
                
                self.wild_level_text = Text(f"Lv. {self.wild_pokemon['level']}", 18, "black")
                self.wild_level_text.rect.topright = (GameSettings.SCREEN_WIDTH * 3 // 4 + 100, 50)
                
                # Element type display
                element = self.wild_pokemon.get("element", "Normal")
                color = ELEMENT_COLORS_DISPLAY.get(element, (128, 128, 128))
                self.wild_element_text = Text(element, 16, color)
                self.wild_element_text.rect.topleft = (GameSettings.SCREEN_WIDTH * 3 // 4 - 100, 30)
                
                # Update battle UI
                self.battle_ui.set_enemy_pokemon(self.wild_pokemon)
                
                Logger.info(f"Wild Pokemon sprite loaded successfully")
            except Exception as e:
                Logger.error(f"Failed to load wild Pokemon sprite: {e}")
        
        # Load player's Pokemon
        if self.game_manager:
            Logger.info(f"Loading player Pokemon from bag...")
            self.player_monster = self.game_manager.bag.get_first_alive_monster()
            
            # If no alive Pokemon, flag for exit with professor message
            if not self.player_monster:
                Logger.warning("No alive Pokemon in party!")
                self.no_alive_pokemon = True
                self.battle_message = "You have no Pokemon that can fight!"
                self._update_battle_text()
                return
            
            if self.player_monster:
                Logger.info(f"Player Pokemon: {self.player_monster.get('name')}, HP: {self.player_monster.get('hp')}/{self.player_monster.get('max_hp')}")
                
                # Initialize XP if not present
                if "xp" not in self.player_monster:
                    self.player_monster["xp"] = calculate_xp_for_level(self.player_monster.get("level", 1))
                
                # Initialize moves for player's Pokemon
                get_pokemon_moves(self.player_monster)
                self._setup_move_buttons()
                
                sprite_path = self.player_monster.get("sprite") or self.player_monster.get("sprite_path")
                Logger.info(f"Player sprite path: {sprite_path}")
                
                if sprite_path:
                    try:
                        self.player_monster_sprite = Sprite(
                            sprite_path,
                            (GameSettings.TILE_SIZE * 9, GameSettings.TILE_SIZE * 9)
                        )
                        
                        self.player_monster_sprite.image = pg.transform.flip(
                            self.player_monster_sprite.image, 
                            True,
                            False
                        )
                        
                        player_x = GameSettings.SCREEN_WIDTH // 4 + 80
                        player_y = GameSettings.SCREEN_HEIGHT // 2 + 50
                        self.player_monster_sprite.rect.center = (player_x, player_y)
                        
                        self.player_health_bar.set_hp(
                            self.player_monster["hp"],
                            self.player_monster["max_hp"]
                        )
                        
                        self.player_name_text = Text(self.player_monster["name"], 20, "black")
                        self.player_name_text.rect.topleft = (GameSettings.SCREEN_WIDTH // 4 - 100, GameSettings.SCREEN_HEIGHT - 125)
                        
                        self.player_level_text = Text(f"Lv. {self.player_monster['level']}", 18, "black")
                        self.player_level_text.rect.topright = (GameSettings.SCREEN_WIDTH // 4 + 100, GameSettings.SCREEN_HEIGHT - 125)
                        
                        # Element type display
                        element = self.player_monster.get("element", "Normal")
                        color = ELEMENT_COLORS_DISPLAY.get(element, (128, 128, 128))
                        self.player_element_text = Text(element, 16, color)
                        self.player_element_text.rect.topleft = (GameSettings.SCREEN_WIDTH // 4 - 100, GameSettings.SCREEN_HEIGHT - 145)
                        
                        # Update battle UI
                        self.battle_ui.set_player_pokemon(self.player_monster)
                        
                        Logger.info(f"Player Pokemon sprite loaded successfully")
                    except Exception as e:
                        Logger.error(f"Failed to load player Pokemon sprite: {e}")
        else:
            Logger.error("No game_manager available!")
        
        self._update_hp_text()

    @override
    def enter(self, data: Any = None) -> None:
        """Called when entering the wild Pokemon scene."""
        Logger.info("Entering WildPokemonScene...")
        sound_manager.play_bgm("RBY 107 Battle! (Trainer).ogg")
        
        self.game_manager = data
        if not self.game_manager:
            Logger.error("WildPokemonScene entered without game_manager!")
        
        self.wild_pokemon = self._generate_wild_pokemon()
        Logger.info(f"Generated wild Pokemon: {self.wild_pokemon.get('name') if self.wild_pokemon else 'None'}")
        
        self.is_player_turn = True
        self.battle_over = False
        self.pokemon_caught = False
        self.show_moves = False
        self.evolution_pending = False
        self.evolution_timer = 0
        self.evolution_new_name = ""
        self.no_alive_pokemon = False  # Flag for no alive Pokemon
        self.battle_message = f"A wild {self.wild_pokemon['name']} appeared!"
        self.wild_attack_timer = 0
        self.escape_timer = 0
        self.message_delay_timer = 0
        self.victory_timer = 0
        self.effectiveness_text = Text("", 18, "black")
        self._update_battle_text()
        
        self._load_sprites()
        
        # If no alive Pokemon, set flag to exit with professor message
        if self.no_alive_pokemon:
            self.battle_over = True
            self.victory_timer = 0.5  # Quick exit
            # Set flag for game_scene to show professor dialog
            global need_professor_heal_dialog
            need_professor_heal_dialog = True
        
        Logger.info("WildPokemonScene enter complete")

    @override
    def exit(self) -> None:
        self.wild_attack_timer = 0
        self.escape_timer = 0
        self.message_delay_timer = 0
        self.victory_timer = 0
        self.evolution_timer = 0
        self.evolution_pending = False
        self.wild_pokemon_sprite = None
        self.player_monster_sprite = None
        self.wild_pokemon = None
        self.player_monster = None
        self.show_moves = False
        self.show_defeat_screen = False
        self.show_victory_screen = False
        self.victory_screen_timer = 0
        self.battle_ui.show_moves = False

    @override
    def update(self, dt: float) -> None:
        # Update switch Pokemon UI
        self.switch_pokemon_ui.update(dt)
        self.battle_ui.update(dt)
        
        # Block other updates if switch UI is open
        if self.switch_pokemon_ui.overlay_show:
            return
        
        # Handle victory/defeat screen timer
        if self.show_victory_screen or self.show_defeat_screen:
            self.victory_screen_timer -= dt
            if self.victory_screen_timer <= 0:
                scene_manager.change_scene("game")
            return
        
        # Handle victory timer (for catching/running)
        if self.victory_timer > 0:
            self.victory_timer -= dt
            if self.victory_timer <= 0:
                self.victory_timer = 0
                scene_manager.change_scene("game")
                return
        
        if self.wild_attack_timer > 0:
            self.wild_attack_timer -= dt
            if self.wild_attack_timer <= 0:
                self.wild_attack_timer = 0
                self._wild_attack()
        
        if self.message_delay_timer > 0:
            self.message_delay_timer -= dt
            if self.message_delay_timer <= 0:
                self.message_delay_timer = 0
                self.battle_message = "What will you do?"
                self._update_battle_text()
                self.effectiveness_text = Text("", 18, "black")
                self.effectiveness_message = ""
        
        if self.escape_timer > 0:
            self.escape_timer -= dt
            if self.escape_timer <= 0:
                self.escape_timer = 0
                scene_manager.change_scene("game")
        
        # Handle clicks for the new UI
        if input_manager.mouse_pressed(1):
            mouse_pos = pg.mouse.get_pos()
            if self.victory_timer <= 0 and ((self.is_player_turn and not self.battle_over) or self.battle_over):
                self.battle_ui.handle_click(mouse_pos)

    @override
    def draw(self, screen: pg.Surface) -> None:
        self.background.draw(screen)
        
        if self.wild_pokemon_sprite:
            self.wild_pokemon_sprite.draw(screen)
        
        if self.player_monster_sprite:
            self.player_monster_sprite.draw(screen)
        
        # Draw defeat screen
        if self.show_defeat_screen:
            self.battle_ui.draw_defeat_screen(screen, "All your Pokemon have fainted!")
            self.switch_pokemon_ui.draw(screen)
            return
        
        # Draw victory screen
        if self.show_victory_screen:
            self.battle_ui.draw_victory_screen(
                screen,
                f"Defeated {self.wild_pokemon.get('name', 'the wild Pokemon')}!",
                xp_gained=self.xp_gained,
                leveled_up=self.leveled_up,
                coins_gained=self.coins_gained
            )
            self.switch_pokemon_ui.draw(screen)
            return
        
        # Draw the modern battle UI
        self.battle_ui.draw(screen)
        
        # Draw switch Pokemon UI (on top of everything)
        self.switch_pokemon_ui.draw(screen)


# Helper function to set water Pokemon requirement
def set_need_water_pokemon(need: bool):
    """Set whether we need to guarantee water Pokemon spawns."""
    global encounter_tracker
    encounter_tracker["need_water_pokemon"] = need
    encounter_tracker["encounters_since_water"] = 0
    Logger.info(f"Water Pokemon requirement set to: {need}")