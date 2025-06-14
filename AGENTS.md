# AGENTS Instructions

This repository hosts StreamController plugins.

## Creating a new plugin

1. Create a new folder in the repository root. The folder name must be the plugin
   ID in *reversed domain* notation, replacing dots with underscores. Example:
   ```bash
   mkdir com_example_plugin
   ```
2. Place your plugin files (`main.py`, `manifest.json`, `actions/`, etc.) inside
   this directory.

## Development summary

1. Come up with an idea for a plugin that improves your workflow.
2. Clone the StreamController application and set up a Python virtual
   environment:
   ```bash
   git clone https://github.com/StreamController/StreamController
   cd StreamController
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
3. Optionally copy the official plugin template to bootstrap your plugin.
4. Fill in `manifest.json` with your version, id, name, author, compatible app
   version and GitHub link. Optional fields include descriptions, tags and
   minimum app version.
5. After testing, submit your plugin to the store.

The classes provided by StreamController (`ActionBase`, `BackendBase` and
`PluginBase`) expose convenience methods for manipulating keys, registering
actions, managing settings and launching backends. See the source code for
details.

