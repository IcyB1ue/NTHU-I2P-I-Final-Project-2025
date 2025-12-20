import pygame as pg
from typing import override, Any
import random

from src.utils import GameSettings, Logger
from src.utils.definition import (
    Monster, get_type_multiplier, get_effectiveness_message,
    check_evolution, evolve_monster, ElementType, Move,
    get_pokemon_moves, MOVE_DATABASE
)
from src.sprites import BackgroundSprite, Sprite
from src.scenes.scene import Scene
from src.interface.components import Button
from src.interface.battle_items_ui import BattleItemsUI
from src.core.services import scene_manager, sound_manager, input_manager
from src.sprites.sprite import Text
from src.entities.enemy_trainer import EnemyTrainer
from src.interface.switch_pokemon_ui import SwitchPokemonUI
from src.interface.battle_ui import BattleUI


# Monster sprite size (larger scale)
MONSTER_SPRITE_SIZE = GameSettings.TILE_SIZE * 9

# Flag to trigger professor "no alive pokemon" dialog
need_professor_heal_dialog = False

# Pending evolution data: (monster_data, old_name, new_name, old_sprite, new_sprite)
pending_evolution_data = None


def get_need_professor_heal_dialog_battle() -> bool:
    """Get and reset the professor heal dialog flag for battle scene."""
    global need_professor_heal_dialog
    result = need_professor_heal_dialog
    need_professor_heal_dialog = False
    return result


def get_pending_evolution() -> tuple | None:
    """Get and reset pending evolution data."""
    global pending_evolution_data
    result = pending_evolution_data
    pending_evolution_data = None
    return result


def set_pending_evolution(monster: dict, old_name: str, new_name: str, 
                          old_sprite: str, new_sprite: str):
    """Set pending evolution data to be handled by game scene."""
    global pending_evolution_data
    pending_evolution_data = (monster, old_name, new_name, old_sprite, new_sprite)


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

# Global flag to track if player won the last trainer battle
last_battle_result = {
    "player_won": False,
    "was_trainer_battle": False,
    "is_gym_leader": False,  # Track if battle was against a gym leader
    "is_corrupted": False    # Track if battle was against a corrupted trainer
}


# ============== XP SYSTEM ==============

def calculate_xp_reward(defeated_pokemon: Monster, is_trainer_battle: bool = False) -> int:
    """Calculate XP reward from defeating a Pokemon.
    Trainer battles give 1.5x XP bonus.
    """
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
    
    total = base_xp + level_bonus + type_bonus
    
    # Trainer battle bonus
    if is_trainer_battle:
        total = int(total * 1.5)
    
    return total


def calculate_xp_for_level(level: int) -> int:
    """Calculate total XP needed to reach a level."""
    # Simple quadratic formula: XP = 100 * level^1.5
    return int(100 * (level ** 1.5))


def calculate_xp_to_next_level(current_level: int) -> int:
    """Calculate XP needed to go from current level to next."""
    return calculate_xp_for_level(current_level + 1) - calculate_xp_for_level(current_level)


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
        
        # Trigger on mouse released (single click)
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


class BattleScene(Scene):
    def __init__(self):
        super().__init__()
        self.background = BackgroundSprite("backgrounds/background2.png")
        self.enemy_trainer = None
        self.enemy_monster = None
        self.player_monster = None
        self.enemy_monster_sprite = None
        self.player_monster_sprite = None
        self.is_player_turn = True
        self.battle_over = False
        self.player_won = False
        self.battle_message = "What will you do?"
        self.enemy_attack_timer = 0
        self.run_away_timer = 0
        self.message_delay_timer = 0
        self.evolution_pending = False
        self.evolution_timer = 0
        self.victory_timer = 0
        
        # Message queue for sequential messages
        self.message_queue: list[str] = []
        self.message_display_timer = 0
        self.message_display_duration = 1.5
        
        # Victory/Defeat state
        self.show_victory_screen = False
        self.show_defeat_screen = False
        self.victory_screen_timer = 0
        
        # Move selection state
        self.show_moves = False
        self.selected_move: Move | None = None
        
        # Text attributes (kept for compatibility)
        self.enemy_name_text = None
        self.enemy_level_text = None
        self.enemy_hp_text = None
        self.enemy_element_text = None
        self.player_name_text = None
        self.player_level_text = None
        self.player_hp_text = None
        self.player_element_text = None
        
        # Victory text
        self.victory_text = None
        self.level_up_text = None
        self.xp_text = None
        self.xp_gained = 0
        self.leveled_up = False

        # Create health bars (kept for compatibility, but using BattleUI now)
        self.enemy_health_bar = HealthBar(GameSettings.SCREEN_WIDTH * 3 // 4 - 100, 100)
        self.player_health_bar = HealthBar(GameSettings.SCREEN_WIDTH // 4 - 100, GameSettings.SCREEN_HEIGHT - 75)

        # Create the Banner (legacy - using BattleUI message box now)
        self.game_announcement_banner_sprite = Sprite("UI/raw/UI_Flat_Banner04a.png", (450, 200))
        self.game_announcement_banner_sprite.rect.topleft = (20, 20)
        
        # Battle message text (legacy)
        self.battle_text = Text(self.battle_message, 24, "black")
        self.battle_text.rect.topleft = (30, 30)
        
        # Secondary message for effectiveness
        self.effectiveness_text = Text("", 18, "black")
        self.effectiveness_text.rect.topleft = (50, 80)
        self.effectiveness_message = ""

        # Battle items UI
        self.battle_items_ui = BattleItemsUI(on_item_used=self._on_item_used)

        # Switch Pokemon UI
        self.switch_pokemon_ui = SwitchPokemonUI(
            on_switch=self._on_pokemon_switched,
            on_cancel=self._on_switch_cancelled
        )

        # === NEW MODERN BATTLE UI ===
        self.battle_ui = BattleUI(is_trainer_battle=True)
        self.battle_ui.set_callbacks(
            fight_cb=self._on_attack,
            run_cb=self._on_run,
            switch_cb=self._on_switch,
            items_cb=self._on_items,
            back_cb=self._on_back,
            move_cb=self._on_move_selected
        )
        
        # Create move buttons for the new UI (handled by BattleUI)
        self.move_buttons: list[MoveButton] = []
        
        # Legacy buttons (kept for reference but not used)
        px, py = GameSettings.SCREEN_WIDTH // 2, GameSettings.SCREEN_HEIGHT * 3 // 4
        
        self.attack_button = Button(
            "UI/raw/UI_Flat_Button02a_3.png", "UI/raw/UI_Flat_Button02a_2.png",
            px + 50, py - 50, 200, 100,
            self._on_attack
        )
        self.attack_text = Text("Fight", 30, "black")
        self.attack_text.rect.center = (px + 150, py)

        self.run_button = Button(
            "UI/raw/UI_Flat_Button02a_3.png", "UI/raw/UI_Flat_Button02a_2.png",
            px + 250, py - 50, 200, 100,
            self._on_run
        )
        self.run_text = Text("Run", 30, "black")
        self.run_text.rect.center = (px + 350, py)

        self.switch_button = Button(
            "UI/raw/UI_Flat_Button02a_3.png", "UI/raw/UI_Flat_Button02a_2.png",
            px + 50, py + 45, 200, 100,
            self._on_switch
        )
        self.switch_text = Text("Switch", 30, "black")
        self.switch_text.rect.center = (px + 150, py + 95)

        self.items_button = Button(
            "UI/raw/UI_Flat_Button02a_3.png", "UI/raw/UI_Flat_Button02a_2.png",
            px + 250, py + 45, 200, 100,
            self._on_items
        )
        self.items_text = Text("Items", 30, "black")
        self.items_text.rect.center = (px + 350, py + 95)
        
        # Back button for move selection
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

    def _calculate_damage_with_move(self, attacker: Monster, defender: Monster, move: Move) -> tuple[int, float]:
        """Calculate damage based on monster stats, move power, and element types."""
        attack_stat = attacker.get("attack", 10)
        defense_stat = defender.get("defense", 5)
        level = attacker.get("level", 1)
        
        move_power = move.get("power", 40)
        move_type = move.get("type", "Normal")
        accuracy = move.get("accuracy", 100)
        
        if random.randint(1, 100) > accuracy:
            return 0, 1.0
        
        defender_type = defender.get("element", "Normal")
        type_multiplier = get_type_multiplier(move_type, defender_type)
        
        attacker_type = attacker.get("element", "Normal")
        stab = 1.5 if move_type == attacker_type else 1.0
        
        random_factor = random.uniform(0.85, 1.0)
        
        base = ((2 * level / 5 + 2) * move_power * attack_stat / defense_stat / 50 + 2)
        damage = int(base * type_multiplier * stab * random_factor)
        
        return max(1, damage), type_multiplier

    def _player_attack_with_move(self, move: Move):
        """Player attacks with a specific move."""
        if not self.player_monster or not self.enemy_monster or self.battle_over:
            return
        
        move["pp"] = max(0, move.get("pp", 0) - 1)
        
        move_name = move.get("name", "Attack")
        damage, type_mult = self._calculate_damage_with_move(self.player_monster, self.enemy_monster, move)
        
        if damage == 0:
            self.battle_message = f"{self.player_monster['name']} used {move_name}! But it missed!"
            self._update_battle_text()
            self.effectiveness_text = Text("", 18, "black")
        else:
            self.enemy_monster["hp"] = max(0, self.enemy_monster["hp"] - damage)
            self.battle_message = f"{self.player_monster['name']} used {move_name}! Dealt {damage} damage!"
            self._update_battle_text()
            
            eff_msg = get_effectiveness_message(type_mult)
            if eff_msg:
                self.effectiveness_text = Text(eff_msg, 18, "black")
                self.effectiveness_text.rect.topleft = (50, 85)
            else:
                self.effectiveness_text = Text("", 18, "black")
        
        self.enemy_health_bar.set_hp(self.enemy_monster["hp"], self.enemy_monster["max_hp"])
        self._update_hp_text()
        
        if self.enemy_monster["hp"] <= 0:
            self._on_enemy_defeated()
            return
        
        self.is_player_turn = False
        self.message_display_timer = 1.5
        self.enemy_attack_timer = 2.0

    def _player_attack(self):
        """Opens move selection menu."""
        if not self.player_monster or not self.enemy_monster or self.battle_over:
            return
            
        self.show_moves = True
        self.battle_ui.show_moves = True
        self._setup_move_buttons()
        
        # Reset input to prevent carried clicks
        input_manager.reset()

    def _on_enemy_defeated(self):
        """Handle enemy defeat - award XP, coins, level up, check evolution, show victory screen."""
        global last_battle_result
        
        self.player_won = True
        last_battle_result["player_won"] = True
        last_battle_result["was_trainer_battle"] = True
        # Track if this was a gym leader battle
        last_battle_result["is_gym_leader"] = self.enemy_trainer.is_gym_leader if self.enemy_trainer else False
        # Track if this was a corrupted trainer battle
        last_battle_result["is_corrupted"] = self.enemy_trainer.is_corrupted if self.enemy_trainer else False
        Logger.info(f"Player won the trainer battle! (gym_leader={last_battle_result['is_gym_leader']}, corrupted={last_battle_result['is_corrupted']})")
        
        # Start cooldown on the enemy trainer (5 minutes before can battle again)
        if self.enemy_trainer:
            self.enemy_trainer.start_cooldown()
        
        self.battle_over = True
        self.show_victory_screen = True
        self.victory_screen_timer = 3.0
        
        level_up_msg = None
        xp_msg = None
        coins_earned = 0
        
        # Calculate and award coins
        coins_earned = calculate_coin_reward(self.enemy_monster, is_trainer=True)
        if self.game_manager:
            self.game_manager.bag.add_item("Coins", coins_earned, "ingame_ui/coin.png")
            Logger.info(f"Awarded {coins_earned} coins for trainer battle!")
        
        if self.player_monster:
            # Initialize XP if not present
            if "xp" not in self.player_monster:
                self.player_monster["xp"] = calculate_xp_for_level(self.player_monster.get("level", 1))
            
            # Calculate and award XP (trainer battles give 1.5x bonus)
            xp_gained = calculate_xp_reward(self.enemy_monster, is_trainer_battle=True)
            self.xp_gained = xp_gained  # Store for victory screen
            current_level = self.player_monster.get("level", 1)
            
            self.player_monster["xp"] = self.player_monster.get("xp", 0) + xp_gained
            
            # Check for level ups
            levels_gained = 0
            xp_needed = calculate_xp_for_level(current_level + 1)
            
            while self.player_monster["xp"] >= xp_needed and current_level < 100:
                levels_gained += 1
                current_level += 1
                xp_needed = calculate_xp_for_level(current_level + 1)
            
            if levels_gained > 0:
                self.leveled_up = True  # Store for victory screen
                old_level = self.player_monster["level"]
                self.player_monster["level"] = current_level
                
                # Apply stat scaling for each level gained
                apply_stat_scaling(self.player_monster, levels_gained)
                
                # Update health bar to reflect new max HP
                self.player_health_bar.set_hp(
                    self.player_monster["hp"],
                    self.player_monster["max_hp"]
                )
                
                level_up_msg = f"{self.player_monster['name']} leveled up to Lv.{current_level}!"
                xp_msg = f"{self.player_monster['name']} gained {xp_gained} XP and {coins_earned} coins!"
                
                Logger.info(f"{self.player_monster['name']} leveled up! {old_level} -> {current_level}")
                Logger.info(f"  Stats: HP={self.player_monster['max_hp']}, ATK={self.player_monster.get('attack', 10)}, DEF={self.player_monster.get('defense', 10)}")
                
                # Check for evolution - store data for game scene to handle with animation
                evolution_result = check_evolution(self.player_monster)
                if evolution_result:
                    new_name, new_sprite = evolution_result
                    old_name = self.player_monster['name']
                    old_sprite = self.player_monster.get('sprite_path', '')
                    set_pending_evolution(self.player_monster, old_name, new_name, old_sprite, new_sprite)
                    Logger.info(f"Evolution pending: {old_name} -> {new_name}")
            else:
                self.leveled_up = False
                # Just show XP and coins gained
                xp_to_next = calculate_xp_for_level(current_level + 1) - self.player_monster["xp"]
                xp_msg = f"{self.player_monster['name']} gained {xp_gained} XP and {coins_earned} coins!"
        
        # Create victory text
        try:
            victory_font = pg.font.Font("assets/fonts/Pokemon Solid.ttf", 72)
        except:
            victory_font = pg.font.Font(None, 72)
        
        self.victory_text = victory_font.render("VICTORY!", True, (255, 215, 0))
        
        # Create level up text
        if level_up_msg:
            try:
                level_font = pg.font.Font("assets/fonts/Pokemon Solid.ttf", 32)
            except:
                level_font = pg.font.Font(None, 32)
            self.level_up_text = level_font.render(level_up_msg, True, (255, 255, 255))
        else:
            self.level_up_text = None
        
        # Create XP text
        if xp_msg:
            try:
                xp_font = pg.font.Font("assets/fonts/Pokemon Solid.ttf", 24)
            except:
                xp_font = pg.font.Font(None, 24)
            self.xp_text = xp_font.render(xp_msg, True, (200, 200, 255))
        else:
            self.xp_text = None

    def _on_player_defeated(self):
        """Handle player defeat - show defeat screen."""
        global last_battle_result
        
        self.player_won = False
        last_battle_result["player_won"] = False
        last_battle_result["was_trainer_battle"] = True
        # Track if this was a gym leader battle
        last_battle_result["is_gym_leader"] = self.enemy_trainer.is_gym_leader if self.enemy_trainer else False
        # Track if this was a corrupted trainer battle
        last_battle_result["is_corrupted"] = self.enemy_trainer.is_corrupted if self.enemy_trainer else False
        Logger.info(f"Player lost the trainer battle! (gym_leader={last_battle_result['is_gym_leader']}, corrupted={last_battle_result['is_corrupted']})")
        
        self.battle_over = True
        self.show_defeat_screen = True
        self.victory_screen_timer = 3.0
        
        try:
            defeat_font = pg.font.Font("assets/fonts/Pokemon Solid.ttf", 72)
        except:
            defeat_font = pg.font.Font(None, 72)
        
        self.victory_text = defeat_font.render("DEFEAT!", True, (255, 50, 50))
        self.level_up_text = None
        self.xp_text = None

    def _enemy_attack(self):
        """Enemy attacks the player monster with a random move."""
        if not self.player_monster or not self.enemy_monster or self.battle_over:
            return
        
        enemy_moves = get_pokemon_moves(self.enemy_monster)
        available_moves = [m for m in enemy_moves if m.get("pp", 0) > 0]
        
        if not available_moves:
            move = {"name": "Struggle", "type": "Normal", "power": 50, "accuracy": 100, "pp": 999, "max_pp": 999, "category": "physical"}
        else:
            move = random.choice(available_moves)
        
        move_name = move.get("name", "Attack")
        move["pp"] = max(0, move.get("pp", 0) - 1)
        
        damage, type_mult = self._calculate_damage_with_move(self.enemy_monster, self.player_monster, move)
        
        if damage == 0:
            self.battle_message = f"Enemy {self.enemy_monster['name']} used {move_name}! But it missed!"
            self._update_battle_text()
            self.effectiveness_text = Text("", 18, "black")
        else:
            self.player_monster["hp"] = max(0, self.player_monster["hp"] - damage)
            self.battle_message = f"Enemy {self.enemy_monster['name']} used {move_name}! Dealt {damage} damage!"
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
            if self.enemy_trainer and self.enemy_trainer.game_manager:
                all_monsters = self.enemy_trainer.game_manager.bag.monsters
                alive_monsters = [m for m in all_monsters if m.get("hp", 0) > 0]
                
                if alive_monsters:
                    # Force switch to another Pokemon
                    self.message_delay_timer = 1.5
                    self._force_switch_pokemon()
                    return
            
            # No alive Pokemon left - player loses
            self._on_player_defeated()
            return
        
        self.message_display_timer = 1.5
        self.message_delay_timer = 2.0

    def _update_battle_text(self):
        """Update the battle message text."""
        self.battle_text = Text(self.battle_message, 20, "black")
        self.battle_text.rect.topleft = (50, 55)
        # Update battle UI message
        self.battle_ui.set_message(self.battle_message, self.effectiveness_message)

    def _update_hp_text(self):
        """Update HP display text."""
        if self.enemy_monster:
            self.enemy_hp_text = Text(
                f"HP: {self.enemy_monster['hp']}/{self.enemy_monster['max_hp']}", 
                18, "black"
            )
            self.enemy_hp_text.rect.topleft = (GameSettings.SCREEN_WIDTH * 3 // 4 - 100, 75)
            # Update battle UI
            self.battle_ui.update_enemy_hp(self.enemy_monster['hp'], self.enemy_monster['max_hp'])
            
        if self.player_monster:
            self.player_hp_text = Text(
                f"HP: {self.player_monster['hp']}/{self.player_monster['max_hp']}", 
                18, "black"
            )
            self.player_hp_text.rect.topleft = (GameSettings.SCREEN_WIDTH // 4 - 100, GameSettings.SCREEN_HEIGHT - 100)
            # Update battle UI
            self.battle_ui.update_player_hp(self.player_monster['hp'], self.player_monster['max_hp'])

    def _on_attack(self):
        """Handle attack button press - show move selection."""
        if self.battle_items_ui.overlay_show or self.switch_pokemon_ui.overlay_show:
            return
        if self.battle_over or self.show_victory_screen or self.show_defeat_screen:
            return
        if self.is_player_turn:
            self._player_attack()

    def _on_run(self):
        """Handle run button press."""
        if self.battle_items_ui.overlay_show or self.switch_pokemon_ui.overlay_show:
            return
        if self.show_moves or self.show_victory_screen or self.show_defeat_screen:
            return
        if self.battle_over:
            self._exit_battle()
        else:
            global last_battle_result
            last_battle_result["player_won"] = False
            last_battle_result["was_trainer_battle"] = True
            self._exit_battle()

    def _on_switch(self):
        """Handle switch button press - open switch Pokemon UI."""
        if self.battle_items_ui.overlay_show or self.switch_pokemon_ui.overlay_show:
            return
        if self.show_moves or self.battle_over:
            return
        if not self.is_player_turn:
            return
            
        if self.enemy_trainer and self.enemy_trainer.game_manager:
            all_monsters = self.enemy_trainer.game_manager.bag.monsters
            if all_monsters:
                self.switch_pokemon_ui.open(
                    monsters=all_monsters,
                    current_monster=self.player_monster,
                    force_switch=False
                )

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
            self.message_display_timer = 1.0
            self.enemy_attack_timer = 1.5
        else:
            # After forced switch, it's still player's turn
            self.message_delay_timer = 1.5

    def _on_switch_cancelled(self):
        """Called when switch is cancelled."""
        pass  # Just close the UI, handled by SwitchPokemonUI

    def _force_switch_pokemon(self):
        """Force open the switch UI when current Pokemon faints."""
        if self.enemy_trainer and self.enemy_trainer.game_manager:
            all_monsters = self.enemy_trainer.game_manager.bag.monsters
            if all_monsters:
                self.switch_pokemon_ui.open(
                    monsters=all_monsters,
                    current_monster=self.player_monster,
                    force_switch=True
                )

    def _on_items(self):
        """Handle items button press."""
        if self.battle_items_ui.overlay_show or self.switch_pokemon_ui.overlay_show:
            return
        if self.show_moves or self.battle_over:
            return
        if self.is_player_turn:
            if self.enemy_trainer and self.enemy_trainer.game_manager:
                self.battle_items_ui.open(
                    self.enemy_trainer.game_manager.bag,
                    self.player_monster
                )

    def _on_item_used(self, item_name: str, item_info: dict):
        """Called when an item is used."""
        self.battle_message = f"Used {item_name}!"
        self._update_battle_text()
        self._update_hp_text()
        self.player_health_bar.set_hp(
            self.player_monster["hp"],
            self.player_monster["max_hp"]
        )
        self.is_player_turn = False
        self.message_display_timer = 1.0
        self.enemy_attack_timer = 1.5

    def _reload_player_sprite(self):
        """Reload the player monster sprite."""
        if not self.player_monster:
            return
        
        sprite_path = self.player_monster.get("sprite") or self.player_monster.get("sprite_path")
        if sprite_path:
            try:
                self.player_monster_sprite = Sprite(
                    sprite_path,
                    (MONSTER_SPRITE_SIZE, MONSTER_SPRITE_SIZE)
                )
                self.player_monster_sprite.image = pg.transform.flip(
                    self.player_monster_sprite.image, True, False
                )
                player_x = GameSettings.SCREEN_WIDTH // 4 + 80
                player_y = GameSettings.SCREEN_HEIGHT // 2 + 50
                self.player_monster_sprite.rect.center = (player_x, player_y)
                
                self.player_health_bar.set_hp(
                    self.player_monster.get("hp", 100),
                    self.player_monster.get("max_hp", 100)
                )
                
                self.player_name_text = Text(self.player_monster.get("name", "Unknown"), 20, "black")
                self.player_name_text.rect.topleft = (GameSettings.SCREEN_WIDTH // 4 - 100, GameSettings.SCREEN_HEIGHT - 125)
                
                self.player_level_text = Text(f"Lv. {self.player_monster.get('level', 1)}", 18, "black")
                self.player_level_text.rect.topright = (GameSettings.SCREEN_WIDTH // 4 + 100, GameSettings.SCREEN_HEIGHT - 125)
                
                element = self.player_monster.get("element", "Normal")
                color = ELEMENT_COLORS_DISPLAY.get(element, (128, 128, 128))
                self.player_element_text = Text(element, 16, color)
                self.player_element_text.rect.topleft = (GameSettings.SCREEN_WIDTH // 4 - 100, GameSettings.SCREEN_HEIGHT - 145)
                
                # Update battle UI
                self.battle_ui.set_player_pokemon(self.player_monster)
                
                self._update_hp_text()
            except Exception as e:
                Logger.error(f"Failed to reload player sprite: {e}")

    def _exit_battle(self):
        """Exit the battle."""
        scene_manager.change_scene("game")

    def _load_monster_sprites(self):
        """Load the monster sprites based on the enemy trainer's monster data."""
        if not self.enemy_trainer or not self.enemy_trainer.monsters:
            Logger.warning("No enemy monster data to load sprites")
            return

        self.enemy_monster = self.enemy_trainer.monsters
        
        if isinstance(self.enemy_monster, dict):
            sprite_path = self.enemy_monster.get("sprite") or self.enemy_monster.get("sprite_path")
            if sprite_path:
                try:
                    self.enemy_monster_sprite = Sprite(
                        sprite_path, 
                        (MONSTER_SPRITE_SIZE, MONSTER_SPRITE_SIZE)
                    )
                    # Position enemy sprite below its info card
                    enemy_x = GameSettings.SCREEN_WIDTH - 150  # Center aligned with card
                    enemy_y = 250  # Just below info card
                    self.enemy_monster_sprite.rect.center = (enemy_x, enemy_y)
                    
                    self.enemy_health_bar.set_hp(
                        self.enemy_monster.get("hp", 100),
                        self.enemy_monster.get("max_hp", 100)
                    )
                    
                    self.enemy_name_text = Text(self.enemy_monster.get("name", "Unknown"), 20, "black")
                    self.enemy_name_text.rect.topleft = (GameSettings.SCREEN_WIDTH * 3 // 4 - 100, 50)
                    
                    self.enemy_level_text = Text(f"Lv. {self.enemy_monster.get('level', 1)}", 18, "black")
                    self.enemy_level_text.rect.topright = (GameSettings.SCREEN_WIDTH * 3 // 4 + 100, 50)
                    
                    element = self.enemy_monster.get("element", "Normal")
                    color = ELEMENT_COLORS_DISPLAY.get(element, (128, 128, 128))
                    self.enemy_element_text = Text(element, 16, color)
                    self.enemy_element_text.rect.topleft = (GameSettings.SCREEN_WIDTH * 3 // 4 - 100, 30)
                    
                    get_pokemon_moves(self.enemy_monster)
                    
                    # Update battle UI
                    self.battle_ui.set_enemy_pokemon(self.enemy_monster)
                    
                    Logger.info(f"Loaded enemy monster sprite: {sprite_path}")
                except Exception as e:
                    Logger.error(f"Failed to load enemy monster sprite '{sprite_path}': {e}")
        
        if self.enemy_trainer and self.enemy_trainer.game_manager:
            self.player_monster = self.enemy_trainer.game_manager.bag.get_first_alive_monster()
            if self.player_monster:
                # Initialize XP if not present
                if "xp" not in self.player_monster:
                    self.player_monster["xp"] = calculate_xp_for_level(self.player_monster.get("level", 1))
                
                self._reload_player_sprite()
                get_pokemon_moves(self.player_monster)
                self._setup_move_buttons()
            else:
                # No alive Pokemon - flag for exit with professor message
                global need_professor_heal_dialog
                need_professor_heal_dialog = True
                self.no_alive_pokemon = True
                self.battle_message = "You have no Pokemon that can fight!"
                self._update_battle_text()
                Logger.warning("Player has no alive monsters!")
        
        self._update_hp_text()

    @override
    def enter(self, data: Any = None) -> None:
        """Called when entering the battle scene."""
        global last_battle_result
        
        sound_manager.play_bgm("RBY 107 Battle! (Trainer).ogg")
        
        last_battle_result["player_won"] = False
        last_battle_result["was_trainer_battle"] = False
        
        self.is_player_turn = True
        self.battle_over = False
        self.player_won = False
        self.show_moves = False
        self.show_victory_screen = False
        self.show_defeat_screen = False
        self.victory_screen_timer = 0
        self.battle_message = "What will you do?"
        self.enemy_attack_timer = 0
        self.run_away_timer = 0
        self.message_delay_timer = 0
        self.message_display_timer = 0
        self.message_queue.clear()
        self.evolution_pending = False
        self.evolution_timer = 0
        self.victory_timer = 0
        self.victory_text = None
        self.level_up_text = None
        self.xp_text = None
        self.no_alive_pokemon = False  # Flag for no alive Pokemon
        self.effectiveness_text = Text("", 18, "black")
        self._update_battle_text()
        
        if isinstance(data, EnemyTrainer):
            self.enemy_trainer = data
            self.game_manager = data.game_manager  # Store reference for coin rewards
            last_battle_result["was_trainer_battle"] = True
            Logger.info(f"Battle started!")
            self._load_monster_sprites()
            
            # Check if no alive Pokemon after loading
            if self.no_alive_pokemon:
                self.battle_over = True
                self.victory_timer = 0.5  # Quick exit
        else:
            Logger.warning("BattleScene entered without enemy trainer data!")
            self.enemy_trainer = None
            self.game_manager = None

    @override
    def exit(self) -> None:
        self.enemy_attack_timer = 0
        self.run_away_timer = 0
        self.message_delay_timer = 0
        self.message_display_timer = 0
        self.enemy_monster_sprite = None
        self.player_monster_sprite = None
        self.enemy_monster = None
        self.player_monster = None
        self.evolution_pending = False
        self.evolution_timer = 0
        self.victory_timer = 0
        self.show_moves = False
        self.show_victory_screen = False
        self.show_defeat_screen = False
        self.victory_text = None
        self.level_up_text = None
        self.xp_text = None
        self.message_queue.clear()

    @override
    def update(self, dt: float) -> None:
        self.battle_items_ui.update(dt)
        self.switch_pokemon_ui.update(dt)
        self.battle_ui.update(dt)
        
        if self.battle_items_ui.overlay_show or self.switch_pokemon_ui.overlay_show:
            return
        
        # Handle immediate exit when no alive Pokemon
        if self.no_alive_pokemon and self.battle_over:
            self.victory_timer -= dt
            if self.victory_timer <= 0:
                self._exit_battle()
            return
        
        if self.show_victory_screen or self.show_defeat_screen:
            self.victory_screen_timer -= dt
            
            if self.victory_screen_timer <= 0:
                self._exit_battle()
            return
        
        if self.message_display_timer > 0:
            self.message_display_timer -= dt
        
        if self.enemy_attack_timer > 0:
            self.enemy_attack_timer -= dt
            if self.enemy_attack_timer <= 0:
                self.enemy_attack_timer = 0
                self._enemy_attack()
        
        if self.message_delay_timer > 0:
            self.message_delay_timer -= dt
            if self.message_delay_timer <= 0:
                self.message_delay_timer = 0
                self.is_player_turn = True
                self.battle_message = "What will you do?"
                self._update_battle_text()
                self.effectiveness_text = Text("", 18, "black")
                self.effectiveness_message = ""
        
        if self.run_away_timer > 0:
            self.run_away_timer -= dt
            if self.run_away_timer <= 0:
                self.run_away_timer = 0
                self._exit_battle()
        
        # Handle clicks for the new UI
        if input_manager.mouse_pressed(1):
            mouse_pos = pg.mouse.get_pos()
            if not self.battle_over and self.is_player_turn:
                self.battle_ui.handle_click(mouse_pos)

    @override
    def draw(self, screen: pg.Surface) -> None:
        self.background.draw(screen)
        
        if self.enemy_monster_sprite:
            self.enemy_monster_sprite.draw(screen)
        
        if self.player_monster_sprite:
            self.player_monster_sprite.draw(screen)
        
        # Draw victory/defeat screens
        if self.show_victory_screen:
            self.battle_ui.draw_victory_screen(
                screen, 
                f"Defeated {self.enemy_monster.get('name', 'the enemy')}!",
                xp_gained=self.xp_gained,
                leveled_up=self.leveled_up
            )
            self.battle_items_ui.draw(screen)
            self.switch_pokemon_ui.draw(screen)
            return
        
        if self.show_defeat_screen:
            self.battle_ui.draw_defeat_screen(screen, "All your Pokemon have fainted!")
            self.battle_items_ui.draw(screen)
            self.switch_pokemon_ui.draw(screen)
            return
        
        # Draw the modern battle UI
        self.battle_ui.draw(screen)
        
        self.battle_items_ui.draw(screen)
        self.switch_pokemon_ui.draw(screen)