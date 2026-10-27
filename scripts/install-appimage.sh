#!/usr/bin/env bash
set -euo pipefail
[[ $# -eq 1 && -f "$1" ]] || { echo "Usage: bash scripts/install-appimage.sh /path/to/Music-RPC-Linux.AppImage" >&2; exit 2; }
target="$HOME/.local/bin/music-rpc"
mkdir -p "$HOME/.local/bin" "$HOME/.local/share/applications" "$HOME/.local/share/icons/hicolor/scalable/apps"
install -m 755 "$1" "$target"
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
install -m 644 "$repo/share/applications/music-rpc-linux.desktop" "$HOME/.local/share/applications/music-rpc-linux.desktop"
install -m 644 "$repo/assets/music-rpc.svg" "$HOME/.local/share/icons/hicolor/scalable/apps/music-rpc-linux.svg"
echo "Installed AppImage launcher at $target. You can now run scripts/install-native-host.sh."
