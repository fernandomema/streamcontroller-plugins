# StreamController Plugins

This repository contains plugins for [StreamController](https://github.com/Core447/StreamController).  
Currently it includes the **Steam Friends** plugin located in `com_fernandomema_StreamControllerSteamPlugin` and the **FreeDesktop Launcher** plugin located in `com_fernandomema_FreeDesktopLauncher`.

The Steam Friends plugin displays your Steam friends and their current status. It requires a Steam Web API key and the SteamID of your account. These can be configured from the plugin settings inside the application.

## Installation

Run the provided `install_plugins.sh` script to copy the plugin directory to StreamController's user plugin folder:

```sh
./install_plugins.sh
```

The script copies each `com_*` directory into `~/.var/app/com.core447.StreamController/data/plugins`. After copying, restart StreamController and enable the plugin from the plugin manager.

## License

The Steam Friends plugin is released under the MIT License. See the `LICENSE` file inside the plugin directory for details.
