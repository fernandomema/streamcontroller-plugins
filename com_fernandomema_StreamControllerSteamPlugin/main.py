from .actions.FriendSlot.FriendSlot import FriendSlot
from .actions.GameLauncher.GameLauncher import GameLauncher

# StreamController Steam Friends Plugin

from src.backend.PluginManager.PluginBase import PluginBase
from src.backend.PluginManager.ActionHolder import ActionHolder
from src.backend.PluginManager.ActionInputSupport import ActionInputSupport
from src.backend.DeckManagement.InputIdentifier import Input
import requests
import logging
import math
import os
import json
import re


class SteamFriendsPlugin(PluginBase):
    ITEMS_PER_PAGE = 15
    def __init__(self):
        import time
        super().__init__()
        self.init_vars()
        self.lm = self.locale_manager
        self.logger = logging.getLogger(__name__)

        # Cargar settings del plugin (persistentes)
        self.settings = self.get_settings() if hasattr(self, 'get_settings') else {}
        # Valores por defecto
        self.settings.setdefault('api_key', "")
        self.settings.setdefault('steam_id', "")
        self.api_key = self.settings['api_key']
        self.steam_id = self.settings['steam_id']

        # Caches
        self._avatar_url = None
        self._avatar_url_last_update = 0
        self._friends_cache = None
        self._friends_cache_last_update = 0
        self._cache_ttl = 60  # segundos

        # Obtener avatar del usuario principal (cacheado)
        self.avatar_url = self.get_main_avatar_url()

        # Lista cacheada de amigos para los slots
        self.friends_cache = self.get_steam_friends()

        # ActionHolder para los slots de amigos
        self.friend_slot_holder = ActionHolder(
            plugin_base=self,
            action_base=FriendSlot,
            action_id_suffix="FriendSlot",
            action_name="Friend Slot",
            action_support={
                Input.Key: ActionInputSupport.SUPPORTED,
                Input.Dial: ActionInputSupport.UNSUPPORTED,
                Input.Touchscreen: ActionInputSupport.SUPPORTED
            }
        )
        self.friend_slot_holder.has_configuration = True  # Permite configurar steamid
        self.add_action_holder(self.friend_slot_holder)

        # ActionHolder para lanzar juegos de Steam
        self.game_launcher_holder = ActionHolder(
            plugin_base=self,
            action_base=GameLauncher,
            action_id_suffix="GameLauncher",
            action_name="Steam Game Launcher",
            action_support={
                Input.Key: ActionInputSupport.SUPPORTED,
                Input.Dial: ActionInputSupport.UNSUPPORTED,
                Input.Touchscreen: ActionInputSupport.SUPPORTED
            }
        )
        self.add_action_holder(self.game_launcher_holder)

        # Register plugin
        self.register(
            plugin_name = self.lm.get("plugin.name"),
            github_repo = "https://github.com/fernandomema/StreamControllerSteamPlugin",
            plugin_version = "1.0.0",
            app_version = "1.2.0-alpha"
        )
        # Registrar la página dinámica de amigos si existe
        self.register_friends_page()
        # Registrar la página de juegos instalados
        self.register_games_page()        

    def _safe_get_json(self, url):
        """Helper to GET and parse JSON without raising exceptions."""
        try:
            resp = requests.get(url, timeout=5)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            self.logger.warning(f"Failed to fetch {url}: {exc}")
            return {}

    def set_settings(self, settings):
        """Guarda los settings y actualiza api_key y steam_id en memoria"""
        super().set_settings(settings)
        self.settings = settings
        self.api_key = self.settings.get('api_key', "E91DBC4C9CA96527F844933EEEB03EF1")
        self.steam_id = self.settings.get('steam_id', "76561198074254458")

    def get_settings_area(self):
        """Devuelve la UI de configuración del plugin (API Key y SteamID)"""
        from gi.repository import Adw
        group = Adw.PreferencesGroup(title="Steam API")

        from gi.repository.Adw import EntryRow
        api_key_row = EntryRow(title="Steam API Key")
        api_key_row.set_text(self.settings.get('api_key', ""))
        steam_id_row = EntryRow(title="SteamID64 principal")
        steam_id_row.set_text(self.settings.get('steam_id', ""))

        def on_api_key_changed(row, _param):
            self.set_setting('api_key', row.get_text())

        def on_steam_id_changed(row, _param):
            self.set_setting('steam_id', row.get_text())

        api_key_row.connect("notify::text", on_api_key_changed)
        steam_id_row.connect("notify::text", on_steam_id_changed)

        group.add(api_key_row)
        group.add(steam_id_row)
        return group

    def set_setting(self, key, value):
        self.settings[key] = value
        self.set_settings(self.settings)

    def register_friends_page(self):
        """Registra la página dinámica de amigos de Steam"""
        import os
        import json
        
        # Verificar si ya existe la página estática
        page_path = os.path.join(self.PATH, "pages", "SteamFriends.json")
        
        self.register_page(page_path)

    def init_vars(self):
        """Inicializa variables y registra íconos para los botones Next y Previous."""
        size = 0.7

        # Registrar íconos predeterminados para los botones con registro adicional
        next_icon_path = self.get_asset_path("next.png")
        previous_icon_path = self.get_asset_path("previous.png")

        self.add_icon("NEXT_BUTTON", next_icon_path, size)
        self.add_icon("PREVIOUS_BUTTON", previous_icon_path, size)

    def register_games_page(self):
        """Genera y registra páginas con los juegos instalados de Steam."""
        import os
        import json

        games = self.get_installed_games()
        if not games:
            return

        per_page = self.ITEMS_PER_PAGE
        max_cols, max_rows = 5, 3
        total_pages = math.ceil(len(games) / per_page) or 1

        pages_dir = os.path.join(self.PATH, "pages")
        os.makedirs(pages_dir, exist_ok=True)

        # Usar directamente las rutas generadas por get_asset_path
        next_icon = self.get_asset_path("next.png")
        previous_icon = self.get_asset_path("previous.png")


        # clone games to avoid modifying the original list
        games_to_append = games.copy()
        for page_idx in range(total_pages):
            keys = {}

            # Botón de página anterior
            if page_idx > 0:
                keys["0x1"] = {
                    "states": {
                        "0": {
                            "actions": [
                                {
                                    "id": "com_core447_DeckPlugin::ChangePage",
                                    "settings": {
                                        "selected_page": os.path.join(self.PATH, "pages", f"SteamGames{page_idx}.json"),
                                        "deck_number": None
                                    },
                                }
                            ],
                            "media": {
                                "path": previous_icon
                            },
                            "image-control-action": 0,
                            "label-control-actions": [0, 0, 0],
                            "background-control-action": 0,
                        }
                    }
                }

            # Botón de página siguiente
            if page_idx < total_pages - 1:
                next_page_path = os.path.join(self.PATH, "pages", f"SteamGames{page_idx + 2}.json")
                keys["0x2"] = {  # Cambiar posición a 1x0
                    "states": {
                        "0": {
                            "actions": [
                                {
                                    "id": "com_core447_DeckPlugin::ChangePage",
                                    "settings": {
                                        "selected_page": next_page_path,
                                        "deck_number": None
                                    },
                                }
                            ],
                            "media": {
                                "path": next_icon
                            },
                            "label-control-actions": [0, 0, 0],
                            "background-control-action": 0,
                        }
                    }
                }

            
            for x in range(max_cols):
                for y in range(max_rows):
                    if x == 0:
                        continue

                    # get first game in the chunk and remove it from the list
                    if not games_to_append:
                        self.logger.warning("No more games to append.")
                        break
                    game = games_to_append.pop(0)
                    
                    key = f"{x}x{y}"
                    keys[key] = {
                        "states": {
                            "0": {
                                "actions": [
                                    {
                                        "id": f"{self.plugin_id}::GameLauncher",
                                        "settings": {"appid": game["appid"], "name": game["name"]},
                                    }
                                ],
                                "media": {
                                    "path": self.get_asset_path(f"{game['appid']}.jpg")
                                },
                                "image-control-action": 0,
                                "label-control-actions": [0, 0, 0],
                                "background-control-action": 0,
                            }
                        }
                    }

            page_data = {"keys": keys}
            filename = (
                f"SteamGames{page_idx + 1}.json" if total_pages > 1 else "SteamGames.json"
            )
            page_path = os.path.join(pages_dir, filename)
            with open(page_path, "w") as f:
                json.dump(page_data, f, indent=4)

            self.register_page(page_path)

    def get_main_avatar_url(self):
        # Obtiene el avatar del usuario principal, usando caché
        import time
        now = time.time()
        if self._avatar_url and (now - self._avatar_url_last_update < self._cache_ttl):
            return self._avatar_url
        url = (
            "https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/"
            f"?key={self.api_key}&steamids={self.steam_id}"
        )
        data = self._safe_get_json(url)
        players = data.get('response', {}).get('players', [])
        if players and 'avatarfull' in players[0]:
            self._avatar_url = players[0]['avatarfull']
            self._avatar_url_last_update = now
            return self._avatar_url
        return self._avatar_url

    def get_steam_friends(self, api_key=None, steam_id=None):
        # Devuelve la lista de amigos, usando caché por steamid
        import time
        now = time.time()
        # Inicializa la caché como un dict si no existe
        if not hasattr(self, '_friends_cache') or self._friends_cache is None or not isinstance(self._friends_cache, dict):
            self._friends_cache = {}
            self._friends_cache_last_update = {}
        api_key = api_key or self.api_key
        steam_id = steam_id or self.steam_id
        # Si ya está cacheado y no expiró, devuelve la caché
        if steam_id in self._friends_cache and (now - self._friends_cache_last_update.get(steam_id, 0) < self._cache_ttl):
            return self._friends_cache[steam_id]
        # Get friend list
        url = (
            "https://api.steampowered.com/ISteamUser/GetFriendList/v1/"
            f"?key={api_key}&steamid={steam_id}"
        )
        data = self._safe_get_json(url)
        ids = [f['steamid'] for f in data.get('friendslist', {}).get('friends', [])]
        if not ids:
            self._friends_cache[steam_id] = []
            self._friends_cache_last_update[steam_id] = now
            return []
        # Get player summaries
        ids_str = ",".join(ids)
        url = (
            "https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/"
            f"?key={api_key}&steamids={ids_str}"
        )
        players = self._safe_get_json(url).get('response', {}).get('players', [])
        # Solo guarda los campos relevantes: steamid, personaname, avatarfull, personastate
        friends = [
            {
                'steamid': p.get('steamid'),
                'name': p.get('personaname'),
                'avatar': p.get('avatarfull'),
                'state': p.get('personastate')
            }
            for p in players
        ]
        self._friends_cache[steam_id] = friends
        self._friends_cache_last_update[steam_id] = now
        return friends

    def refresh_friends_cache(self):
        """Refresca manualmente la caché de amigos"""
        # Reiniciar las estructuras de caché para evitar errores al refrescar
        self._friends_cache = {}
        self._friends_cache_last_update = {}
        self.friends_cache = self.get_steam_friends()
        print("[SteamFriends] Caché de amigos refrescada manualmente.")
        return self.friends_cache

    def get_installed_games(self):
        """Detecta juegos instalados por Steam y descarga sus iconos desde SteamGridDB (SGDB)."""
        import os
        import re
        import json
        import time
        import requests
        from pathlib import Path

        SGDB_API_KEY = "6d9fa654dac9d39265f691464d8414e5"

        # Carpeta para los iconos
        assets_dir = Path(__file__).parent / "assets"
        assets_dir.mkdir(parents=True, exist_ok=True)

        # Lista de posibles ubicaciones de steamapps
        libraryfolders = [
            Path.home() / ".steam/steam/steamapps",
            Path.home() / ".local/share/Steam/steamapps"
        ]

        # Agregar rutas desde libraryfolders.vdf si existen
        vdf_path = Path.home() / ".steam/steam/steamapps/libraryfolders.vdf"
        if vdf_path.exists():
            try:
                with vdf_path.open("r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        match = re.search(r'"path"\s*"([^"]+)"', line)
                        if match:
                            clean_path = bytes(match.group(1), "utf-8").decode("unicode_escape")
                            steamapps = Path(clean_path) / "steamapps"
                            if steamapps.exists():
                                libraryfolders.append(steamapps)
            except Exception as e:
                self.logger.warning(f"[SteamPlugin] Error leyendo libraryfolders.vdf: {e}")

        self.logger.warning(f"[SteamPlugin] Bibliotecas encontradas: {libraryfolders}")

        seen_appids = set()
        games = []

        headers = {
            "Authorization": f"Bearer {SGDB_API_KEY}",
            "User-Agent": "SteamPlugin/1.0"
        }

        for steamapps_path in libraryfolders:
            if not steamapps_path.exists():
                continue

            for fname in os.listdir(steamapps_path):
                if fname.startswith("appmanifest") and fname.endswith(".acf"):
                    try:
                        path = steamapps_path / fname
                        with open(path, "r", encoding="utf-8", errors="replace") as f:
                            data = f.read()

                        appid_match = re.search(r'"appid"\s*"(\d+)"', data)
                        name_match = re.search(r'"name"\s*"([^"]+)"', data)

                        if appid_match and name_match:
                            appid = appid_match.group(1)
                            name = name_match.group(1)

                            if appid in seen_appids:
                                continue
                            seen_appids.add(appid)

                            output_jpg = assets_dir / f"{appid}.jpg"

                            if output_jpg.exists():
                                self.logger.info(f"[SteamPlugin] Icono ya existe, se omite: {output_jpg}")
                            else:
                                try:
                                    # 1. Buscar el juego por nombre
                                    query = requests.utils.quote(name)
                                    search_url = f"https://www.steamgriddb.com/api/v2/search/autocomplete/{query}"
                                    res = requests.get(search_url, headers=headers)
                                    if res.status_code == 403:
                                        raise Exception("403 Forbidden (API Key inválida o límite)")
                                    search_data = res.json().get("data", [])
                                    if not search_data:
                                        raise Exception(f"No encontrado en SGDB: {name}")

                                    sgdb_id = search_data[0]["id"]

                                    # 2. Obtener iconos
                                    icons_url = f"https://www.steamgriddb.com/api/v2/icons/game/{sgdb_id}"
                                    res = requests.get(icons_url, headers=headers)
                                    icons_data = res.json().get("data", [])
                                    if not icons_data:
                                        raise Exception(f"No hay iconos en SGDB para {name}")

                                    # 3. Descargar el primero
                                    icon_data = icons_data[0]
                                    icon_url = icon_data.get("thumb", icon_data["url"])  # preferimos thumb si existe

                                    img_res = requests.get(icon_url, headers={
                                        "User-Agent": "Mozilla/5.0",
                                        "Referer": "https://www.steamgriddb.com/"
                                    })

                                    if img_res.status_code == 200 and "image" in img_res.headers.get("Content-Type", ""):
                                        with open(output_jpg, "wb") as f:
                                            f.write(img_res.content)
                                        self.logger.info(f"[SteamPlugin] Icono SGDB descargado: {output_jpg}")
                                    else:
                                        self.logger.warning(f"[SteamPlugin] Error al descargar icono: {icon_url}")
                                        raise Exception(f"Respuesta inválida al descargar imagen: status {img_res.status_code}, content-type {img_res.headers.get('Content-Type')}")


                                    self.logger.info(f"[SteamPlugin] Icono SGDB descargado: {output_jpg}")
                                    time.sleep(0.3)

                                except Exception as e:
                                    self.logger.warning(f"[SteamPlugin] SGDB error con {name} ({appid}): {e}")

                            games.append({
                                "name": name,
                                "appid": appid,
                                "path": str(path)
                            })

                    except Exception as e:
                        self.logger.warning(f"[SteamPlugin] Error leyendo {fname}: {e}")

        return games
