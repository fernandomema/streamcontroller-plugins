#!/usr/bin/env sh

# Copy all plugin directories to the StreamController plugins directory
DEST="$HOME/.var/app/com.core447.StreamController/data/plugins"

# Create destination directory if it doesn't exist
mkdir -p "$DEST"

for plugin_dir in com_*; do
    if [ -d "$plugin_dir" ]; then
        echo "Copying $plugin_dir to $DEST" >&2
        cp -r "$plugin_dir" "$DEST/"
    fi
done

