Name:           music-rpc-linux
Version:        1.0.0
Release:        1%{?dist}
Summary:        YouTube Music and MPRIS Discord Rich Presence
License:        MIT
BuildArch:      x86_64
Requires:       glibc
Requires:       libstdc++

%description
Linux desktop tray application publishing MPRIS and YouTube Music playback to Discord.

%install
install -D -m 0755 %{_sourcedir}/music-rpc %{buildroot}%{_bindir}/music-rpc
mkdir -p %{buildroot}%{_libdir}/music-rpc
cp -a %{_sourcedir}/music-rpc-lib/. %{buildroot}%{_libdir}/music-rpc/
install -D -m 0644 %{_sourcedir}/music-rpc-linux.desktop %{buildroot}%{_datadir}/applications/music-rpc-linux.desktop
install -D -m 0644 %{_sourcedir}/music-rpc.svg %{buildroot}%{_datadir}/icons/hicolor/scalable/apps/music-rpc-linux.svg
install -D -m 0644 %{_sourcedir}/LICENSE %{buildroot}%{_datadir}/licenses/music-rpc-linux/LICENSE
install -D -m 0644 %{_sourcedir}/THIRD-PARTY-NOTICES.md %{buildroot}%{_datadir}/licenses/music-rpc-linux/THIRD-PARTY-NOTICES.md
if [ -d %{_sourcedir}/third-party-licenses ]; then cp -a %{_sourcedir}/third-party-licenses %{buildroot}%{_datadir}/licenses/music-rpc-linux/; fi

%files
%{_bindir}/music-rpc
%{_libdir}/music-rpc
%{_datadir}/applications/music-rpc-linux.desktop
%{_datadir}/icons/hicolor/scalable/apps/music-rpc-linux.svg
%{_datadir}/licenses/music-rpc-linux
