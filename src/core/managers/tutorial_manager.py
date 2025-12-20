from typing import Callable
from enum import Enum, auto

from src.utils import Logger


class TutorialQuest(Enum):
    NONE = auto()
    CATCH_FIRST_POKEMON = auto()
    FIGHT_FIRST_TRAINER = auto()
    SURVIVE_THE_NIGHT = auto()
    FIGHT_FIRE_GYM = auto()  # NEW QUEST
    CATCH_WATER_POKEMON = auto()  # NEW QUEST (split from WATER_WALKING)
    WATER_WALKING = auto()
    # Water World quests
    ENTER_WATER_WORLD = auto()  # Walk away from spawn, learn about gym master
    VISIT_WATER_GYM = auto()  # Go to gym, see corrupted leader
    WAIT_FOR_NIGHT = auto()  # Wait until night to investigate
    SNEAK_WATER_GYM = auto()  # Sneak past traps (math/coding)
    RESCUE_REAL_LEADER = auto()  # Find real gym leader in core
    GO_TO_HOSPITAL = auto()  # Escort real leader to hospital
    HOSPITAL_TRAINING = auto()  # Training/find secret item quest
    FIGHT_CORRUPTED = auto()  # Battle the corrupted trainer
    RECEIVE_WATER_BADGE = auto()  # Get badge
    TO_BE_CONTINUED = auto()  # Ending sequence
    COMPLETED = auto()


# Hospital coordinates for game_scene to use
# Set to None to indicate "use map center" - game_scene should calculate:
#   spawn_x = map_width_in_tiles // 2
#   spawn_y = map_height_in_tiles // 2
HOSPITAL_SPAWN_POSITION = None  # Will spawn at center of hospital map
HOSPITAL_EXIT_POSITION = (22, 18)  # Where player teleports after hospital (outside hospital entrance in water_map)


class TutorialManager:
    """Manages the tutorial quest progression."""
    
    def __init__(self):
        self.current_quest = TutorialQuest.NONE
        self.quest_started = False
        self.quest_step = 0
        self.night_survived = False
        self.gengar_repeller_obtained = False
        
        # Callbacks
        self.on_dialogue_request: Callable[[list[str]], None] | None = None
        self.on_quest_complete: Callable[[TutorialQuest], None] | None = None
        
        # Track progress
        self.has_left_house = False
        self.first_pokemon_caught = False
        self.first_trainer_defeated = False
        self.night_started = False
        self.night_time_remaining = 0.0
        self.fire_gym_attempted = False  # NEW
        self.fire_gym_won = False  # Track if actually won (for badge)
        self.trainer_battles_won = 0  # Track total trainer wins (for achievements)
        self.water_pokemon_caught = False
        self.entered_water_with_water_pokemon = False
        
        # Track when tutorial was completed (for fade out)
        self.tutorial_completed_time = 0.0
        self.tutorial_just_completed = False
        
        # Water World quest tracking
        self.entered_water_world = False
        self.visited_water_gym = False
        self.saw_corrupted_leader = False
        self.is_night_in_water_world = False
        self.sneak_puzzles_completed = 0
        self.sneak_puzzles_required = 1  # Single large puzzle
        self.real_leader_found = False
        self.reached_hospital = False
        self.hospital_quest_done = False
        self.hospital_locked = False  # Track if hospital has been locked
        self.corrupted_battles_won = 0
        self.water_badge_received = False
        self.ending_triggered = False
        
    def start_tutorial(self):
        """Start the tutorial from the beginning."""
        self.current_quest = TutorialQuest.CATCH_FIRST_POKEMON
        self.quest_started = False  # Not started until player leaves house
        self.quest_step = 0
        Logger.info("Tutorial initialized - waiting for player to leave house")
        
    def on_left_house(self):
        """Called when player leaves the house for the first time."""
        if self.has_left_house:
            return
            
        self.has_left_house = True
        self.quest_started = True
        
        if self.current_quest == TutorialQuest.CATCH_FIRST_POKEMON:
            self._show_catch_pokemon_dialogue()
    
    def _show_catch_pokemon_dialogue(self):
        """Show the first tutorial dialogue about catching Pokemon."""
        dialogues = [
            "Hey there! Welcome to the world of Pokemon!",
            "When you wander around in tall grass, you have a chance to encounter wild Pokemon!",
            "I've given you some Pokeballs and a starter Pokemon to begin with.",
            "Try to catch a Pokemon! But remember...",
            "Try to weaken it first before throwing a Pokeball for a better chance!",
            "Good luck out there, trainer!"
        ]
        if self.on_dialogue_request:
            self.on_dialogue_request(dialogues)
    
    def on_pokemon_caught(self, pokemon_name: str, pokemon_element: str):
        """Called when a Pokemon is caught."""
        Logger.info(f"Pokemon caught: {pokemon_name} ({pokemon_element})")
        
        if self.current_quest == TutorialQuest.CATCH_FIRST_POKEMON:
            self.first_pokemon_caught = True
            self._complete_quest(TutorialQuest.CATCH_FIRST_POKEMON)
            self._start_trainer_quest()
        
        # Check for water type for water quest
        if pokemon_element == "Water" and self.current_quest == TutorialQuest.CATCH_WATER_POKEMON:
            self.water_pokemon_caught = True
            self._complete_quest(TutorialQuest.CATCH_WATER_POKEMON)
            self._start_water_walking_quest()
    
    def _start_trainer_quest(self):
        """Start the fight trainer quest."""
        self.current_quest = TutorialQuest.FIGHT_FIRST_TRAINER
        
        dialogues = [
            "Congratulations on catching your first Pokemon!",
            "Now, let's test your battling skills!",
            "Find a trainer nearby and challenge them to a battle!",
            "Defeat them to prove your strength!"
        ]
        if self.on_dialogue_request:
            self.on_dialogue_request(dialogues)
    
    def on_trainer_defeated(self):
        """Called when a trainer is defeated."""
        Logger.info("Trainer defeated")
        
        # Always count trainer wins
        self.trainer_battles_won += 1
        
        if self.current_quest == TutorialQuest.FIGHT_FIRST_TRAINER:
            self.first_trainer_defeated = True
            self._complete_quest(TutorialQuest.FIGHT_FIRST_TRAINER)
            self._start_night_quest()
    
    def _start_night_quest(self):
        """Start the survive the night quest."""
        self.current_quest = TutorialQuest.SURVIVE_THE_NIGHT
        self.night_started = True
        self.night_time_remaining = 60.0  # 60 seconds of night
        
        dialogues = [
            "Great battle! But look... the sun is setting...",
            "Night is falling, and with it comes danger!",
            "Gengars roam the land at night, hunting for trainers!",
            "Your Pokemon aren't strong enough to fight them yet...",
            "You must survive until dawn! Avoid the Gengars!",
            "If they catch you, they'll steal items from your bag!",
            "Stay alert and keep moving!"
        ]
        if self.on_dialogue_request:
            self.on_dialogue_request(dialogues)
    
    def on_night_survived(self):
        """Called when the night is survived."""
        Logger.info("Night survived!")
        
        if self.current_quest == TutorialQuest.SURVIVE_THE_NIGHT:
            self.night_survived = True
            self.gengar_repeller_obtained = True
            self._complete_quest(TutorialQuest.SURVIVE_THE_NIGHT)
            self._start_fire_gym_quest()
    
    def _start_fire_gym_quest(self):
        """Start the fire gym challenge quest."""
        self.current_quest = TutorialQuest.FIGHT_FIRE_GYM
        
        dialogues = [
            "You survived the night! Impressive!",
            "Here, take these 5 Pokeballs as a reward!",
            "And this Gengar Repeller - it will keep Gengars away at night!",
            "Now, for your next challenge...",
            "Head to the Fire Gym to the east!",
            "The Gym Leader there is very powerful...",
            "But a true trainer never backs down from a challenge!",
            "Go and test your strength against the Fire Gym Leader!"
        ]
        if self.on_dialogue_request:
            self.on_dialogue_request(dialogues)
    
    def on_fire_gym_lost(self):
        """Called when player loses to the Fire Gym Leader."""
        Logger.info("Lost to Fire Gym Leader")
        
        if self.current_quest == TutorialQuest.FIGHT_FIRE_GYM:
            self.fire_gym_attempted = True
            # DON'T complete the quest - player needs to come back and win
            # Just start the catch water pokemon quest to get stronger
            self._start_catch_water_quest()
    
    def on_fire_gym_won(self):
        """Called when player wins against the Fire Gym Leader."""
        Logger.info("Won against Fire Gym Leader!")
        
        if self.current_quest == TutorialQuest.FIGHT_FIRE_GYM:
            self.fire_gym_attempted = True
            self.fire_gym_won = True  # Actually won - award badge
            self.trainer_battles_won += 1  # Count as trainer win
            self._complete_quest(TutorialQuest.FIGHT_FIRE_GYM)
            # Portal will open via _on_quest_complete in game_scene
            # Next quest will be set there
    
    def _start_catch_water_quest(self):
        """Start the catch water Pokemon quest."""
        self.current_quest = TutorialQuest.CATCH_WATER_POKEMON
        
        dialogues = [
            "Ouch! That Fire Gym Leader is tough!",
            "Fire-type Pokemon are weak to Water-type moves...",
            "If you want to beat them, you'll need a Water-type Pokemon!",
            "Go explore the tall grass and catch a Water-type Pokemon!",
            "Water types are usually found near bodies of water.",
            "Once you have one, you'll be much stronger against Fire types!",
            "Plus, Water Pokemon have a special ability...",
            "They can carry you across water! Very useful for exploration!"
        ]
        if self.on_dialogue_request:
            self.on_dialogue_request(dialogues)
    
    def _start_water_walking_quest(self):
        """Start the water walking quest after catching water Pokemon."""
        self.current_quest = TutorialQuest.WATER_WALKING
        
        dialogues = [
            "Excellent! You caught a Water-type Pokemon!",
            "Now, let me show you something cool...",
            "Head to the pond on the right side of the Fire Gym.",
            "With your Water Pokemon, you can walk right across it!",
            "Try it out - your Water Pokemon will carry you safely!"
        ]
        if self.on_dialogue_request:
            self.on_dialogue_request(dialogues)
    
    def on_water_crossed(self):
        """Called when player crosses water with a water Pokemon."""
        Logger.info("Water crossed with water Pokemon!")
        
        if self.current_quest == TutorialQuest.WATER_WALKING:
            self.entered_water_with_water_pokemon = True
            self._complete_quest(TutorialQuest.WATER_WALKING)
            self._post_water_walking_dialogue()
    
    def _post_water_walking_dialogue(self):
        """Show dialogue after water walking - directs to Fire Gym rematch."""
        dialogues = [
            "Amazing! You've mastered the basics of being a Pokemon Trainer!",
            "You can catch Pokemon, battle trainers, survive dangers...",
            "And even travel across water with your Pokemon partners!",
            "Now you are one step closer to beating the person at the Fire Gym!",
            "With your Water Pokemon, you'll have the advantage!",
            "Go defeat the Fire Gym Leader and claim your badge!"
        ]
        if self.on_dialogue_request:
            self.on_dialogue_request(dialogues)
        
        # Set quest back to FIGHT_FIRE_GYM for rematch (but don't show dialogue again)
        self.current_quest = TutorialQuest.FIGHT_FIRE_GYM
        Logger.info("Ready for Fire Gym rematch!")
    
    # ============== WATER WORLD QUEST METHODS ==============
    
    def on_entered_water_world(self):
        """Called when player teleports to Water World."""
        Logger.info("Entered Water World!")
        self.entered_water_world = True
        self.current_quest = TutorialQuest.ENTER_WATER_WORLD
    
    def on_water_world_walk(self):
        """Called when player walks away from spawn in Water World."""
        if self.current_quest == TutorialQuest.ENTER_WATER_WORLD:
            self._complete_quest(TutorialQuest.ENTER_WATER_WORLD)
            self._start_visit_water_gym_quest()
    
    def _start_visit_water_gym_quest(self):
        """Start the quest to visit the Water Gym."""
        self.current_quest = TutorialQuest.VISIT_WATER_GYM
        
        dialogues = [
            "If we want to find someone powerful enough to create a portal like this...",
            "It would have to be the Gym Master of this world!",
            "Let's head to the Water Gym and see if we can find any clues.",
            "The gym should be somewhere in this area..."
        ]
        if self.on_dialogue_request:
            self.on_dialogue_request(dialogues)
    
    def on_entered_water_gym(self):
        """Called when player enters the Water Gym."""
        Logger.info("Entered Water Gym!")
        
        if self.current_quest == TutorialQuest.VISIT_WATER_GYM:
            self.visited_water_gym = True
            self._complete_quest(TutorialQuest.VISIT_WATER_GYM)
            self._show_corrupted_leader_dialogue()
    
    def _show_corrupted_leader_dialogue(self):
        """Show dialogue when seeing the corrupted gym leader."""
        self.saw_corrupted_leader = True
        self.current_quest = TutorialQuest.WAIT_FOR_NIGHT
        
        dialogues = [
            "Wait... look at the Gym Leader!",
            "There's a strange, dark aura surrounding her...",
            "Something isn't right here. She looks... corrupted somehow.",
            "We shouldn't confront her directly like this.",
            "Let's wait until night to investigate what's going on.",
            "We can sneak around and find out what happened to her."
        ]
        if self.on_dialogue_request:
            self.on_dialogue_request(dialogues)
    
    def on_night_in_water_world(self):
        """Called when night falls in Water World after seeing corrupted leader."""
        if self.current_quest == TutorialQuest.WAIT_FOR_NIGHT:
            self.is_night_in_water_world = True
            self._complete_quest(TutorialQuest.WAIT_FOR_NIGHT)
            self._start_sneak_quest()
    
    def _start_sneak_quest(self):
        """Start the sneaking/puzzle quest."""
        self.current_quest = TutorialQuest.SNEAK_WATER_GYM
        
        dialogues = [
            "It's night now. The corrupted trainer is dormant!",
            "There's a magical floor puzzle blocking the way ahead.",
            "You'll need to solve it to reach the inner chamber!",
            "Step carefully - one wrong move and you'll have to start over!"
        ]
        if self.on_dialogue_request:
            self.on_dialogue_request(dialogues)
    
    def on_sneak_puzzle_completed(self):
        """Called when a sneak puzzle (math/coding) is completed."""
        self.sneak_puzzles_completed += 1
        Logger.info(f"Sneak puzzle completed: {self.sneak_puzzles_completed}/{self.sneak_puzzles_required}")
        
        if self.sneak_puzzles_completed >= self.sneak_puzzles_required:
            if self.current_quest == TutorialQuest.SNEAK_WATER_GYM:
                self._complete_quest(TutorialQuest.SNEAK_WATER_GYM)
                self._start_rescue_quest()
    
    def _start_rescue_quest(self):
        """Start the rescue real leader quest."""
        self.current_quest = TutorialQuest.RESCUE_REAL_LEADER
        # Dialogue handled by on_found_real_leader which is called immediately after
        Logger.info("Started rescue quest")
    
    def on_found_real_leader(self):
        """Called when player finds the real gym leader."""
        Logger.info("Found the real gym leader!")
        
        if self.current_quest == TutorialQuest.RESCUE_REAL_LEADER:
            self.real_leader_found = True
            self._complete_quest(TutorialQuest.RESCUE_REAL_LEADER)
            self._show_real_leader_lore()
    
    def _show_real_leader_lore(self):
        """Show the real gym leader's lore explanation."""
        self.current_quest = TutorialQuest.GO_TO_HOSPITAL
        
        # The lore dialogue - Misty explains what happened
        # Player will fight alone - Misty stays to rest
        dialogues = [
            "Misty: Thank goodness you found me! I'm Misty, the real Water Gym Leader.",
            "Misty: That thing out there... it's not me. It's a Shadow Clone.",
            "Misty: Long ago, an ancient evil was sealed beneath this gym.",
            "Misty: The Shadow Corruption - it feeds on the power of strong trainers.",
            "Misty: When I discovered its prison weakening, I tried to reseal it...",
            "Misty: But it was too powerful. It created a copy of me and trapped me here.",
            "Misty: It's been using my identity to lure in strong trainers to absorb their power.",
            "Misty: If it gathers enough energy, it will break free completely!",
            "Misty: My Wartortle... it was hurt badly protecting me.",
            "Misty: I'm too weak to fight right now. I need to rest and recover.",
            "Misty: But you... I can sense the strength in you!",
            "Misty: Let's head to the hospital so I can rest up."
        ]
        if self.on_dialogue_request:
            self.on_dialogue_request(dialogues)
    
    def on_reached_hospital(self):
        """Called when player reaches the hospital with the real leader."""
        Logger.info("Reached hospital!")
        
        if self.current_quest == TutorialQuest.GO_TO_HOSPITAL:
            self.reached_hospital = True
            self._complete_quest(TutorialQuest.GO_TO_HOSPITAL)
            self._start_hospital_training()
    
    def _start_hospital_training(self):
        """Start the hospital rest phase."""
        self.current_quest = TutorialQuest.HOSPITAL_TRAINING
        
        # Simple dialogue - the actual rest sequence is handled in game_scene
        Logger.info("Hospital training quest started - waiting for rest sequence")
    
    def on_hospital_quest_complete(self):
        """Called when hospital training/item quest is done."""
        Logger.info("Hospital quest complete!")
        
        if self.current_quest == TutorialQuest.HOSPITAL_TRAINING:
            self.hospital_quest_done = True
            self._complete_quest(TutorialQuest.HOSPITAL_TRAINING)
            self._show_hospital_exit_dialogue()
    
    def _show_hospital_exit_dialogue(self):
        """Show dialogue when leaving hospital - Misty stays, player goes alone."""
        self.hospital_locked = True
        
        dialogues = [
            "Misty: I found this Evolution Stone while resting! My Wartortle evolved into Blastoise!",
            "Misty: But I'm still not strong enough to fight the Shadow Clone...",
            "Misty: You'll have to face it alone. I believe in you!",
            "Misty: I'll lock up the hospital to make sure no more corruptors can vandalize it.",
            "Misty: Now go! Defeat the Shadow Clone and free this gym from corruption!",
            "Misty: I'll be cheering for you from here. Good luck!"
        ]
        if self.on_dialogue_request:
            self.on_dialogue_request(dialogues)
    
    def on_hospital_exit_dialogue_complete(self):
        """Called after hospital exit dialogue - start final battle quest."""
        self._start_final_battle_quest()
    
    def _start_final_battle_quest(self):
        """Start the final battle quest."""
        self.current_quest = TutorialQuest.FIGHT_CORRUPTED
        
        # Dialogue for going alone
        dialogues = [
            "Time to face the Shadow Clone alone...",
            "I can do this. Misty is counting on me!"
        ]
        if self.on_dialogue_request:
            self.on_dialogue_request(dialogues)
        
        Logger.info("Final battle quest started - player fighting alone")
    
    def on_corrupted_battle_won(self):
        """Called when a corrupted battle is won."""
        self.corrupted_battles_won += 1
        Logger.info(f"Corrupted battle won!")
        
        # Only need to win 1 battle against corrupted trainer
        if self.current_quest == TutorialQuest.FIGHT_CORRUPTED:
            self._complete_quest(TutorialQuest.FIGHT_CORRUPTED)
            # Badge and ending handled by game_scene
    
    def _show_victory_and_badge(self):
        """Show victory dialogue and give badge."""
        self.current_quest = TutorialQuest.RECEIVE_WATER_BADGE
        
        # Solo victory dialogue
        dialogues = [
            "The Shadow Corruption has been purified!",
            "I did it... I actually did it!",
            "Misty: You were incredible! I saw everything from the hospital!",
            "Misty: Thank you so much for saving me and this gym.",
            "Misty: I'm Misty, and you've proven yourself to be a truly remarkable trainer.",
            "Misty: Please, take this Water Badge as a token of my gratitude.",
            "Misty: You've more than earned it!"
        ]
        if self.on_dialogue_request:
            self.on_dialogue_request(dialogues)
    
    def on_badge_received(self):
        """Called when the badge is received."""
        Logger.info("Water badge received!")
        
        if self.current_quest == TutorialQuest.RECEIVE_WATER_BADGE:
            self.water_badge_received = True
            self._complete_quest(TutorialQuest.RECEIVE_WATER_BADGE)
            self._trigger_ending()
    
    def _trigger_ending(self):
        """Trigger the ending sequence."""
        self.current_quest = TutorialQuest.TO_BE_CONTINUED
        self.ending_triggered = True
        
        dialogues = [
            "Wait... what's happening?!",
            "My body... it's moving on its own!"
        ]
        if self.on_dialogue_request:
            self.on_dialogue_request(dialogues)
    
    def on_ending_complete(self):
        """Called when ending sequence completes."""
        Logger.info("Ending sequence complete!")
        self._complete_quest(TutorialQuest.TO_BE_CONTINUED)
        self._complete_game()
    
    def _complete_game(self):
        """Mark the game as completed."""
        self.current_quest = TutorialQuest.COMPLETED
        self.tutorial_just_completed = True
        self.tutorial_completed_time = 0.0
        Logger.info("Game completed - To Be Continued!")
    
    def _complete_quest(self, quest: TutorialQuest):
        """Mark a quest as complete."""
        Logger.info(f"Quest completed: {quest.name}")
        if self.on_quest_complete:
            self.on_quest_complete(quest)

    def get_current_quest(self) -> TutorialQuest | None:
        """Get the current active quest."""
        return self.current_quest

    def is_quest_active(self, quest: TutorialQuest) -> bool:
        """Check if a specific quest is currently active."""
        return self.current_quest == quest
    
    def update(self, dt: float) -> dict:
        """Update tutorial state. Returns events that occurred."""
        events = {}
        
        # Track time since tutorial completed for fade out
        if self.current_quest == TutorialQuest.COMPLETED:
            self.tutorial_completed_time += dt
        
        # Handle night time countdown
        if self.night_started and self.current_quest == TutorialQuest.SURVIVE_THE_NIGHT:
            self.night_time_remaining -= dt
            events["is_night"] = True
            events["night_progress"] = 1.0 - (self.night_time_remaining / 60.0)
            
            if self.night_time_remaining <= 0:
                self.night_started = False
                events["night_ended"] = True
                self.on_night_survived()
        elif self.current_quest.value > TutorialQuest.SURVIVE_THE_NIGHT.value:
            # After night quest, use day/night cycle
            events["use_day_night_cycle"] = True
        
        return events
    
    def is_night_active(self) -> bool:
        """Check if night time is currently active."""
        return self.night_started and self.current_quest == TutorialQuest.SURVIVE_THE_NIGHT
    
    def get_quest_description(self) -> str:
        """Get current quest description for UI."""
        # Don't show quest if tutorial hasn't really started yet
        if not self.quest_started:
            return ""
        
        if self.current_quest == TutorialQuest.CATCH_FIRST_POKEMON:
            return "Quest: Catch your first wild Pokemon!"
        elif self.current_quest == TutorialQuest.FIGHT_FIRST_TRAINER:
            return "Quest: Defeat a trainer in battle!"
        elif self.current_quest == TutorialQuest.SURVIVE_THE_NIGHT:
            remaining = int(self.night_time_remaining)
            return f"Quest: Survive the night! ({remaining}s remaining)"
        elif self.current_quest == TutorialQuest.FIGHT_FIRE_GYM:
            if self.fire_gym_won:
                return "Quest: Explore the mysterious portal!"
            return "Quest: Challenge the Fire Gym Leader!"
        elif self.current_quest == TutorialQuest.CATCH_WATER_POKEMON:
            return "Quest: Catch a Water-type Pokemon!"
        elif self.current_quest == TutorialQuest.WATER_WALKING:
            return "Quest: Cross the pond near the Fire Gym!"
        # Water World quests
        elif self.current_quest == TutorialQuest.ENTER_WATER_WORLD:
            return "Quest: Explore the Water World!"
        elif self.current_quest == TutorialQuest.VISIT_WATER_GYM:
            return "Quest: Find the Water Gym!"
        elif self.current_quest == TutorialQuest.WAIT_FOR_NIGHT:
            return "Quest: Wait until night to investigate..."
        elif self.current_quest == TutorialQuest.SNEAK_WATER_GYM:
            return "Quest: Solve the puzzle and sneak past!"
        elif self.current_quest == TutorialQuest.RESCUE_REAL_LEADER:
            return "Quest: Find the hidden chamber!"
        elif self.current_quest == TutorialQuest.GO_TO_HOSPITAL:
            return "Quest: Escort the Gym Leader to the hospital!"
        elif self.current_quest == TutorialQuest.HOSPITAL_TRAINING:
            return "Quest: Rest at the hospital..."
        elif self.current_quest == TutorialQuest.FIGHT_CORRUPTED:
            return "Quest: Defeat the Shadow Clone alone!"
        elif self.current_quest == TutorialQuest.RECEIVE_WATER_BADGE:
            return "Quest: Receive your reward!"
        elif self.current_quest == TutorialQuest.TO_BE_CONTINUED:
            return "???"
        elif self.current_quest == TutorialQuest.COMPLETED:
            return "To Be Continued..."
        return ""
    
    def should_hide_quest_ui(self) -> bool:
        """Check if quest UI should be hidden (after tutorial complete fade out)."""
        if self.current_quest == TutorialQuest.COMPLETED:
            return self.tutorial_completed_time > 5.0  # Hide after 5 seconds
        return False
    
    def get_quest_fade_alpha(self) -> int:
        """Get alpha value for quest UI (for fade out effect)."""
        if self.current_quest == TutorialQuest.COMPLETED:
            if self.tutorial_completed_time > 4.0:
                # Fade out over 1 second (from 4s to 5s)
                fade_progress = (self.tutorial_completed_time - 4.0) / 1.0
                return max(0, int(255 * (1.0 - fade_progress)))
        return 255
    
    def to_dict(self) -> dict:
        """Serialize tutorial state."""
        return {
            "current_quest": self.current_quest.name,
            "quest_started": self.quest_started,
            "has_left_house": self.has_left_house,
            "first_pokemon_caught": self.first_pokemon_caught,
            "first_trainer_defeated": self.first_trainer_defeated,
            "night_survived": self.night_survived,
            "gengar_repeller_obtained": self.gengar_repeller_obtained,
            "fire_gym_attempted": self.fire_gym_attempted,
            "fire_gym_won": self.fire_gym_won,
            "trainer_battles_won": self.trainer_battles_won,
            "water_pokemon_caught": self.water_pokemon_caught,
            "entered_water_with_water_pokemon": self.entered_water_with_water_pokemon,
            # Water World progress
            "entered_water_world": self.entered_water_world,
            "visited_water_gym": self.visited_water_gym,
            "saw_corrupted_leader": self.saw_corrupted_leader,
            "sneak_puzzles_completed": self.sneak_puzzles_completed,
            "real_leader_found": self.real_leader_found,
            "reached_hospital": self.reached_hospital,
            "hospital_quest_done": self.hospital_quest_done,
            "hospital_locked": self.hospital_locked,
            "corrupted_battles_won": self.corrupted_battles_won,
            "water_badge_received": self.water_badge_received,
            "ending_triggered": self.ending_triggered,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "TutorialManager":
        """Deserialize tutorial state."""
        manager = cls()
        manager.current_quest = TutorialQuest[data.get("current_quest", "NONE")]
        manager.quest_started = data.get("quest_started", False)
        manager.has_left_house = data.get("has_left_house", False)
        manager.first_pokemon_caught = data.get("first_pokemon_caught", False)
        manager.first_trainer_defeated = data.get("first_trainer_defeated", False)
        manager.night_survived = data.get("night_survived", False)
        manager.gengar_repeller_obtained = data.get("gengar_repeller_obtained", False)
        manager.fire_gym_attempted = data.get("fire_gym_attempted", False)
        manager.fire_gym_won = data.get("fire_gym_won", False)
        manager.trainer_battles_won = data.get("trainer_battles_won", 0)
        manager.water_pokemon_caught = data.get("water_pokemon_caught", False)
        manager.entered_water_with_water_pokemon = data.get("entered_water_with_water_pokemon", False)
        # Water World progress
        manager.entered_water_world = data.get("entered_water_world", False)
        manager.visited_water_gym = data.get("visited_water_gym", False)
        manager.saw_corrupted_leader = data.get("saw_corrupted_leader", False)
        manager.sneak_puzzles_completed = data.get("sneak_puzzles_completed", 0)
        manager.real_leader_found = data.get("real_leader_found", False)
        manager.reached_hospital = data.get("reached_hospital", False)
        manager.hospital_quest_done = data.get("hospital_quest_done", False)
        manager.hospital_locked = data.get("hospital_locked", False)
        manager.corrupted_battles_won = data.get("corrupted_battles_won", 0)
        manager.water_badge_received = data.get("water_badge_received", False)
        manager.ending_triggered = data.get("ending_triggered", False)
        
        # If tutorial was already completed, set the time high so it stays hidden
        if manager.current_quest == TutorialQuest.COMPLETED:
            manager.tutorial_completed_time = 10.0  # Already past fade out
        
        return manager