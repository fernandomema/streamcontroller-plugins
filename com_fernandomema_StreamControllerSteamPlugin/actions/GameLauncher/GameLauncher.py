from src.backend.PluginManager.ActionBase import ActionBase
import subprocess

class GameLauncher(ActionBase):
    """Simple action that launches a Steam game using the appid from settings."""

    def on_key_down(self, *_args, **_kwargs):
        """Launch the Steam game when the key is pressed."""
        appid = self.settings.get("appid") if hasattr(self, 'settings') else None
        if not appid:
            return
        try:
            subprocess.Popen(["steam", f"steam://rungameid/{appid}"])
        except Exception as e:
            print(f"[GameLauncher] Failed to launch {appid}: {e}")

    def on_tick(self):
        """Display the game name on the key label."""
        name = None
        if hasattr(self, 'settings'):
            name = self.settings.get("name")
        if name:
            self.set_label(text=name, position="center")
        else:
            self.set_label(text="Steam Game", position="center")
