#!/usr/bin/env bash
set -euo pipefail
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo"
[[ -x dist/music-rpc ]] || { echo "Run scripts/build-linux.sh first." >&2; exit 2; }
command -v rpmbuild >/dev/null || { echo "Install rpm-build first (Nobara: sudo dnf install rpm-build)." >&2; exit 2; }
top="$repo/build/rpmbuild"
mkdir -p "$top"/{BUILD,BUILDROOT,RPMS,SOURCES,SPECS,SRPMS}
rm -rf "$top/SOURCES/music-rpc-lib"
cp -a dist/music-rpc "$top/SOURCES/music-rpc-lib"
cat > "$top/SOURCES/music-rpc" <<'EOF'
#!/usr/bin/env bash
HERE="$(dirname "$(readlink -f "$0")")"
export MUSIC_RPC_LAUNCHER="$HERE/music-rpc"
exec "$HERE/../lib/music-rpc/music-rpc" "$@"
EOF
chmod 755 "$top/SOURCES/music-rpc"
cp share/applications/music-rpc-linux.desktop "$top/SOURCES/music-rpc-linux.desktop"
cp assets/music-rpc.svg "$top/SOURCES/music-rpc.svg"
cp LICENSE "$top/SOURCES/LICENSE"
cp THIRD-PARTY-NOTICES.md "$top/SOURCES/THIRD-PARTY-NOTICES.md"
if [[ -d dist/third-party-licenses ]]; then cp -a dist/third-party-licenses "$top/SOURCES/third-party-licenses"; fi
rpmbuild --define "_topdir $top" --define "_sourcedir $top/SOURCES" -bb packaging/rpm/music-rpc-linux.spec
mkdir -p dist
cp "$top"/RPMS/*/*.rpm dist/
echo "RPM built in $repo/dist"
