import os
import json
import math
import configparser
from pathlib import Path

from src.backend.PluginManager.PluginBase import PluginBase
from src.backend.PluginManager.ActionHolder import ActionHolder
from src.backend.PluginManager.ActionInputSupport import ActionInputSupport
from src.backend.DeckManagement.InputIdentifier import Input

from .actions.AppLauncher.AppLauncher import AppLauncher


class FreeDesktopLauncherPlugin(PluginBase):
    ITEMS_PER_PAGE = 15

    def __init__(self):
        super().__init__()
        self.lm = self.locale_manager

        self.launcher_holder = ActionHolder(
            plugin_base=self,
            action_base=AppLauncher,
            action_id_suffix="AppLauncher",
            action_name="Application Launcher",
            action_support={
                Input.Key: ActionInputSupport.SUPPORTED,
                Input.Dial: ActionInputSupport.UNSUPPORTED,
                Input.Touchscreen: ActionInputSupport.SUPPORTED,
            },
        )
        self.add_action_holder(self.launcher_holder)

        self.register(
            plugin_name="FreeDesktop Launcher",
            github_repo="https://github.com/example/FreeDesktopLauncher",
            plugin_version="1.0.0",
            app_version="1.2.0-alpha",
        )

        self.generate_pages()

    def load_desktop_entries(self):
        paths = [
            Path("/usr/share/applications"),
            Path("/usr/local/share/applications"),
            Path.home() / ".local/share/applications",
        ]
        entries = []
        for base in paths:
            if not base.exists():
                continue
            for f in base.glob("*.desktop"):
                parser = configparser.ConfigParser(interpolation=None)
                try:
                    parser.read(f)
                except Exception:
                    continue
                if not parser.has_section("Desktop Entry"):
                    continue
                sect = parser["Desktop Entry"]
                name = sect.get("Name")
                exec_cmd = sect.get("Exec")
                icon = sect.get("Icon")
                if not name or not exec_cmd:
                    continue
                entries.append({"name": name, "exec": exec_cmd, "icon": icon})
        # sort by name
        entries.sort(key=lambda e: e["name"].lower())
        return entries

    def generate_pages(self):
        entries = self.load_desktop_entries()
        pages_dir = os.path.join(self.PATH, "pages")
        os.makedirs(pages_dir, exist_ok=True)
        per_page = self.ITEMS_PER_PAGE
        total_pages = math.ceil(len(entries) / per_page) or 1
        for idx in range(total_pages):
            chunk = entries[idx * per_page:(idx + 1) * per_page]
            page = self.create_page(chunk)
            page_path = os.path.join(pages_dir, f"MenuPage{idx+1}.json")
            with open(page_path, "w") as fh:
                json.dump(page, fh, indent=4)
            self.register_page(page_path)

    def create_page(self, entries):
        page = {"keys": {"0x0": {}}}
        positions = [(x, y) for x in range(5) for y in range(3)][1:]
        for entry, pos in zip(entries, positions):
            key = f"{pos[0]}x{pos[1]}"
            page["keys"][key] = {
                "states": {
                    "0": {
                        "actions": [
                            {
                                "id": f"{self.plugin_id}::AppLauncher",
                                "settings": entry,
                            }
                        ],
                        "image-control-action": 0,
                        "label-control-actions": [0, 0, 0],
                        "background-control-action": 0,
                    }
                }
            }
        # Fill remaining positions
        for pos in positions[len(entries):]:
            key = f"{pos[0]}x{pos[1]}"
            page["keys"].setdefault(key, {})
        return page
