#!/usr/bin/env bash
set -euo pipefail
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[[ "$(uname -s)" == Linux ]] || { echo "A Linux build host is required; PyInstaller is not a Linux cross-compiler." >&2; exit 1; }
cd "$repo"
python3 -m venv .build-venv
. .build-venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-build.txt
rm -rf build dist AppDir
pyinstaller --noconfirm --clean --onedir --name music-rpc --paths src \
  --add-data "assets/music-rpc.svg:assets" app.py

python - "$repo/dist/third-party-licenses" <<'PY'
import importlib.metadata, pathlib, shutil, sys
target = pathlib.Path(sys.argv[1])
for dist in importlib.metadata.distributions():
    name = (dist.metadata.get("Name") or "").lower()
    if not (name.startswith("pyside6") or name.startswith("shiboken6")):
        continue
    for item in dist.files or []:
        leaf = pathlib.PurePosixPath(str(item)).name.lower()
        if leaf.startswith(("license", "copying", "notice")):
            source = pathlib.Path(dist.locate_file(item))
            if source.is_file():
                destination = target / name / pathlib.Path(str(item))
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)
PY

mkdir -p AppDir/usr/bin AppDir/usr/lib/music-rpc AppDir/usr/share/applications AppDir/usr/share/icons/hicolor/scalable/apps AppDir/usr/share/licenses/music-rpc-linux
cp -a dist/music-rpc/. AppDir/usr/lib/music-rpc/
cat > AppDir/usr/bin/music-rpc <<'EOF'
#!/usr/bin/env bash
HERE="$(dirname "$(readlink -f "$0")")"
export MUSIC_RPC_LAUNCHER="$HERE/music-rpc"
exec "$HERE/../lib/music-rpc/music-rpc" "$@"
EOF
chmod 755 AppDir/usr/bin/music-rpc
install -m 644 share/applications/music-rpc-linux.desktop AppDir/usr/share/applications/music-rpc-linux.desktop
install -m 644 share/applications/music-rpc-linux.desktop AppDir/music-rpc-linux.desktop
install -m 644 assets/music-rpc.svg AppDir/usr/share/icons/hicolor/scalable/apps/music-rpc-linux.svg
install -m 644 LICENSE AppDir/usr/share/licenses/music-rpc-linux/LICENSE
install -m 644 THIRD-PARTY-NOTICES.md AppDir/usr/share/licenses/music-rpc-linux/THIRD-PARTY-NOTICES.md
if [[ -d dist/third-party-licenses ]]; then cp -a dist/third-party-licenses AppDir/usr/share/licenses/music-rpc-linux/; fi
cp assets/music-rpc.svg AppDir/music-rpc-linux.svg
cat > AppDir/AppRun <<'EOF'
#!/usr/bin/env bash
HERE="$(dirname "$(readlink -f "$0")")"
exec "$HERE/usr/bin/music-rpc" "$@"
EOF
chmod 755 AppDir/AppRun

if ! command -v appimagetool >/dev/null; then
  echo "appimagetool is required. See https://github.com/AppImage/appimagetool/releases" >&2
  exit 2
fi
ARCH="$(uname -m)" appimagetool AppDir "dist/Music-RPC-Linux-$(cat VERSION)-$(uname -m).AppImage"
echo "AppImage built in $repo/dist. Qt shared libraries remain separate inside the AppImage for LGPL replacement compliance. Build it on Ubuntu 22.04 or another older glibc baseline for broader compatibility."
