"""
Coding Quiz UI - Minigame for earning coins.
"""
import pygame as pg
import random
from typing import Callable

from src.utils import GameSettings, Logger
from src.core.services import input_manager


# Coding questions database
CODING_QUESTIONS = [
    {
        "question": "What does 'print()' do in Python?",
        "options": ["Displays output", "Gets input", "Creates a loop", "Defines a function"],
        "correct": 0
    },
    {
        "question": "Which symbol is used for comments in Python?",
        "options": ["//", "/* */", "#", "<!-- -->"],
        "correct": 2
    },
    {
        "question": "What is the output of: print(2 + 3 * 4)?",
        "options": ["20", "14", "24", "Error"],
        "correct": 1
    },
    {
        "question": "Which data type is: 'Hello World'?",
        "options": ["int", "float", "str", "bool"],
        "correct": 2
    },
    {
        "question": "What does 'len()' return?",
        "options": ["Length/count", "Last element", "First element", "Sum"],
        "correct": 0
    },
    {
        "question": "How do you create a list in Python?",
        "options": ["{1, 2, 3}", "[1, 2, 3]", "(1, 2, 3)", "<1, 2, 3>"],
        "correct": 1
    },
    {
        "question": "What keyword starts a function definition?",
        "options": ["func", "function", "def", "define"],
        "correct": 2
    },
    {
        "question": "What is the output of: print(10 // 3)?",
        "options": ["3.33", "3", "4", "Error"],
        "correct": 1
    },
    {
        "question": "Which operator checks equality?",
        "options": ["=", "==", "===", "!="],
        "correct": 1
    },
    {
        "question": "What does 'range(5)' produce?",
        "options": ["1,2,3,4,5", "0,1,2,3,4", "0,1,2,3,4,5", "5,4,3,2,1"],
        "correct": 1
    },
    {
        "question": "How do you start an if statement?",
        "options": ["if condition then", "if (condition):", "if condition:", "if: condition"],
        "correct": 2
    },
    {
        "question": "What does 'append()' do to a list?",
        "options": ["Removes item", "Adds to end", "Adds to start", "Sorts list"],
        "correct": 1
    },
    {
        "question": "What is True and False in Python?",
        "options": ["Strings", "Integers", "Booleans", "Keywords only"],
        "correct": 2
    },
    {
        "question": "What does 'import' do?",
        "options": ["Exports code", "Loads a module", "Deletes file", "Creates class"],
        "correct": 1
    },
    {
        "question": "What is the index of first element in a list?",
        "options": ["1", "0", "-1", "First"],
        "correct": 1
    },
    {
        "question": "Which loop iterates over a sequence?",
        "options": ["while", "do-while", "for", "repeat"],
        "correct": 2
    },
    {
        "question": "What does 'break' do in a loop?",
        "options": ["Pauses loop", "Exits loop", "Skips iteration", "Restarts loop"],
        "correct": 1
    },
    {
        "question": "What is 'None' in Python?",
        "options": ["Zero", "Empty string", "Null value", "False"],
        "correct": 2
    },
    {
        "question": "How do you get user input?",
        "options": ["get()", "input()", "read()", "scan()"],
        "correct": 1
    },
    {
        "question": "What does '+' do with strings?",
        "options": ["Adds them mathematically", "Concatenates them", "Compares them", "Error"],
        "correct": 1
    },
]

COIN_REWARD = 15  # Coins per correct answer


class CodingQuizUI:
    """UI for the coding quiz minigame."""
    
    def __init__(self, on_complete: Callable[[int], None] | None = None):
        """
        Initialize quiz UI.
        on_complete: Callback with coins earned when quiz ends.
        """
        self.overlay_show = False
        self.on_complete = on_complete
        
        # Quiz state
        self.current_question = None
        self.question_index = 0
        self.questions_answered = 0
        self.coins_earned = 0
        self.selected_answer = -1
        self.answer_revealed = False
        self.reveal_timer = 0.0
        
        # Track total correct answers (persists across sessions)
        self.total_correct = 0
        
        # Load font
        try:
            self.font_path = "assets/fonts/Minecraft.ttf"
            self.title_font = pg.font.Font(self.font_path, 28)
            self.question_font = pg.font.Font(self.font_path, 18)
            self.option_font = pg.font.Font(self.font_path, 16)
            self.result_font = pg.font.Font(self.font_path, 20)
            self.small_font = pg.font.Font(self.font_path, 14)
        except:
            self.font_path = None
            self.title_font = pg.font.Font(None, 36)
            self.question_font = pg.font.Font(None, 28)
            self.option_font = pg.font.Font(None, 24)
            self.result_font = pg.font.Font(None, 32)
            self.small_font = pg.font.Font(None, 18)
        
        # UI dimensions
        self.panel_width = 700
        self.panel_height = 450
        self.panel_x = (GameSettings.SCREEN_WIDTH - self.panel_width) // 2
        self.panel_y = (GameSettings.SCREEN_HEIGHT - self.panel_height) // 2
        
        # Option button rects
        self.option_rects: list[pg.Rect] = []
        self.option_hovered = -1
        
        # Continue/exit buttons
        self.continue_rect = pg.Rect(
            self.panel_x + self.panel_width // 2 - 80,
            self.panel_y + self.panel_height - 60,
            160, 40
        )
        self.exit_rect = pg.Rect(
            self.panel_x + self.panel_width - 100,
            self.panel_y + 15,
            80, 30
        )
        
        # Darken background
        self.darken = pg.Surface((GameSettings.SCREEN_WIDTH, GameSettings.SCREEN_HEIGHT))
        self.darken.fill("Black")
        self.darken.set_alpha(180)
        
        # Used questions to avoid repeats
        self.used_questions: set[int] = set()
    
    def open(self):
        """Open the quiz UI with a new question."""
        self.overlay_show = True
        self.questions_answered = 0
        self.coins_earned = 0
        self.answer_revealed = False
        self.reveal_timer = 0.0
        self.selected_answer = -1
        self._load_new_question()
        input_manager.reset()
        Logger.info("Coding quiz opened")
    
    def close(self):
        """Close the quiz UI."""
        self.overlay_show = False
        if self.on_complete:
            self.on_complete(self.coins_earned)
        Logger.info(f"Coding quiz closed. Earned {self.coins_earned} coins")
    
    def _load_new_question(self):
        """Load a new random question."""
        # Get available questions (not used yet)
        available = [i for i in range(len(CODING_QUESTIONS)) if i not in self.used_questions]
        
        # Reset if all used
        if not available:
            self.used_questions.clear()
            available = list(range(len(CODING_QUESTIONS)))
        
        # Pick random question
        self.question_index = random.choice(available)
        self.used_questions.add(self.question_index)
        self.current_question = CODING_QUESTIONS[self.question_index]
        self.selected_answer = -1
        self.answer_revealed = False
        self.reveal_timer = 0.0
        
        # Create option rects
        self._create_option_rects()
    
    def _create_option_rects(self):
        """Create clickable rects for answer options."""
        self.option_rects.clear()
        
        if not self.current_question:
            return
        
        options = self.current_question["options"]
        option_width = self.panel_width - 80
        option_height = 45
        start_y = self.panel_y + 160  # Moved down to make room for result text
        spacing = 55
        
        for i in range(len(options)):
            rect = pg.Rect(
                self.panel_x + 40,
                start_y + i * spacing,
                option_width,
                option_height
            )
            self.option_rects.append(rect)
    
    def _check_answer(self, answer_index: int):
        """Check if selected answer is correct."""
        if not self.current_question or self.answer_revealed:
            return
        
        self.selected_answer = answer_index
        self.answer_revealed = True
        
        correct = self.current_question["correct"]
        if answer_index == correct:
            self.coins_earned += COIN_REWARD
            self.total_correct += 1  # Track total correct for achievements
            Logger.info(f"Correct! +{COIN_REWARD} coins (Total correct: {self.total_correct})")
        else:
            Logger.info(f"Wrong! Correct answer was: {self.current_question['options'][correct]}")
        
        self.questions_answered += 1
        self.reveal_timer = 2.0  # Show result for 2 seconds
    
    def update(self, dt: float):
        """Update the quiz UI."""
        if not self.overlay_show:
            return
        
        # Handle reveal timer
        if self.answer_revealed and self.reveal_timer > 0:
            self.reveal_timer -= dt
            if self.reveal_timer <= 0:
                # Auto continue to next question or show result
                pass  # Wait for click
        
        mouse_pos = input_manager.mouse_pos
        
        # Check exit button
        if self.exit_rect.collidepoint(mouse_pos) and input_manager.mouse_pressed(1):
            self.close()
            return
        
        # After answer revealed, check continue button
        if self.answer_revealed and self.reveal_timer <= 0:
            if self.continue_rect.collidepoint(mouse_pos) and input_manager.mouse_pressed(1):
                self._load_new_question()
                return
        
        # Check option hover and clicks
        self.option_hovered = -1
        if not self.answer_revealed:
            for i, rect in enumerate(self.option_rects):
                if rect.collidepoint(mouse_pos):
                    self.option_hovered = i
                    if input_manager.mouse_pressed(1):
                        self._check_answer(i)
                        break
    
    def draw(self, screen: pg.Surface):
        """Draw the quiz UI."""
        if not self.overlay_show:
            return
        
        # Darken background
        screen.blit(self.darken, (0, 0))
        
        # Main panel
        panel_rect = pg.Rect(self.panel_x, self.panel_y, self.panel_width, self.panel_height)
        pg.draw.rect(screen, (40, 50, 70), panel_rect, border_radius=15)
        pg.draw.rect(screen, (80, 100, 140), panel_rect, 3, border_radius=15)
        
        # Title
        title_text = self.title_font.render("Professor's Coding Quiz!", True, (255, 220, 100))
        title_rect = title_text.get_rect(centerx=self.panel_x + self.panel_width // 2, y=self.panel_y + 20)
        screen.blit(title_text, title_rect)
        
        # Coins earned display
        coins_text = self.small_font.render(f"Coins earned: {self.coins_earned}", True, (255, 215, 0))
        coins_rect = coins_text.get_rect(x=self.panel_x + 20, y=self.panel_y + 25)
        screen.blit(coins_text, coins_rect)
        
        # Exit button
        mouse_pos = input_manager.mouse_pos
        exit_color = (150, 80, 80) if self.exit_rect.collidepoint(mouse_pos) else (100, 60, 60)
        pg.draw.rect(screen, exit_color, self.exit_rect, border_radius=5)
        exit_text = self.small_font.render("Exit", True, (255, 255, 255))
        exit_text_rect = exit_text.get_rect(center=self.exit_rect.center)
        screen.blit(exit_text, exit_text_rect)
        
        if not self.current_question:
            return
        
        # Question text (with word wrap)
        question = self.current_question["question"]
        self._draw_wrapped_text(screen, question, self.question_font, 
                                self.panel_x + 40, self.panel_y + 70, 
                                self.panel_width - 80, (255, 255, 255))
        
        # Result message (shown ABOVE the options when answer is revealed)
        if self.answer_revealed:
            correct = self.current_question["correct"]
            if self.selected_answer == correct:
                result_text = self.result_font.render(f"Correct! +{COIN_REWARD} coins!", True, (100, 255, 100))
            else:
                result_text = self.result_font.render("Wrong! Try another question.", True, (255, 100, 100))
            result_rect = result_text.get_rect(centerx=self.panel_x + self.panel_width // 2,
                                                y=self.panel_y + 120)
            # Draw background for result
            result_bg = result_rect.inflate(20, 10)
            pg.draw.rect(screen, (0, 0, 0, 180), result_bg, border_radius=8)
            screen.blit(result_text, result_rect)
        
        # Answer options
        correct = self.current_question["correct"]
        
        for i, (option, rect) in enumerate(zip(self.current_question["options"], self.option_rects)):
            # Determine color
            if self.answer_revealed:
                if i == correct:
                    color = (60, 150, 60)  # Green for correct
                elif i == self.selected_answer:
                    color = (150, 60, 60)  # Red for wrong selection
                else:
                    color = (60, 60, 80)  # Dim for others
            else:
                if self.option_hovered == i:
                    color = (80, 80, 120)  # Hover
                else:
                    color = (60, 60, 80)  # Normal
            
            pg.draw.rect(screen, color, rect, border_radius=8)
            pg.draw.rect(screen, (100, 100, 130), rect, 2, border_radius=8)
            
            # Option text
            letter = chr(65 + i)  # A, B, C, D
            option_text = self.option_font.render(f"{letter}. {option}", True, (255, 255, 255))
            option_text_rect = option_text.get_rect(midleft=(rect.x + 15, rect.centery))
            screen.blit(option_text, option_text_rect)
        
        # Continue button (after reveal timer, at bottom)
        if self.answer_revealed and self.reveal_timer <= 0:
            cont_color = (80, 120, 80) if self.continue_rect.collidepoint(mouse_pos) else (60, 100, 60)
            pg.draw.rect(screen, cont_color, self.continue_rect, border_radius=8)
            pg.draw.rect(screen, (40, 80, 40), self.continue_rect, 2, border_radius=8)
            
            cont_text = self.option_font.render("Next Question", True, (255, 255, 255))
            cont_text_rect = cont_text.get_rect(center=self.continue_rect.center)
            screen.blit(cont_text, cont_text_rect)
    
    def _draw_wrapped_text(self, screen: pg.Surface, text: str, font: pg.font.Font,
                           x: int, y: int, max_width: int, color: tuple):
        """Draw text with word wrapping."""
        words = text.split(" ")
        lines = []
        current_line = ""
        
        for word in words:
            test_line = current_line + word + " "
            if font.size(test_line)[0] <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line.strip())
                current_line = word + " "
        if current_line:
            lines.append(current_line.strip())
        
        for i, line in enumerate(lines):
            text_surface = font.render(line, True, color)
            screen.blit(text_surface, (x, y + i * (font.get_height() + 5)))