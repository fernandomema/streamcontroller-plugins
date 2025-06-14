from src.backend.PluginManager.ActionBase import ActionBase
from src.backend.PluginManager.ActionBase import ActionBase
from src.backend.DeckManagement.DeckController import DeckController
from src.backend.PageManagement.Page import Page
from src.backend.PluginManager.PluginBase import PluginBase

import globals as gl
from loguru import logger as log

import os
from PIL import Image

# Import gtk modules
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

class OpenVolumeMixer(ActionBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def on_ready(self):
        icon_path = os.path.join(self.plugin_base.PATH, "assets", "equalizer.png")
        self.set_media(media_path=icon_path)

    def on_key_down(self):
        # Reset position
        self.plugin_base.start_index = 0

        page_name = "VolumeMixer"
        if self.deck_controller.deck.dial_count() > 0:
            page_name = "VolumeMixerSDPlus"

        page_path = os.path.join(self.plugin_base.PATH, "pages", f"{page_name}.json")
        if not os.path.exists(page_path):
            log.error("Could not find volume mixer page. Consider reinstalling the plugin.")
            return
        page = gl.page_manager.get_page(path=page_path, deck_controller=self.deck_controller)
        if page is None:
            log.error("Could not create volume mixer page object. Consider reinstalling the plugin.")

        self.plugin_base.original_page_path = self.deck_controller.active_page.json_path
        self.deck_controller.load_page(page)

    def get_config_rows(self) -> list:
        self.increments_row = Adw.SpinRow.new_with_range(min=0, max=100, step=5)
        self.increments_row.set_title("Increments (%):")

        # Load default
        settings = self.get_settings()
        self.increments_row.set_value(settings.get("increments", 10))
        self.plugin_base.volume_increment = self.increments_row.get_value() / 100

        # Connect signal
        self.increments_row.connect("changed", self.on_increments_change)

        return [self.increments_row]
    
    def on_increments_change(self, row):
        settings = self.get_settings()
        settings["increments"] = row.get_value()
        self.plugin_base.volume_increment = row.get_value() / 100
        self.set_settings(settings)