from src.backend.PluginManager.ActionBase import ActionBase
import subprocess


class GameLauncher(ActionBase):
    """Action that launches a Steam game using the configured appid.

    If no game is configured it will try to automatically assign one based on
    the key position within the Steam games page."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not hasattr(self, "settings") or self.settings is None:
            self.settings = {}

    def _slot_coords(self):
        """Return x, y and page index when available."""
        x = getattr(self, "x", None)
        y = getattr(self, "y", None)
        page = getattr(self, "page", getattr(self, "page_index", None))

        # If a Page object is provided, try to extract its index
        if page is not None and not isinstance(page, int):
            page = getattr(page, "page_index", getattr(page, "index", 0))

        ident = getattr(self, "input_ident", None)
        if (x is None or y is None) and ident is not None:
            coords = getattr(ident, "coords", None)
            if coords:
                try:
                    x = int(coords[0])
                    y = int(coords[1])
                except Exception:
                    pass
            if page is None:
                page = getattr(ident, "page_index", page)

        if (x is None or y is None) and hasattr(self, "settings"):
            x = self.settings.get("_x", x)
            y = self.settings.get("_y", y)
            if page is None:
                page = self.settings.get("_page_index", page)

        if (x is None or y is None) and hasattr(self, "key"):
            try:
                parts = str(getattr(self, "key")).split("x")
                if len(parts) == 2:
                    x = int(parts[0])
                    y = int(parts[1])
            except Exception:
                pass

        if page is None:
            page = 0

        return x, y, page

    def _get_default_game(self, games):
        """Return the game assigned to this position if possible."""
        x, y, page = self._slot_coords()
        if x is None or y is None:
            return None
        if x == 0:
            return None
        cols = 4
        index = (page * cols * 3) + ((y * cols) + (x - 1))
        if 0 <= index < len(games):
            return games[index]
        return None

    def _ensure_settings(self):
        if not hasattr(self.plugin_base, "get_installed_games"):
            return
        if self.settings.get("appid"):
            return
        try:
            games = self.plugin_base.get_installed_games()
        except Exception:
            games = []
        game = self._get_default_game(games)
        if not game:
            return
        x, y, page = self._slot_coords()
        self.settings["appid"] = game.get("appid")
        self.settings["name"] = game.get("name")
        if x is not None:
            self.settings.setdefault("_x", x)
        if y is not None:
            self.settings.setdefault("_y", y)
        if page is not None:
            self.settings.setdefault("_page_index", page)
        self.set_settings(self.settings)

    def load_config_defaults(self):
        """Ensure settings have a valid appid/name when possible."""
        self._ensure_settings()

    def get_config_rows(self):
        """Create configuration rows to choose the game."""
        import gi
        gi.require_version("Gtk", "4.0")
        gi.require_version("Adw", "1")
        from gi.repository import Gtk, Adw

        self.load_config_defaults()

        games = []
        if hasattr(self.plugin_base, "get_installed_games"):
            try:
                games = self.plugin_base.get_installed_games()
            except Exception:
                games = []

        entries = [(g.get("name", g.get("appid")), g.get("appid")) for g in games]
        entries = [("(None)", None)] + entries if entries else [("(No games found)", None)]

        combo_row = Adw.ComboRow(
            title="Steam Game",
            subtitle="Select the game to launch",
        )
        combo_row.set_model(Gtk.StringList.new([n for n, _ in entries]))

        current_appid = self.settings.get("appid")
        selected_idx = 0
        for idx, (_, aid) in enumerate(entries):
            if aid == current_appid or (aid is None and current_appid in (None, "", "null")):
                selected_idx = idx
                break
        combo_row.set_selected(selected_idx)

        def on_changed(row, _param):
            idx = row.get_selected()
            if 0 <= idx < len(entries):
                appid = entries[idx][1]
                game_name = next((g.get("name") for g in games if g.get("appid") == appid), "") if appid else ""
                new_settings = dict(self.settings)
                new_settings["appid"] = appid if appid is not None else None
                new_settings["name"] = game_name
                self.set_settings(new_settings)
                self.settings = new_settings
                self.on_tick()

        combo_row.connect("notify::selected", on_changed)
        return [combo_row]

    def on_key_down(self, *_args, **_kwargs):
        """Launch the Steam game when the key is pressed."""
        self._ensure_settings()
        appid = self.settings.get("appid") if hasattr(self, "settings") else None
        if not appid:
            return
        try:
            subprocess.Popen(["steam", f"steam://rungameid/{appid}"])
        except Exception as e:
            print(f"[GameLauncher] Failed to launch {appid}: {e}")

    def on_tick(self):
        """Display the game name on the key label."""
        self._ensure_settings()
        name = self.settings.get("name") if hasattr(self, "settings") else None
        if name:
            self.set_label(text=name, position="center")
        else:
            self.set_label(text="Steam Game", position="center")
