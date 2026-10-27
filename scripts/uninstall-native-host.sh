#!/usr/bin/env bash
set -euo pipefail
config_root="${XDG_CONFIG_HOME:-$HOME/.config}"
name="app.music_rpc_linux.json"
for dir in \
  "$config_root/google-chrome/NativeMessagingHosts" \
  "$config_root/chromium/NativeMessagingHosts" \
  "$config_root/BraveSoftware/Brave-Browser/NativeMessagingHosts" \
  "$config_root/thorium/NativeMessagingHosts"; do
  rm -f "$dir/$name"
done
rm -f "$HOME/.local/bin/music-rpc-native-host"
echo "Removed Music RPC Chromium native-messaging registrations."
