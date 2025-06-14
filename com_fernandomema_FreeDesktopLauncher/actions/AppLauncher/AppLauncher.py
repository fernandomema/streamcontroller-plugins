from src.backend.PluginManager.ActionBase import ActionBase
import subprocess
import shlex
from PIL import Image
from gi.repository import Gtk, Gdk
import os

class AppLauncher(ActionBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not hasattr(self, "settings") or self.settings is None:
            self.settings = {}

    def on_short_press(self):
        # Call on_key_down for backward compatibility with older app versions
        self.on_key_down()

    def on_key_down(self, *_args, **_kwargs):
        settings = self.settings if hasattr(self, "settings") and self.settings else {}
        cmd = settings.get("exec")
        if cmd:
            self.launch_command(cmd)

    def launch_command(self, cmd):
        cmd = self.sanitize_exec(cmd)
        try:
            subprocess.Popen(cmd, shell=True)
        except Exception as e:
            print(f"[AppLauncher] Failed to launch '{cmd}': {e}")

    def sanitize_exec(self, cmd):
        # Remove desktop entry field codes like %f, %F, %u, etc.
        tokens = ["%f", "%F", "%u", "%U", "%i", "%c", "%k"]
        for token in tokens:
            cmd = cmd.replace(token, "")
        return cmd.strip()

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
        if os.path.exists(icon_name):
            return icon_name
        try:
            theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())
            info = theme.lookup_icon(icon_name, 64, 0)
            if info:
                return info.get_filename()
        except Exception:
            pass
        # fallback paths
        search_paths = [
            f"/usr/share/pixmaps/{icon_name}.png",
            f"/usr/share/icons/hicolor/64x64/apps/{icon_name}.png",
            f"/usr/share/icons/hicolor/48x48/apps/{icon_name}.png",
            f"/usr/share/icons/hicolor/256x256/apps/{icon_name}.png",
        ]
        for p in search_paths:
            if os.path.exists(p):
                return p
        return None
