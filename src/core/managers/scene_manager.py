import pygame as pg
from typing import Any

from src.scenes.scene import Scene
from src.utils import Logger

class SceneManager:
    
    _scenes: dict[str, Scene]
    _current_scene: Scene | None = None
    _next_scene: str | None = None
    _scene_data: Any = None  # Store data to pass to the next scene
    
    def __init__(self):
        Logger.info("Initializing SceneManager")
        self._scenes = {}
        
    def register_scene(self, name: str, scene: Scene) -> None:
        self._scenes[name] = scene
        
    def change_scene(self, scene_name: str, data: Any = None) -> None:
        """
        Change to a different scene.
        
        Args:
            scene_name: The name of the scene to change to
            data: Optional data to pass to the scene's enter() method
        """
        if scene_name in self._scenes:
            Logger.info(f"Changing scene to '{scene_name}'")
            self._next_scene = scene_name
            self._scene_data = data  # Store the data
        else:
            raise ValueError(f"Scene '{scene_name}' not found")
            
    def update(self, dt: float) -> None:
        # Handle scene transition
        if self._next_scene is not None:
            self._perform_scene_switch()
            
        # Update current scene
        if self._current_scene:
            self._current_scene.update(dt)
            
    def draw(self, screen: pg.Surface) -> None:
        if self._current_scene:
            self._current_scene.draw(screen)
            
    def _perform_scene_switch(self) -> None:
        if self._next_scene is None:
            return
            
        # Exit current scene
        if self._current_scene:
            self._current_scene.exit()
        
        self._current_scene = self._scenes[self._next_scene]
        
        # Enter new scene with data
        if self._current_scene:
            Logger.info(f"Entering {self._next_scene} scene")
            self._current_scene.enter(self._scene_data)  # Pass the data
            
        # Clear the transition request and data
        self._next_scene = None
        self._scene_data = None  # Clear after passing

    # Add this method to your SceneManager class
    def get_current_scene(self):
        """Return the current active scene."""
        return self._current_scene  # or whatever your variable is called