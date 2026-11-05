<div align="center">

# KiCad Android (unofficial)

**The real KiCad 10.99 EDA suite, running natively on Android tablets and foldables.**

Schematics, PCB layout with the interactive router, 3D viewer and Gerber output, built from
upstream KiCad sources.

[![Release](https://img.shields.io/github/v/release/deveshrai/kicad-android?include_prereleases&label=APK)](https://github.com/deveshrai/kicad-android/releases)
[![Licence: GPL-3.0-or-later](https://img.shields.io/badge/licence-GPL--3.0--or--later-blue)](LICENSE)
![Android 10+](https://img.shields.io/badge/Android-10%2B%20arm64-3DDC84?logo=android&logoColor=white)
![KiCad 10.99](https://img.shields.io/badge/KiCad-10.99%20(master)-314CB0)

<img src="docs/media/hero-3d-fold.jpg" alt="KiCad's 3D viewer showing an RP2350 board on a Galaxy Z Fold" width="860">

<sub>The 3D viewer on a Samsung Galaxy Z Fold: STEP models rendered through OpenGL 2.1 on GLES.</sub>

</div>

> **Not an official KiCad release.**  This project is not affiliated with or endorsed by the KiCad
> project.  "KiCad" is a trademark of the KiCad project and is used here only to say what this
> software is built from.  Please report problems here, not on KiCad's issue tracker.

## Highlights

- **Full desktop KiCad, not a viewer.**  It includes the project manager, schematic editor, PCB
  editor and push-and-shove router, footprint and symbol editors, Gerber viewer, calculator and
  `kicad-cli`.
- **GPU canvas.**  It runs on KiCad's Vulkan backend, with pointer motion coalesced so the
  interactive router keeps up.
- **3D viewer** with STEP component models, through [gl4es](https://github.com/ptitSeb/gl4es).
- **Desktop-identical output.**  Gerbers and drill files match the macOS build of the same sources
  byte for byte.  [How we checked](docs/CHANGES.md#how-it-was-checked).
- **Keyboard and mouse first**, with KiCad's normal hotkeys, plus touch gestures on the canvas.
- **Libraries included.**  The KiCad 10.0.8 symbol and footprint libraries are bundled.

## See it run

<table>
<tr>
<td width="50%" align="center">
<img src="docs/media/touch-gestures.gif" alt="Pinch zoom, two-finger pan and three-finger tap to fit in the PCB editor"><br>
<sub><b>Touch:</b> pinch to zoom, two fingers to pan, three-finger tap to fit</sub>
</td>
<td width="50%" align="center">
<img src="docs/media/3d-viewer.gif" alt="Rotating a board in the 3D viewer by dragging"><br>
<sub><b>3D viewer:</b> drag to orbit the board and its STEP models</sub>
</td>
</tr>
<tr>
<td width="50%" align="center">
<img src="docs/media/pcbnew-fold.jpg" alt="PCB editor with a routed RP2350 board on a Galaxy Z Fold"><br>
<sub><b>PCB editor</b> on the Fold's inner screen</sub>
</td>
<td width="50%" align="center">
<img src="docs/eeschema-android.png" alt="Schematic editor with KiCad's pic_programmer demo"><br>
<sub><b>Schematic editor</b> with a KiCad demo project</sub>
</td>
</tr>
</table>

## Install

1. Download the APK from [**Releases**](https://github.com/deveshrai/kicad-android/releases).
   It needs an arm64 device with Android 10 or newer.
2. Let your browser or file manager install apps, then open the APK.
3. On first start, grant **All files access**, so KiCad can open projects in shared storage
   (`Documents`).

A keyboard and mouse are recommended: a Bluetooth or USB keyboard, or Samsung DeX.

<details>
<summary><b>3D models</b> (not bundled, the full set is several GB)</summary>

Download the `.3dshapes` folders you need from
[kicad-packages3D](https://gitlab.com/kicad/libraries/kicad-packages3D) into a folder in shared
storage (e.g. `Documents/kicad-3dmodels`).  Then set `KICAD10_3DMODEL_DIR` to that folder in
**Preferences > Configure Paths**.

</details>

## Using it

| Input | What it does |
|---|---|
| Mouse and keyboard | Same as KiCad on the desktop, hotkeys included |
| One finger on the canvas | Left mouse button: click, select, drag, draw tracks and wires |
| Two fingers | Pinch to zoom around your fingers; drag to pan |
| Three-finger tap | Zoom to fit |

## How it works

KiCad's UI is written against wxWidgets, which has no Android port.  This build runs wxWidgets'
**Qt port** on **Qt 6 for Android**.  KiCad draws its canvas with **Vulkan** and its 3D view with
**OpenGL 2.1 via gl4es**.  It stays close to upstream: everything is a patch series against exact
upstream revisions.

| Layer | Changes |
|---|---|
| KiCad | [`patches/kicad`](patches/kicad): Android platform layer, Vulkan canvas, touch, 3D viewer, a few general fixes |
| wxWidgets (wxQt) | [`patches/wxwidgets`](patches/wxwidgets): input, dialogs, fonts, Android pickers and intents, crash fixes |
| Qt for Android | [`patches/qtbase`](patches/qtbase): faster window composition, input-method fixes |

**[Read the full write-up of the changes →](docs/CHANGES.md)**

## Status

This is a development build of KiCad master.  It works for real design work with a keyboard and
mouse.  Known rough edges:

- Some dialogs open partly under the status bar, or with their buttons clipped, at tablet scales.
- Docked panels can cover the canvas on smaller screens.  Close them from **View > Panels**.
- The soft keyboard can cover the field being edited.
- The 3D viewer doesn't take touch gestures yet; it gets the standard mouse emulation.

The working notes and the full list are in [`docs/HANDOVER.md`](docs/HANDOVER.md).

## Building from source

The build runs on macOS (Apple silicon).  It needs:

- Android NDK r29, SDK build tools 35/36 and a JDK 17
- Qt 6.12.0 for Android arm64 and for macOS
- vcpkg

Then run:

```sh
scripts/build-deps.sh          # vcpkg dependencies for arm64-android
scripts/build-wxqt-android.sh  # wxWidgets (wxQt) + patches/wxwidgets
scripts/build-qtforandroid.sh  # Qt's Android platform plugin + patches/qtbase
scripts/build-gl4es.sh         # libGL.so for the 3D viewer
scripts/build-kicad-android.sh # KiCad + patches/kicad
scripts/build-kicad-apk.sh     # the APK
```

- [`SOURCES.md`](SOURCES.md) lists the exact upstream revision each patch series applies to.
- [`PLAN.md`](PLAN.md) covers the architecture.
- [`docs/HANDOVER.md`](docs/HANDOVER.md) covers the toolchain, devices and test setup.

Most of this port was written with an AI coding assistant (Claude); see the commit trailers.

## Licence

- This repository's own files are licensed **GPL-3.0-or-later** ([`LICENSE`](LICENSE)).
- Each patch carries the licence of the project it modifies:
  - KiCad: GPL-3.0-or-later
  - wxWidgets: wxWindows Library Licence
  - Qt: LGPL-3.0
- The APK combines KiCad with Qt (LGPL-3.0), wxWidgets, gl4es (MIT) and the libraries in
  [`SOURCES.md`](SOURCES.md), each under its own licence.  The bundled KiCad libraries are
  CC-BY-SA-4.0 with the KiCad library exception.
- The corresponding source for every published APK is this repository at the release tag, together
  with the upstream revisions in `SOURCES.md`.
