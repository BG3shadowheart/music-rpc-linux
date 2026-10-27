# Third-party software notices

The Linux package pins the following direct dependencies:

- **dbus-fast 5.2.0** — MIT. Python D-Bus client implementation. <https://pypi.org/project/dbus-fast/>
- **pypresence 4.6.2** — MIT. Discord local IPC client. <https://pypi.org/project/pypresence/>
- **PySide6 6.11.3 / Qt for Python** — LGPL-3.0-only or GPL-2.0-only or GPL-3.0-only, as offered by the upstream distribution. This project uses the LGPL-compatible option. <https://doc.qt.io/qtforpython-6/licenses.html>
- **PyInstaller 6.22.3** (build tool only) — GPL-2.0-or-later with an exception for distributing bundled applications. <https://pyinstaller.org/en/stable/license.html>

The AppImage build uses PyInstaller's one-directory layout so Qt shared libraries remain separate and replaceable in an extracted application directory. Redistributors should include the license texts shipped with the PySide6/Qt wheels and preserve the ability to replace those Qt libraries. The AppImage runtime tool is a build-time tool and is not bundled by this project.

No third-party extension source code is copied into the included browser extension. The MIT-licensed `mprisence` project was reviewed as a design reference only.
