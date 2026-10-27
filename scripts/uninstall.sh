#!/usr/bin/env bash
set -euo pipefail
bash "$(dirname "${BASH_SOURCE[0]}")/uninstall-native-host.sh"
rm -f "$HOME/.local/bin/music-rpc" \
      "$HOME/.local/share/applications/music-rpc-linux.desktop" \
      "$HOME/.local/share/icons/hicolor/scalable/apps/music-rpc-linux.svg" \
      "${XDG_CONFIG_HOME:-$HOME/.config}/autostart/music-rpc-linux.desktop"
echo "Removed Music RPC launchers and startup registration. Config, logs and artwork cache were kept."
