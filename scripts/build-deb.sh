#!/usr/bin/env bash
set -euo pipefail
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo"
[[ -x dist/music-rpc ]] || { echo "Run scripts/build-linux.sh first." >&2; exit 2; }
stage="build/deb-root"
rm -rf "$stage"
mkdir -p "$stage/usr/bin" "$stage/usr/lib/music-rpc" "$stage/usr/share/applications" "$stage/usr/share/icons/hicolor/scalable/apps" "$stage/usr/share/doc/music-rpc-linux" "$stage/usr/share/licenses/music-rpc-linux" "$stage/DEBIAN"
cp -a dist/music-rpc/. "$stage/usr/lib/music-rpc/"
cat > "$stage/usr/bin/music-rpc" <<'EOF'
#!/usr/bin/env bash
HERE="$(dirname "$(readlink -f "$0")")"
export MUSIC_RPC_LAUNCHER="$HERE/music-rpc"
exec "$HERE/../lib/music-rpc/music-rpc" "$@"
EOF
chmod 755 "$stage/usr/bin/music-rpc"
install -m 644 share/applications/music-rpc-linux.desktop "$stage/usr/share/applications/"
install -m 644 assets/music-rpc.svg "$stage/usr/share/icons/hicolor/scalable/apps/music-rpc-linux.svg"
install -m 644 LICENSE THIRD-PARTY-NOTICES.md "$stage/usr/share/doc/music-rpc-linux/"
install -m 644 LICENSE "$stage/usr/share/licenses/music-rpc-linux/"
if [[ -d dist/third-party-licenses ]]; then cp -a dist/third-party-licenses "$stage/usr/share/licenses/music-rpc-linux/"; fi
cat > "$stage/DEBIAN/control" <<EOF
Package: music-rpc-linux
Version: $(cat VERSION)
Section: sound
Priority: optional
Architecture: $(dpkg --print-architecture)
Maintainer: Music RPC contributors
Description: YouTube Music and MPRIS Discord Rich Presence for Linux
EOF
dpkg-deb --root-owner-group --build "$stage" "dist/music-rpc-linux_$(cat VERSION)_$(dpkg --print-architecture).deb"
