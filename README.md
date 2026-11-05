# KiCad Android (unofficial)

An unofficial port of [KiCad](https://www.kicad.org) (master, 10.99) to Android tablets, aimed first
at use with a keyboard and mouse.

**This is not an official KiCad release and is not affiliated with or endorsed by the KiCad
project.**  KiCad is a trademark of the KiCad project; it is used here only to say what the software
is built from.  Please don't report problems with this build to KiCad's issue tracker.

Most of the porting work was done with an AI coding assistant (Claude); see the commit trailers.

## What it is

The real KiCad code, built for Android arm64:

- **UI:** wxWidgets' Qt port (wxQt) on Qt 6.12 for Android, with the fixes in `patches/wxwidgets`.
- **Canvas:** KiCad's Vulkan graphics backend on an Android surface.
- **3D viewer:** OpenGL 2.1 through [gl4es](https://github.com/ptitSeb/gl4es) on top of GLES.
- **KiCad changes:** Android support plus fixes, in `patches/kicad`.

The schematic editor, PCB editor (including the interactive router), footprint and symbol editors,
Gerber viewer, calculator, 3D viewer and `kicad-cli` all run.  Gerber and drill output have been
checked byte for byte against the macOS build of the same sources.

## Installing

1. Download the APK from the [Releases](../../releases) page (arm64 devices, Android 10 or newer).
2. Allow installing from your browser or file manager, then open the APK.
3. On first start, grant "All files access" so KiCad can open projects in shared storage.

The APK includes the KiCad symbol and footprint libraries (10.0.8), but not the 3D models: the full
set is several GB.  To see component bodies in the 3D viewer, download the `.3dshapes` folders you
need from [kicad-packages3D](https://gitlab.com/kicad/libraries/kicad-packages3D) into a folder in
shared storage (e.g. `Documents/kicad-3dmodels`), and set `KICAD10_3DMODEL_DIR` to that folder in
Preferences > Configure Paths.

## Input

- Keyboard and mouse work as on the desktop, hotkeys included.
- Touch on the canvas:
  - one finger is the left mouse button
  - two fingers pan and pinch-zoom
  - a three-finger tap zooms to fit

## Status and known issues

This is a development build.  Expect rough edges, mostly in layout at tablet scales:

- Some dialogs open partly under the status bar, or with their buttons clipped.
- Docked panels can cover the canvas on smaller screens.
- The soft keyboard can cover the field being edited.

`docs/HANDOVER.md` has the full list and the working notes.

## Building

The build runs on macOS (Apple silicon).  It needs:

- Android NDK r29, SDK build tools 35/36 and a JDK 17
- Qt 6.12.0 for Android arm64 and for macOS (the host tools)
- vcpkg

Then run:

```sh
scripts/build-deps.sh          # vcpkg dependencies for arm64-android
scripts/build-wxqt-android.sh  # wxWidgets (wxQt) with patches/wxwidgets
scripts/build-qtforandroid.sh  # Qt's Android platform plugin with patches/qtbase
scripts/build-gl4es.sh         # gl4es (libGL.so for the 3D viewer)
scripts/build-kicad-android.sh # KiCad with patches/kicad
scripts/build-kicad-apk.sh     # the APK
```

`SOURCES.md` lists the exact upstream revisions each patch series applies to.  `PLAN.md` describes
the architecture, and `docs/HANDOVER.md` describes the toolchain and test setup.

## Licence

- This repository's own files (scripts, docs, tools) are under the GNU General Public License,
  version 3 or later (see `LICENSE`).
- The patches carry the licence of the project they modify:
  - KiCad: GPL-3.0-or-later
  - wxWidgets: wxWindows Library Licence
  - Qt: LGPL-3.0
- The APK combines KiCad (GPL-3.0-or-later) with Qt (LGPL-3.0), wxWidgets, gl4es (MIT) and the
  libraries listed in `SOURCES.md`, each under its own licence.  The KiCad libraries bundled in it
  are CC-BY-SA-4.0 with the KiCad library exception.
- The corresponding source for every published APK is this repository at the release tag, plus
  the upstream revisions in `SOURCES.md`.
