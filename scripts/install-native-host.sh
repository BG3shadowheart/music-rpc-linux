#!/usr/bin/env bash
set -euo pipefail

usage() { echo "Usage: $0 --extension-id ID [--browser chrome|chromium|brave|thorium|all]"; }
extension_id=""
browser="all"
while (($#)); do
  case "$1" in
    --extension-id) extension_id="${2:-}"; shift 2 ;;
    --browser) browser="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) usage >&2; exit 2 ;;
  esac
done
[[ "$extension_id" =~ ^[a-p]{32}$ ]] || { echo "Copy the 32-character ID shown for your unpacked extension in chrome://extensions." >&2; exit 2; }

name="app.music_rpc_linux"
config_root="${XDG_CONFIG_HOME:-$HOME/.config}"
bin_dir="${HOME}/.local/bin"
mkdir -p "$bin_dir"
chmod 700 "$bin_dir"
app_command=""
if [[ -x "$HOME/.local/bin/music-rpc" ]]; then app_command="$HOME/.local/bin/music-rpc"; fi
if [[ -z "$app_command" ]]; then app_command="$(command -v music-rpc || true)"; fi
if [[ -z "$app_command" ]]; then
  repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
  if [[ -x "$repo_root/.venv/bin/python" ]]; then
    printf '#!/usr/bin/env bash\nexec %q %q --native-host\n' "$repo_root/.venv/bin/python" "$repo_root/app.py" > "$bin_dir/music-rpc-native-host"
    chmod 755 "$bin_dir/music-rpc-native-host"
    app_command="already-written"
  else
    echo "Install Music RPC first with scripts/install-source.sh or place its AppImage on PATH." >&2
    exit 1
  fi
fi
if [[ "$app_command" != already-written ]]; then
  printf '#!/usr/bin/env bash\nexec %q --native-host\n' "$app_command" > "$bin_dir/music-rpc-native-host"
  chmod 755 "$bin_dir/music-rpc-native-host"
fi

declare -A dirs=(
  [chrome]="$config_root/google-chrome/NativeMessagingHosts"
  [chromium]="$config_root/chromium/NativeMessagingHosts"
  [brave]="$config_root/BraveSoftware/Brave-Browser/NativeMessagingHosts"
  [thorium]="$config_root/thorium/NativeMessagingHosts"
)
if [[ "$browser" == all ]]; then
  targets=()
  for key in chrome chromium brave thorium; do
    case "$key" in
      chrome) marker="$config_root/google-chrome" ;;
      chromium) marker="$config_root/chromium" ;;
      brave) marker="$config_root/BraveSoftware/Brave-Browser" ;;
      thorium) marker="$config_root/thorium" ;;
    esac
    [[ -d "$marker" ]] && targets+=("$key")
  done
  ((${#targets[@]})) || { echo "No supported browser profile found; choose --browser explicitly." >&2; exit 1; }
else
  [[ -n "${dirs[$browser]:-}" ]] || { usage >&2; exit 2; }
  targets=("$browser")
fi

for key in "${targets[@]}"; do
  dir="${dirs[$key]}"
  mkdir -p "$dir"
  manifest="$dir/$name.json"
  python3 - "$manifest" "$name" "$bin_dir/music-rpc-native-host" "$extension_id" <<'PY'
import json, pathlib, sys
path, name, host, extension_id = sys.argv[1:]
data = {"name": name, "description": "Music RPC local browser bridge", "path": host,
        "type": "stdio", "allowed_origins": [f"chrome-extension://{extension_id}/"]}
pathlib.Path(path).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
PY
  chmod 600 "$manifest"
  echo "Installed native host for $key: $manifest"
done
echo "Restart the browser after loading the extension."
