#!/usr/bin/env bash
set -euo pipefail
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[[ "$(uname -s)" == Linux ]] || { echo "This installer is Linux-only." >&2; exit 1; }
python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)' || { echo "Python 3.11 or newer is required." >&2; exit 1; }
python3 -m venv "$repo/.venv"
"$repo/.venv/bin/python" -m pip install --upgrade pip
"$repo/.venv/bin/pip" install -r "$repo/requirements-linux.txt"
mkdir -p "$HOME/.local/bin" "$HOME/.local/share/applications" "$HOME/.local/share/icons/hicolor/scalable/apps"
cat > "$HOME/.local/bin/music-rpc" <<EOF
#!/usr/bin/env bash
export MUSIC_RPC_LAUNCHER="$HOME/.local/bin/music-rpc"
exec "$repo/.venv/bin/python" "$repo/app.py" "\$@"
EOF
chmod 755 "$HOME/.local/bin/music-rpc"
install -m 644 "$repo/share/applications/music-rpc-linux.desktop" "$HOME/.local/share/applications/music-rpc-linux.desktop"
install -m 644 "$repo/assets/music-rpc.svg" "$HOME/.local/share/icons/hicolor/scalable/apps/music-rpc-linux.svg"
echo "Installed Music RPC source launcher. Run: music-rpc"
echo "If ~/.local/bin is not on PATH, sign out and back in or run ~/.local/bin/music-rpc."
