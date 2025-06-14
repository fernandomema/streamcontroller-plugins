from src.backend.PluginManager.ActionBase import ActionBase
import subprocess
from PIL import Image
from gi.repository import Gtk, Gdk
import os

class AppLauncher(ActionBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not hasattr(self, "settings") or self.settings is None:
            self.settings = {}

    def on_short_press(self):
        settings = self.settings if hasattr(self, "settings") and self.settings else {}
        cmd = settings.get("exec")
        if cmd:
            subprocess.Popen(cmd, shell=True)

    def on_tick(self):
        settings = self.settings if hasattr(self, "settings") and self.settings else {}
        name = settings.get("name", "")
        icon_name = settings.get("icon")
        image = None
        if icon_name:
            path = self.resolve_icon(icon_name)
            if path and os.path.exists(path):
                try:
                    image = Image.open(path).convert('RGBA')
                except Exception:
                    image = None
        self.set_media(image=image, size=1, valign=0)
        self.set_label(text=name, position="bottom")

    def resolve_icon(self, icon_name):
        # Try absolute path first
        if os.path.isabs(icon_name) and os.path.exists(icon_name):
            return icon_name
        theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())
        info = theme.lookup_icon(icon_name, 64, 0)
        if info:
            return info.get_filename()
        # fallback to pixmaps
        pixmap_path = f"/usr/share/pixmaps/{icon_name}.png"
        if os.path.exists(pixmap_path):
            return pixmap_path
        return None
