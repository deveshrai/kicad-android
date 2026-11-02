# KiCad Android port: handover / working state

Read this first after a context compaction. PLAN.md has the long-form history.

## Repos and layout
- Top level `/Users/devesh/projects/KiCadAndroid0` (git). Tags: `android-10.99b`, `android-10.99d`.
- `kicad/` is a separate git repo on branch `android`. Export patches after each commit:
  `cd kicad && rm -f ../patches/kicad/*.patch && git format-patch -q 113c71d5 -o ../patches/kicad/`
- `toolchain/wxWidgets` is a git repo on branch `kicad-android`. Export patches with
  `git format-patch -1 -o ../../patches/wxwidgets/ --start-number N` (10 so far).
- KiCad commits need an `Assisted-by: Claude Opus 5.5` trailer, plus Co-Authored-By and
  Claude-Session. No agent-created MRs or issues upstream.

## Build / install loop
```
source scripts/env.sh                      # always; puts adb, JAVA_HOME etc on PATH
cmake --build build/wxqt-android && cmake --install build/wxqt-android   # only after wx changes
cmake --build build/kicad-android > build/logs/kicad-build.log 2>&1
scripts/build-kicad-apk.sh > build/logs/kicad-apk.log 2>&1   # -> build/KiCad-debug.apk
adb -s R5GL8486SDD install -r -g build/KiCad-debug.apk       # tablet; emulator is `adb -e`
```
- Versioning: `scripts/bump-build.sh` advances android/BUILD_LETTER a..z, then aa, ab .. zz
  (it sets KICAD_VERSION_EXTRA). APK versionName is 10.99<letter>, versionCode is
  1099000 + letter index (a=1 .. z=26, aa=27 .. zz=702). Bump for every build handed to the
  user. **Current: 10.99k** (installed on the tablet, plus the USB-C footprint filter fix; the next is l).
- APK bundles the KiCad 10.0.8 libraries (`scripts/fetch-kicad-libs.sh`; asset tree
  `kicad-libs`, extracted once per version) and libkimalloc (mimalloc new/delete;
  `scripts/build-kimalloc.sh`, loaded before libc++_shared). APK is about 375 MB.
- Launcher icon sources: `android/icon`; resources: `android/package/res`.

## Devices
- Tablet: Samsung Galaxy Tab S12+ SM-X840 (serial R5GL8486SDD), Android 17 / API 37, 12 GB,
  Mali-G1-Ultra (Vulkan), 2800x1752 @ 280 dpi (scale 1.75). The user has authorized using it
  for testing. DeX works; the user switches modes on request. In DeX the task can be resized
  over adb: `am task resize <taskId> l t r b`.
- Wireless adb (paired with this Mac, 2026-11-01): `adb -s adb-R5GL8486SDD-5yIE9r._adb-tls-connect._tcp ...`
  (mDNS name survives port changes; last seen at 192.168.1.2:45355). USB serial is R5GL8486SDD.
- Emulator: AVD KiCad_Tablet35 (API 35, 8 GB, host GPU). The user starts it with
  `! /Users/devesh/projects/KiCadAndroid0/scripts/emulator.sh`.
- Testing quirks: on the tablet, `input tap` works and Ctrl+E opens eeschema from the project
  manager. `input text` needs the chooser search field to have focus (reopen the chooser with A).
  Avoid tapping the bottom-left or bottom-right corners and avoid KEYCODE_BACK when no keyboard
  is shown: they hit Android Back/nav and background the app. adb can't inject mouse buttons
  (`input mouse scroll` works).
- Debug: `files/wxtrace` (via run-as) or `setprop debug.kicad.wxtrace KICAD_RHI` (the property
  wins) sends traces to logcat. Vulkan opt-out: `novulkan` file in the app home or
  `setprop debug.kicad.vulkan 0`.
- Session recorder: `scripts/record-session.sh -s R5GL8486SDD` (screen, logcat, memory into
  build/sessions/<ts>).

## Tablet session findings (build/sessions/20261101-140854/notes.md has the full log)
Fixed and verified on the tablet:
- Crash on selecting a symbol: Vulkan surface lifetime. We now make our own VkSurfaceKHR on the
  QtWindow's TextureView Surface via JNI, with a process-wide live-window registry hung off qApp.
- Blank GPU previews at 1.75 scale: ±1 px extent tolerance.
- Frozen canvas after a DeX resize or a DeX/tablet switch: the surface is rebuilt if the extent
  wait exceeds 300 ms.
- DeX startup crash: wxQt status bar re-entrancy (wx patch 10).
- Frames always maximized on Android, so they fill the DeX window.
- Dialogs fit and are centred in the top-level frame (no longer under the status bar).
- Chooser splitter panes are kept visible; the footprint selector combo has a usable height.
- Wheel zoom works in DeX (injected events).

Open (next):
1. (done, 10.99f) User storage: all-files access (asked once at first launch) + system picker; content:// URIs of local storage mapped to paths (wx patch 11). Default Documents = /sdcard/Documents. Notes: picker opens in Downloads and doesn't prefill the filename; Drive/cloud documents have no path and are ignored.
2. "Edit schematic" when eeschema is already open behind the project manager doesn't raise it.
3. Blue text-selection handles left on the canvas after the soft keyboard closes.
4. Memory: about 3.3 GB PSS with the full library loaded (lazy loading?).
5. (done) User confirmed on 10.99e: DeX/tablet switch fix works; middle- and right-button pan work in DeX and tablet mode, also after switching.
6. Older items: menu label "Non+KiCad"; the default template isn't preselected in New Project;
   the Qt file dialog is tiny; the soft keyboard pops up over the canvas; mouse-wheel zoom in
   pcbnew is centre-based; there may be a residual eeschema redraw issue at startup.
7. 3D viewer: not yet tried on Android. It uses OpenGL (wxGLCanvas / QOpenGLWidget) next to our
   Vulkan GAL, so expect work: GL context on the Android surface, and raytracing performance.
8. Gerber/drill export (pcbnew Fabrication outputs, and kicad-cli on the device): untested. It
   may just work. TBD when the board gets there. Check output paths on SD card storage too.
9. Fixed in 10.99g–k during the user's copy of the board: net label dialog dead (j: Esc orphaned
   quasi-modal dialogs), chooser crash (k: Qt IME/surface deadlock-protector abort, patched
   qtforandroid), stale "already open" locks (k). The user keeps reporting crashes/issues as
   they go; log them in build/sessions/20261101-140854/notes.md.

## RP2350 board experiment
- Project on the tablet: files/RP2350A-DevBoard (the user is building it by hand).
- Scripted version on the emulator: work/rp2350 (gen_sch.py, place_pcb.py with R=8 mm rounded
  corners; Freerouting jar in toolchain/freerouting; running it requires the user to start it).
  Findings in docs/experiment-rp2350-board.md.

## Later phase (after the open list): touch
- Two-finger pinch/drag: zoom and pan the canvas.
- One finger: select, draw wires/tracks, etc. (as the left mouse button).
- Three-finger tap: zoom to fit.

## Mac version (native wxOSX, Metal canvas), same KiCad tree
- `scripts/build-wxosx.sh` (wx Cocoa -> build/install/wxosx), deps in `deps-mac/` (vcpkg arm64-osx;
  ngspice from deps/overlay-ports, spirv-cross host tool), `scripts/build-kicad-mac.sh`
  (-> build/install/kicad-mac/KiCad.app, kept as **dist/mac/KiCad-10.99k.app**, ad-hoc signed).
- dist app also carries the 10.0.8 symbol/footprint libs in Contents/SharedSupport; global
  sym-lib-table/fp-lib-table copied to ~/Library/Preferences/kicad/10.99.
- kicad-cli: `dist/mac/KiCad-10.99k.app/Contents/MacOS/kicad-cli` (ERC/PDF/BOM verified).
- RP2350 deliverables: work/rp2350/out (sch, PDF, netlist, BOM grouped by MPN, ERC 0).

## Keyboard driving the app over adb (work/rp2350/app_drive.py)
- Arrow keys move the KiCad cursor one grid step; Return clicks (needs 10.99k: wx patch 15 +
  kiplatform virtual pointer). Never tap during a run (taps move the pointer). Chooser: Ctrl+A,
  name, Tab, Enter. Paused at 10.99k after UserLAnd came to the front.

## Patched Qt Android plugin (10.99k)
Qt's prebuilt qtforandroid aborts when a new window needs a Surface while an IME query holds the
deadlock protector. toolchain/qtbase-src (sparse qtbase v6.12.0, branch kicad-android, patch in
patches/qtbase) is rebuilt by scripts/build-qtforandroid.sh (android/qtforandroid/CMakeLists.txt),
which swaps it into the Qt install (stock kept as *.orig) before build-kicad-apk.sh.
