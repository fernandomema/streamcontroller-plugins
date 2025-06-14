from .actions.FriendSlot.FriendSlot import FriendSlot

# StreamController Steam Friends Plugin

from src.backend.PluginManager.PluginBase import PluginBase
from src.backend.PluginManager.ActionHolder import ActionHolder
from src.backend.PluginManager.ActionInputSupport import ActionInputSupport
from src.backend.DeckManagement.InputIdentifier import Input
import requests 


class SteamFriendsPlugin(PluginBase):
    def __init__(self):
        import time
        super().__init__()
        self.lm = self.locale_manager

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

        # Register plugin
        self.register(
            plugin_name = self.lm.get("plugin.name"),
            github_repo = "https://github.com/fernandomema/StreamControllerSteamPlugin",
            plugin_version = "1.0.0",
            app_version = "1.2.0-alpha"
        )
        # Registrar la página dinámica de amigos si existe
        self.register_friends_page()

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

    def get_main_avatar_url(self):
        # Obtiene el avatar del usuario principal, usando caché
        import time
        now = time.time()
        if self._avatar_url and (now - self._avatar_url_last_update < self._cache_ttl):
            return self._avatar_url
        try:
            url = f"https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/?key={self.api_key}&steamids={self.steam_id}"
            resp = requests.get(url)
            players = resp.json().get('response', {}).get('players', [])
            if players and 'avatarfull' in players[0]:
                self._avatar_url = players[0]['avatarfull']
                self._avatar_url_last_update = now
                return self._avatar_url
        except Exception:
            pass
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
        url = f"https://api.steampowered.com/ISteamUser/GetFriendList/v1/?key={api_key}&steamid={steam_id}"
        resp = requests.get(url)
        data = resp.json()
        ids = [f['steamid'] for f in data.get('friendslist', {}).get('friends', [])]
        if not ids:
            self._friends_cache[steam_id] = []
            self._friends_cache_last_update[steam_id] = now
            return []
        # Get player summaries
        ids_str = ",".join(ids)
        url = f"https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/?key={api_key}&steamids={ids_str}"
        resp = requests.get(url)
        players = resp.json().get('response', {}).get('players', [])
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
        self._friends_cache_last_update = 0
        self.friends_cache = self.get_steam_friends()
        print("[SteamFriends] Caché de amigos refrescada manualmente.")
        return self.friends_cache
