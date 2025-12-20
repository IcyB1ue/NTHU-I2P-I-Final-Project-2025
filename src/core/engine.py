import pygame as pg

from src.utils import GameSettings, Logger
from .services import scene_manager, input_manager

from src.scenes.menu_scene import MenuScene
from src.scenes.game_scene import GameScene
from src.scenes.setting_scene import SettingScene
from src.scenes.battle_scene import BattleScene
from src.scenes.wild_pokemon_scene import WildPokemonScene
from src.scenes.intro_scene import IntroScene


class Engine:

    screen: pg.Surface
    clock: pg.time.Clock
    running: bool

    def __init__(self):
        Logger.info("Initializing Engine")

        pg.init()

        self.screen = pg.display.set_mode((GameSettings.SCREEN_WIDTH, GameSettings.SCREEN_HEIGHT))
        self.clock = pg.time.Clock()
        self.running = True

        pg.display.set_caption(GameSettings.TITLE)

        scene_manager.register_scene("menu", MenuScene())
        scene_manager.register_scene("intro", IntroScene())
        scene_manager.register_scene("game", GameScene())
        scene_manager.register_scene("settings", SettingScene())
        scene_manager.register_scene("battle", BattleScene())
        scene_manager.register_scene("wild_pokemon", WildPokemonScene())
        
        scene_manager.change_scene("menu")

    def run(self):
        Logger.info("Running the Game Loop ...")

        while self.running:
            dt = self.clock.tick(GameSettings.FPS) / 1000.0
            self.handle_events()
            self.update(dt)
            self.render()

    def handle_events(self):
        input_manager.reset()
        for event in pg.event.get():
            if event.type == pg.QUIT:
                self.running = False
            input_manager.handle_events(event)
            
            # Pass events to current scene for text input handling
            current_scene = scene_manager.get_current_scene()
            if current_scene and hasattr(current_scene, 'handle_event'):
                current_scene.handle_event(event)

    def update(self, dt: float):
        scene_manager.update(dt)

    def render(self):
        self.screen.fill((0, 0, 0))
        scene_manager.draw(self.screen)
        pg.display.flip()