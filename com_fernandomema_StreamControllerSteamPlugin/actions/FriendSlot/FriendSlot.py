from src.backend.PluginManager.ActionBase import ActionBase
import requests
from PIL import Image
from io import BytesIO

class FriendSlot(ActionBase):

    def _slot_coords(self):
        """Intentar obtener las coordenadas x, y y el indice de pagina."""
        x = getattr(self, "x", None)
        y = getattr(self, "y", None)
        page = getattr(self, "page", getattr(self, "page_index", 0))
        # Algunos entornos exponen el id de la tecla como "1x0"
        if (x is None or y is None) and hasattr(self, "key"):
            try:
                parts = str(getattr(self, "key")).split("x")
                if len(parts) == 2:
                    x = int(parts[0])
                    y = int(parts[1])
            except Exception:
                pass
        return x, y, page

    def _get_default_friend(self, friends):
        """Devuelve el amigo correspondiente a esta posicion si es posible."""
        x, y, page = self._slot_coords()
        if x is None or y is None:
            return None
        if x == 0:
            return None
        cols = 4
        index = (page * cols * 3) + ((y * cols) + (x - 1))
        if 0 <= index < len(friends):
            return friends[index]
        return None

    def on_changed(self, row, _param, steamid_list):
        """Maneja el cambio de selección en el ComboRow"""
        idx = row.get_selected()
        if 0 <= idx < len(steamid_list):
            steamid = steamid_list[idx][1]
            new_settings = dict(self.settings) if hasattr(self, 'settings') and self.settings else {}
            new_settings["steamid"] = steamid
            print("[FriendSlot] Cambiando steamid a:", steamid)
            # Guardar la configuración
            self.set_settings(new_settings)
            # Actualizar self.settings directamente para asegurarnos
            self.settings = new_settings
            # Forzar refresco inmediato
            self.on_tick()
            





    def get_config_rows(self):
        """Crea la UI de configuración para elegir el amigo por SteamID"""
        import gi
        gi.require_version("Gtk", "4.0")
        gi.require_version("Adw", "1")
        from gi.repository import Gtk, Adw

        # Cargar configuración predeterminada primero
        self.load_config_defaults()

        # Obtener lista de amigos (nuevo formato: [{'steamid', 'name', 'avatar', 'state'}])
        friends = getattr(self.plugin_base, 'friends_cache', None)
        if not friends or not isinstance(friends, list):
            friends = []

        # Añadir la opción "Ninguno"
        steamid_list = [("(Ninguno)", None)] + [(f.get('name', f.get('steamid', '')), f.get('steamid')) for f in friends]

        # Crear ComboRow
        combo_row = Adw.ComboRow(
            title="Amigo de Steam",
            subtitle="Selecciona el amigo a mostrar en este botón"
        )
        # Mostrar nombres, pero guardar steamid
        display_names = [name for name, _ in steamid_list] if steamid_list else ["(Sin amigos)"]
        combo_row.set_model(Gtk.StringList.new(display_names))

        # Seleccionar el actual
        current_steamid = self.settings.get("steamid")
        selected_idx = 0
        for idx, (_, sid) in enumerate(steamid_list):
            # Comparar None con None y strings con strings
            if sid == current_steamid or (sid is None and current_steamid in (None, "", "null")):
                selected_idx = idx
                break
        combo_row.set_selected(selected_idx)

        def on_changed(row, _param):
            idx = row.get_selected()
            if 0 <= idx < len(steamid_list):
                steamid = steamid_list[idx][1]
                new_settings = dict(self.settings) if hasattr(self, 'settings') and self.settings else {}
                # Guardar None explícitamente si se selecciona "Ninguno"
                new_settings["steamid"] = steamid if steamid is not None else None
                print("[FriendSlot] Cambiando steamid a:", steamid)
                self.set_settings(new_settings)
                self.settings = new_settings
                self.on_tick()

        combo_row.connect("notify::selected", on_changed)
        return [combo_row]
    def load_config_defaults(self):
        """Carga valores predeterminados para la configuración."""
        friends = getattr(self.plugin_base, 'friends_cache', None)
        if not friends or not isinstance(friends, list):
            friends = []
        steamid_list = [f.get('steamid') for f in friends if f.get('steamid')]
        # Solo rellenar si la clave no existe en settings
        """  if "steamid" not in self.settings and steamid_list:
            print("[FriendSlot] Configurando steamid predeterminado:", steamid_list[0])
            self.settings["steamid"] = steamid_list[0]
            self.set_settings(self.settings) """
            
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_avatar_url = None
        self.current_image = None
        # Asegura que self.settings siempre exista
        if not hasattr(self, 'settings') or self.settings is None:
            self.settings = {}



    def on_tick(self):
        # Cargar configuración predeterminada si es necesario
        self.load_config_defaults()
        
        # Permitir configurar el SteamID del amigo desde settings
        steamid = self.settings.get("steamid")
        friends = getattr(self.plugin_base, 'friends_cache', None)
        if not friends or not isinstance(friends, list):
            friends = []
        friend = None
        # Siempre usar el steamid de la configuración si está presente y válido
        if steamid:
            for f in friends:
                if str(f.get('steamid')) == str(steamid):
                    friend = f
                    break
        # Si no hay steamid o no se encuentra, no mostrar nada
        # Log detallado para depuración
        print("[FriendSlot] Contenido de la caché de amigos:", friends)
        print("[FriendSlot] steamid configurado:", steamid)

        if not friend:
            if steamid is None:
                # Calcular automáticamente qué amigo corresponde a esta posición
                friend = self._get_default_friend(friends)
                if friend:
                    steamid = friend.get("steamid")
                else:
                    self.set_media(image=None)
                    self.set_label(text="Selecciona un amigo", position="center")
                    print("[FriendSlot] steamid no asignado y sin amigo por defecto")
                    return
            else:
                self.set_media(image=None)
                self.set_label(text=f"(Sin amigo: {steamid})", position="center")
                print("[FriendSlot] steamid no encontrado:", steamid)
                print("[FriendSlot] steamids disponibles:", [f.get('steamid') for f in friends])
                return

        avatar_url = friend.get('avatar')
        if avatar_url:
            try:
                response = requests.get(avatar_url)
                image = Image.open(BytesIO(response.content)).convert('RGBA')
                self.set_media(image=image, size=1, valign=0)
            except Exception:
                self.set_media(image=None)
        else:
            self.set_media(image=None)
        # Mostrar el nombre y el estado si está disponible
        nombre = friend.get('name', '(Sin nombre)')
        estado = friend.get('state')
        estado_str = ''
        if estado is not None:
            estados = {
                0: 'Offline',
                1: 'Online',
                2: 'Busy',
                3: 'Away',
                4: 'Snooze',
                5: 'Looking to trade',
                6: 'Looking to play'
            }
            estado_str = f" [{estados.get(estado, estado)}]"
        self.set_label(text=f"{nombre}{estado_str}", position="bottom")

    def get_custom_config_area(self):
        """Crea una zona de configuración personalizada con un botón para refrescar la caché"""
        import gi
        gi.require_version("Gtk", "4.0")
        gi.require_version("Adw", "1")
        from gi.repository import Gtk, Adw

        # Crear box vertical
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        
        # Etiqueta informativa
        label = Gtk.Label()
        label.set_markup("<span size='small'>Selecciona un amigo de Steam para este botón. Si no ves todos tus amigos, refresca la caché.</span>")
        label.set_wrap(True)
        label.set_margin_top(8)
        label.set_margin_bottom(8)
        
        # Botón para refrescar
        refresh_button = Gtk.Button()
        refresh_button.set_label("Refrescar lista de amigos")
        refresh_button.set_margin_top(8)
        refresh_button.set_margin_bottom(8)
        
        def on_refresh_clicked(_button):
            if hasattr(self.plugin_base, 'refresh_friends_cache'):
                self.plugin_base.refresh_friends_cache()
                # Actualizar la UI después de refrescar
                self.rebuild_config_rows()
        
        refresh_button.connect("clicked", on_refresh_clicked)
        
        # Añadir componentes a la caja
        box.append(label)
        box.append(refresh_button)
        
        return box

    def rebuild_config_rows(self):
        """Reconstruye las filas de configuración después de refrescar la caché"""
        if hasattr(self, 'window') and self.window:
            try:
                # Obtener el contenedor padre de la UI
                parent = self.config_rows[0].get_parent()
                if parent:
                    # Eliminar filas antiguas
                    for row in self.config_rows:
                        parent.remove(row)
                    # Generar nuevas filas
                    self.config_rows = self.get_config_rows()
                    # Añadir nuevas filas
                    for row in self.config_rows:
                        parent.append(row)
                    print("[FriendSlot] UI de configuración reconstruida.")
            except Exception as e:
                print("[FriendSlot] Error al reconstruir UI:", e)
