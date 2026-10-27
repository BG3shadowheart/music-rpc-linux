# Music RPC for Linux

Music RPC for Linux is a tray app for **Nobara KDE Plasma** and other current Linux desktops. It requires Python 3.11 or newer for source installation. It shows the playing song in your existing Discord Rich Presence using the same application ID and layout as the Windows Music RPC: title on the first line, artist on the second, album as the image tooltip, and a progress timer when duration/position are available.

This is a new Linux-only project. It does not replace or modify the original Windows app.

## What it supports

- **Fooyin and other MPRIS players** through the session D-Bus. Fooyin is first in the default priority order. If it and another player are playing at once, Fooyin wins unless you change Settings.
- **YouTube Music in Chrome, Chromium, Brave, and Thorium** through the included unpacked extension and native messaging host. The extension only runs on `music.youtube.com`; ordinary YouTube videos are ignored.
- **Discord desktop** through its local IPC socket. There are no Discord tokens, account credentials, or cloud RPC services.
- A KDE/GNOME compatible tray menu with Open, Settings, Restart, and Quit. Startup at login is controlled from Settings and uses a per-user freedesktop autostart entry.
- Disk artwork cache, YouTube thumbnail URLs, and Apple Music/iTunes catalog artwork. Artwork lookup failures do not stop playback presence.

The app does not publish `file://` covers or upload local music files. It does not start a Cloudflare tunnel or expose a network listener. A local embedded cover without an existing public artwork URL may therefore have no image in Discord.

When online artwork lookup is enabled, the song title/artist (and album when available) are queried against public Apple Music/iTunes, Deezer, and YouTube search endpoints to find a permanent cover URL. Only the selected image URL is shared with Discord. Disable **Look up cover art online** to keep catalog lookup off; direct artwork supplied by a player or the YouTube Music extension may still be used.

## Install on Nobara KDE Plasma

Download and extract the `music-rpc-linux` source folder. Open a terminal in that folder, then run:

```bash
sudo dnf install python3 python3-pip python3-devel gcc-c++ git
bash scripts/install-source.sh
~/.local/bin/music-rpc
```

On first install, the script creates a project virtual environment and installs the pinned Linux dependencies. It does not install a background system service. The app starts only after you launch it, or after you turn on **Start when I sign in** in Settings.

The currently provided environment is Windows and has no Linux build host. This repository contains the Linux AppImage build script, but an AppImage binary was not generated or verified here. Build the AppImage on Linux with the steps in [Build packages](#build-packages); building it on Nobara is supported. To target current Linux Mint 22 as well, build on Ubuntu 24.04 or another glibc 2.39-or-older baseline.

## Install on Linux Mint

For source install, open a terminal in the extracted folder:

```bash
sudo apt update
sudo apt install python3 python3-venv python3-pip build-essential libegl1 libxkbcommon-x11-0 libxcb-cursor0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 libxcb-randr0 libxcb-render-util0 libxcb-xinerama0 libxcb-xfixes0 libxcb-shape0
bash scripts/install-source.sh
~/.local/bin/music-rpc
```

Pip installs the pinned Qt runtime into the app's virtual environment. For a future AppImage, download it to a stable location and run:

```bash
chmod +x Music-RPC-Linux-1.0.0-x86_64.AppImage
./Music-RPC-Linux-1.0.0-x86_64.AppImage
```

To install the downloaded AppImage at a stable per-user path so the browser native host can launch it:

```bash
bash scripts/install-appimage.sh ~/Downloads/Music-RPC-Linux-1.0.0-x86_64.AppImage
```

AppImages bundle the Python and Qt app but still use host Linux system libraries and the user session's D-Bus/Discord sockets. If FUSE is unavailable, AppImage's `--appimage-extract-and-run` mode may be used when supported by the AppImage runtime.

## Enable Fooyin Rich Presence

1. Install and open Fooyin. Its MPRIS interface must be enabled in Fooyin's desktop-integration settings if your build presents that option.
2. Start Music RPC from the tray or run `~/.local/bin/music-rpc`.
3. Start a track in Fooyin. The tray tooltip should change to the track and artist, and Discord should show the activity within a few seconds.
4. To verify D-Bus discovery, run:

   ```bash
   ~/.local/bin/music-rpc --dump
   ```

5. Open Settings to reorder **Player priority**. The default is `fooyin, youtube music`.

Pause clears presence by default, matching the Windows app. Turn on **Keep a paused track visible** if you want a paused activity instead.

## Enable YouTube Music in Chromium browsers

The extension has no store ID: load it unpacked, then register the native host with the actual ID your browser assigns.

1. Open `chrome://extensions` (or `brave://extensions`, `chrome://extensions` in Chromium/Thorium).
2. Turn on **Developer mode** and choose **Load unpacked**.
3. Select the `extension/` folder from this project. Leave the extension enabled.
4. Copy the extension's 32-character ID shown on the extension card.
5. Install the native host. Choose the browser you use:

   ```bash
   bash scripts/install-native-host.sh --extension-id YOUR_32_CHARACTER_ID --browser thorium
   ```

   Replace `thorium` with `chrome`, `chromium`, or `brave` as needed. To register in every detected browser profile, use `--browser all`.

6. Fully quit and reopen that browser, open `https://music.youtube.com`, and start a song. The tray tooltip should show the song. Discord should update shortly after.

The extension requests `nativeMessaging` to send playback data to the local app, `tabs` to publish the active YouTube Music tab, and host access only to `https://music.youtube.com/*`. It reads title, artist, album when present, video ID, cover URL, duration, playback state, and position from the current player. It stores no Google credentials and does not access other websites.

The native host uses Chromium's four-byte length-prefixed JSON protocol over standard input/output, then forwards messages to a user-only Unix socket under `~/.cache/music-rpc-linux`. The directory and socket are private to your Linux account. Restart the browser after installing or removing the host manifest.

## Start at login and disable

- In the tray menu, choose **Settings**, then turn **Start when I sign in** on or off. This creates or removes `~/.config/autostart/music-rpc-linux.desktop`.
- Turn **Enable Discord Rich Presence** off to keep the app available in the tray without publishing activity.
- **Quit** exits the app. It does not remove the startup setting.
- Remove the browser bridge and user launchers with:

  ```bash
  bash scripts/uninstall.sh
  ```

  This keeps your config, logs, and artwork cache. To remove those too, delete `~/.config/music-rpc-linux`, `~/.cache/music-rpc-linux`, and `~/.local/state/music-rpc-linux` yourself.

## Build packages

Build on Linux; PyInstaller does not cross-compile between Windows and Linux.

```bash
sudo dnf install python3 python3-pip gcc gcc-c++ make binutils rpm-build
# Install appimagetool from the official AppImage project, then:
bash scripts/build-linux.sh
bash scripts/build-rpm.sh
```

To create a Debian package on Debian/Ubuntu/Mint:

```bash
sudo apt install python3 python3-venv python3-pip build-essential dpkg-dev
bash scripts/build-linux.sh
bash scripts/build-deb.sh
```

Outputs are written to `dist/`. PyInstaller bundles Python and application dependencies into a directory inside the AppImage. AppImage still requires compatible host glibc, a graphical session, session D-Bus, and a locally running Discord desktop client. Build from Ubuntu 24.04 to target current Mint and Fedora-based Nobara. The NVIDIA GPU is not used by Music RPC.

## Configuration and diagnostics

- Settings: `~/.config/music-rpc-linux/config.json`
- Artwork URL cache: `~/.cache/music-rpc-linux/artwork-cache.json`
- Log: `~/.local/state/music-rpc-linux/music-rpc.log`
- Diagnostic snapshot: `music-rpc --dump`
- Debug logging: close the tray app and launch `music-rpc --debug` from a terminal.

The Discord application ID defaults to `1561450956242161745`, matching the current Windows app. To change the Discord-visible app name or icon, update that Discord application's settings in the Developer Portal; the local app cannot change Discord's registered card branding.

## Troubleshooting

### Discord activity does not appear

- Use the Discord **desktop** app, signed in to the account whose profile you are checking. Browser Discord does not expose local Rich Presence IPC.
- Confirm Discord and Music RPC run in the same Linux user session. AppImage or the source launcher should not be started with `sudo`.
- Keep Discord's activity display enabled in Discord settings. See the log for `Connected to the local Discord RPC socket` and `Discord RPC update failed`.
- Discord installed as a sandboxed Flatpak may hide the IPC socket from host apps. A host-installed Discord build is recommended; Flatpak IPC access has not been verified.

### Fooyin does not show up

- Run `music-rpc --dump` while Fooyin is playing. A `players` entry confirms MPRIS is visible.
- Confirm both apps run in the same graphical user session and that `DBUS_SESSION_BUS_ADDRESS` is set.
- Inspect MPRIS names with `busctl --user list | grep org.mpris.MediaPlayer2` if `busctl` is installed.
- Check that the priority field includes `fooyin` if another player is also playing.

### YouTube Music does not appear

- In the browser extension page, confirm Music RPC extension is enabled and its ID matches the ID in `~/.config/<browser>/NativeMessagingHosts/app.music_rpc_linux.json`.
- Confirm the manifest's `path` exists and is executable; then restart the browser.
- Verify the active tab is `music.youtube.com`, not regular YouTube. The extension is intentionally not allowed to read ordinary YouTube videos.
- Start Music RPC before testing. Check `~/.local/state/music-rpc-linux/music-rpc.log` and the extension's **Errors** panel.
- Thorium's NativeMessagingHosts folder is installed under its separate Linux profile directory; this project uses `~/.config/thorium/NativeMessagingHosts` by default. If your Thorium build uses a custom user-data directory, register the generated manifest in that profile's NativeMessagingHosts folder.

### Artwork is missing

- A blank image does not stop title/artist presence. Direct player artwork and catalog artwork are tried; bad URLs are skipped and failures are cached locally.
- Local `file://` cover art is intentionally not sent to Discord. The Linux app never uploads local music or exposes it through a public tunnel.
- Enable **Look up cover art online** in Settings to allow Apple Music catalog requests.

### Tray icon or Qt window is missing

- KDE Plasma and Cinnamon support the standard desktop tray. Confirm the system tray is visible in the panel and run `music-rpc --debug` from a terminal to see Qt plugin errors.
- If the source build lacks Qt libraries, rerun `bash scripts/install-source.sh` in the project directory.

## Tests and current verification

`python3 -m unittest discover -s tests -v` tests metadata parsing, track selection/state, artwork cache/fallback behavior, native messaging framing, Discord retry, and configuration validation. The unit tests can run on Windows because these core modules do not import Windows APIs, but the application itself is Linux-only.

The current development host is Windows with no WSL/Linux toolchain, live D-Bus session, or Linux Discord client. The Linux GUI, Fooyin integration, Chromium native host, AppImage/RPM/DEB outputs, and real Discord reconnection therefore still need a Linux-host manual run. Do not treat source tests as proof of browser or desktop integration.

## Research

- The project uses the official [MPRIS Player interface](https://specifications.freedesktop.org/mpris/latest/Player_Interface.html): metadata, `PlaybackStatus`, track ID, position, and artwork URL are read from D-Bus via the actively maintained [dbus-fast](https://pypi.org/project/dbus-fast/) asyncio library.
- Chromium native messaging uses the official [Chrome host protocol and Linux manifest locations](https://developer.chrome.com/docs/apps/nativeMessaging).
- I reviewed [mprisence](https://github.com/lazykern/mprisence), an MIT-licensed Linux project that supports Fooyin plus a YouTube Music extension bridge. It validates that MPRIS plus native messaging is the right Linux path. I did not copy its code into this project.
- Firefox is not included because this extension build and install path have not been tested there.
