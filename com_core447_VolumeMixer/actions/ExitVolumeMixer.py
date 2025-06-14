from src.backend.PluginManager.ActionBase import ActionBase
from src.backend.DeckManagement.DeckController import DeckController
from src.backend.PageManagement.Page import Page
from src.backend.PluginManager.PluginBase import PluginBase

import globals as gl
from loguru import logger as log

import os
from PIL import Image

class ExitVolumeMixer(ActionBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def on_ready(self):
        icon_path = os.path.join(self.plugin_base.PATH, "assets", "back.png")
        self.set_media(media_path=icon_path)

    def on_key_down(self):
        page_path = self.plugin_base.original_page_path
        if page_path is None:
            log.warning("No original page path to return to.")
            return
        if not os.path.exists(page_path):
            log.error("Could not find original page - cannot exit volume mixer.")
            return
        page = gl.page_manager.get_page(path=page_path, deck_controller=self.deck_controller)
        if page is None:
            log.error("Could not create original page - cannot exit volume mixer.")

        self.plugin_base.original_page_path = None
        self.deck_controller.load_page(page)