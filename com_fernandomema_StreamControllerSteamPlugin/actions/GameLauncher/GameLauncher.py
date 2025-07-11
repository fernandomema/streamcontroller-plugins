from src.backend.PluginManager.ActionBase import ActionBase
import subprocess


class GameLauncher(ActionBase):
    """Action that launches a Steam game using the configured appid."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.has_configuration = True

    def on_ready(self):
        self.settings = self.get_settings()

    def load_config_defaults(self):
        """Ensure settings have a valid appid/name when possible."""
        games = []
        if hasattr(self.plugin_base, "get_installed_games"):
            try:
                games = self.plugin_base.get_installed_games()
            except Exception:
                games = []
        """     if "appid" not in self.settings and games:
            self.settings["appid"] = games[0].get("appid")
            self.settings["name"] = games[0].get("name")
            self.set_settings(self.settings) """

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
        appid = self.settings.get("appid") if hasattr(self, "settings") else None
        if not appid:
            return
        try:
            subprocess.Popen(["steam", f"steam://rungameid/{appid}"])
        except Exception as e:
            print(f"[GameLauncher] Failed to launch {appid}: {e}")

    def on_tick(self):
        """Display the game name on the key label."""
        name = self.settings.get("name") if hasattr(self, "settings") else None
        if name:
            self.set_label(text=name, position="bottom")
        else:
            self.set_label(text="Steam Game", position="bottom")
