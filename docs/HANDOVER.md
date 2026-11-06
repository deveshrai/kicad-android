# KiCad Android port: handover / working state

Read this first after a context compaction. PLAN.md has the long-form history.

## Repos and layout
- Top level: this repository (git). Tags: `android-10.99b`, `android-10.99d`.
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
  user. The in-app version (About, kicad-cli) reads 10.99<letter> too (kicad patch 23; the
  shallow clone has no tags, so it used to say 10.99.0-unknown). **Current: 10.99ad** (tablet, release-signed; 10.99z was the first public release) (io.github.deveshrai.kicadandroid, release-signed with ~/.android/kicad-android-release.jks; GitHub deveshrai/kicad-android). Dev builds keep org.kicad.kicad (the Fold has 10.99x, the tablet 10.99n). Next letter: aa.
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
- Phone: Samsung Galaxy Z Fold 8 SM-F971B (USB serial RZGL62ZE1AZ), Android 17 / API 37, 11 GB,
  Adreno 840 (Qualcomm Vulkan; the tablet is Mali), inner 2448x1848 + cover 1248x1972 @ 420 dpi
  (scale 2.625). Attached 2026-11-04 for the priority list below.
- Emulator: AVD KiCad_Tablet35 (API 35, 8 GB, host GPU). The user starts it with
  `! scripts/emulator.sh` (since 2026-11-05 it also boots from the agent's own shell).
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

### README recordings (2026-11-06)
- **New media** in docs/media: `schematic.gif`, `pcb-layout.gif`, `3d-blinker.gif`,
  `hero-tablet-3d.jpg` and `blinker-3d-closeup.jpg`; MP4s are in `docs/media/video`.
  - Recorded on the tablet from a demo copy of the blinker; see work/blinker/README.md.
  - The device project was restored afterwards.
- **`tools/touchinject`:** gained `hover` and `click` (SOURCE_MOUSE events).
  - The router doesn't follow injected hover events, so the hand-routing part was dropped from
    the video.  Real mouse hover is untested this way.
- **Bug:** after File > Import > Specctra Session, the canvas didn't show the new tracks until the
  view moved.  The status bar already counted 51 segments.
- **Bug:** a single-finger tap on a footprint and an immediate drag sometimes started a selection
  rectangle instead of moving it.  Tap to select first, then drag.
- **Bug:** with W (wire), the wire starts at the pointer at once, so a tap afterwards adds a
  segment from wherever the pointer was.

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
7. 3D viewer: works since 10.99t (gl4es), see State below. Originally: It uses OpenGL (wxGLCanvas / QOpenGLWidget) next to our
   Vulkan GAL, so expect work: GL context on the Android surface, and raytracing performance.
8. Gerber/drill export (pcbnew Fabrication outputs, and kicad-cli on the device): untested. It
   may just work. TBD when the board gets there. Check output paths on SD card storage too.
9. Fixed in 10.99g–k during the user's copy of the board: net label dialog dead (j: Esc orphaned
   quasi-modal dialogs), chooser crash (k: Qt IME/surface deadlock-protector abort, patched
   qtforandroid), stale "already open" locks (k). The user keeps reporting crashes/issues as
   they go; log them in build/sessions/20261101-140854/notes.md.

## User priorities (2026-11-04, in this order)
1. pcbnew is slow while drawing traces etc.: profile and fix.
2. 3D viewer.
3. Zoom at the pointer location (pcbnew zooms on the centre). DONE in 10.99u (patch 0028: no cursor warping on Android), verified on the Fold with injected wheel events.
4. Touch: two-finger pinch/drag zoom+pan, one finger select/draw, three-finger tap zoom to fit. 10.99x: implemented on the
   GAL canvas (kicad 0029, wx 0021), verified on the Fold with tools/touchinject (pinch, pan,
   3-finger tap, 1-finger drag/tap). Waiting for the user's hands-on test. Not covered yet: 3D
   viewer canvas, long-press = right click, stylus.
5. Gerber export: test on an existing board, verify against the Mac build. DONE 2026-11-05 on 10.99x: pcbnew
   Fabrication Outputs > Gerbers + Generate Drill Files on the Fold (rp2350-routed) vs Mac
   kicad-cli 10.99i (--board-plot-params; drill --excellon-separate-th --excellon-oval-format
   route): all 9 Gerbers, the job file and PTH/NPTH drill files identical except the version/date
   header comments; also identical after refilling zones on both (GUI Refill vs --check-zones).
   Files in build/gerber-cmp. The Fold's in-memory board is refilled (unsaved) after this test.
6. Blue text-selection handles left on the canvas. 10.99y: qtbase patch 0003 hides them when the
   focus object or focus window goes away (tapping the Vulkan canvas window, closing a dialog);
   reproduced once on the emulator before the fix, could not make the handle appear afterwards.
   Needs a hands-on check. Also found and fixed: intermittent SIGSEGV opening an editor
   (wx patch 0022, painter used after a failed QPainter::begin in QtHandlePaintEvent).
   New bugs seen on the emulator: New Project via the Android save picker creates
   ".kicad_pro.kicad_pro" (typed name lost); adb `input text abcdef` into a wx text field gave
   "bcdefbcdefe" (emulator IME? the Fold typed correctly); the soft keyboard covers the focused
   field (the window doesn't pan).
**Re-prioritised 2026-11-06:** the user inserted two new items ahead of the rest.  The current
order is in docs/CONTINUE.md:
- P7 is an integrated autorouter (a good one).
- P8 is an integrated MCP server, with a SolidCraft-style settings page.
- The items below each move down by two: import/export becomes P9, the UI sweep P10 and the
  desktop-GL work P11.

7. Import/export third-party symbols, footprints and 3D models (test: SnapEDA ESP32-S31-WROOM-1-N16R16V).
8. UI sweep: fields too big/small or not scaling (check on the Fold's 2.625 scale too).
   Seen so far (Fold): Plot dialog's top edge sits under the status bar and its bottom buttons
   are clipped; the drill files dialog draws without a background/frame; Properties + Appearance
   panels cover the whole canvas on the inner screen at startup.
9. Desktop GL elsewhere (user, 2026-11-05): find every other place that uses desktop OpenGL and
   make it work on Android. Candidates: 3D model preview in footprint properties / footprint
   wizard (EDA_3D_MODEL_VIEWER, same gl4es path, untested), raytracing renderer (display pass),
   OpenGL GAL fallback (opengl_gal.cpp, shaders are desktop GLSL; the "Accelerated" GAL is
   Vulkan here, check what Preferences > Graphics offers), anything using HIDPI_GL_CANVAS,
   3D viewer screenshot/copy (glReadPixels, FBO save/restore at eda_3d_canvas.cpp:730).

## RP2350 board experiment
- Project on the tablet: files/RP2350A-DevBoard (the user is building it by hand).
- Scripted version on the emulator: work/rp2350 (gen_sch.py, place_pcb.py with R=8 mm rounded
  corners; Freerouting jar in toolchain/freerouting; running it requires the user to start it).
  Findings in docs/experiment-rp2350-board.md.


## State at 2026-11-05 (P1 done, P2 done)
- P1 router lag: done in 10.99o/q/r (motion coalescing, QtGui detach NOP, plugin graphics-buffer
  backing store). Fold profile: router 78% of main thread, repaint 3.5%. Waiting for the user's
  verdict on feel; next options if still slow: -O3/LTO for the router, other router modes.
- P2 3D viewer: WORKS in 10.99t on the Fold (OpenGL renderer: board, copper, mask, silk,
  holes, STEP component bodies; rotation; 1-8 ms frames). gl4es (toolchain/gl4es, bc4314d,
  unmodified; its AGENTS.md forbids AI-written gl4es code; scripts/build-gl4es.sh) ships as
  libGL.so in android-extra-libs; Qt's loader loads it at startup, gl4es picks up the
  QOpenGLWidget GLES context by itself. KiCad patch 0027: RTLD_NODELETE pin in
  GL_UTILS::DetectGLBackend (glad dlclose()s libGL.so), and S3D_PLUGIN_MANAGER names the
  3 plugins on Android (native libs stay in the APK, no dir to scan).
  3D MODELS ARE NOT SHIPPED (several GB). For the test, the board's 11 models were pushed to
  files/kicad-data/kicad/3dmodels (build/3dmodels-rp2350; USB_C HRO TYPE-C-31-M-12 and
  QFN-60 7x7 don't exist in kicad-packages3D). Open idea: download a board's missing models
  on demand from gitlab kicad-packages3D. Untested: raytracing renderer, 3D model preview in
  footprint properties, rendering after app suspend/resume.
- Fold test setup: project /sdcard/Documents/rp2350-routed (work/rp2350/routed1), set as
  open_projects in files/settings/kicad/10.99/kicad.json; Ctrl+P opens pcbnew; close the
  Properties panel (tap 762,367) to see the canvas. Screens: scripts/fold-shot.sh OUT.png [cover].
  Profiling: /data/local/tmp/simpleperf record --app org.kicad.kicad -g; symbols via the NDK's
  binary_cache_builder.py -lib build/kicad-android, host simpleperf report --symfs binary_cache.
- Emulator: `scripts/emulator.sh` (now boots from the agent shell too; earlier it needed `!`); kill it
  with `adb -e emu kill` before every build. API 35, 2560x1600 @320 dpi (scale 2.0).
- UI sweep notes so far (P8): pcbnew docks fill the Fold's inner screen (no canvas until
  Properties is closed); project tree icon covers the start of the project name; dock titles
  tiny everywhere; emulator: frame doesn't fill the screen (bands above/below).
- Open notes from the board copy: datasheet via Properties panel (file://) and https untested;
  value field fixed in 10.99m (2pt font root cause) but not yet confirmed by the user.

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
10.99r adds QAndroidPlatformRhiBackingStore (pixels offered as a QPlatformGraphicsBuffer) and
scripts/patch-qtgui.sh NOPs the compositor's QImage::detach() in the prebuilt libQt6Gui
(byte-checked at 0x3ea158; run by build-kicad-apk.sh). Together they remove the full-window
image copy per widget repaint (was 15-21% of the main thread while routing on the Fold).
10.99o: EDA_DRAW_PANEL_GAL coalesces pointer motion on Android (Qt does no move compression).

## Multi-touch injector (tools/touchinject)
adb `input` is single-touch only.  tools/touchinject/build.sh builds Touch.java into a dex and
pushes it; run `adb shell CLASSPATH=/data/local/tmp/touch.dex app_process / Touch <cmd>` with
pinch CX CY FROM TO | pan X Y DX DY | tap3 X Y | drag X Y DX DY (display pixels).  It injects
through InputManager(Global).injectInputEvent with the shell's permission, like scrcpy.

## Publishing a release
KA_APP_ID=io.github.deveshrai.kicadandroid KA_APP_LABEL="KiCad Android" \
KA_RELEASE_KEYSTORE=~/.android/kicad-android-release.jks KICAD_APK_MODE=release scripts/build-kicad-apk.sh
gives build/KiCad-Android-<version>.apk.  Keep the keystore and its .pass file backed up:
updates must be signed with the same key.  Then commit, push to GitHub, tag android-<version> and `gh release create`.
The user wants every publish to update the git repo too (2026-11-06).  App name: just "KiCad Android"
(no "(unofficial)"); the README keeps a short not-affiliated note.

## 2026-11-06: end-to-end blinker test on the Galaxy Tab (10.99ad)
work/blinker: new project via the Android save picker → generated schematic (ERC 0) → Update PCB →
placement → Freerouting → zones, DRC 0 + parity → 3D with STEP models.  All in the app on the tablet.
Fixed on the way (wx 0023-0025): picker URIs (msf:/numeric Downloads ids) → paths; DoGetPosition null
crash (New Project); wxFileName::Mkdir failing on /storage/emulated (save/backup to shared storage).
Open, found in this test:
- Preferences > Configure Paths: grid cells can't be edited (tap, double tap, F2) and the dialog then
  ignores Cancel/Escape — forced a restart.  So KICAD10_3DMODEL_DIR can't be set; the test used
  absolute model paths in the board.
- First launch after the welcome wizard: the frame fills ~77% of the screen, centred (fine after a
  restart).  The tablet's display size is set below default (density 280 vs 320).
- The Specctra import picker listed a 0-byte "blinker" placeholder that the picker left in Downloads.
- Wireless adb only (USB dropped); `svc power stayon true` is set on the tablet.

## Integrated autorouter (P7, 10.99ae)
Route > Autoroute Board... routes the whole board on the device with Freerouting 2.5.0.
- **Java side:** `scripts/build-autorouter.sh` clones Freerouting v2.5.0 into toolchain/freerouting-src,
  applies `patches/freerouting` on branch `android`, and compiles only the routing core (no gui/, api/,
  cli/) plus `android/autorouter/java` (the driver, `io.github.deveshrai.kicadandroid.Autorouter`)
  into build/autorouter/autorouter.jar.  build-kicad-apk.sh copies it into the APK's libs/.
  - Freerouting needs Java 25; D8 (build-tools 36) reads class files only up to Java 24, so the
    script relabels the class files as Java 21 (the bytecode is the same).  After a Freerouting
    update, run `scripts/check-autorouter-api.sh` to list library calls Android lacks (java.awt,
    JMX, virtual threads, java.net.http).  The 2.5.0 list is all off the routing path or caught.
  - The patch: board statistics use their own Rectangle2D.Float; ConductionArea keeps its awt cache
    in an Object field with a fixed serialVersionUID (board hashing serializes the board, and
    serialization reflects on field and method types); logging goes to stdout (logcat); no
    analytics client is ever created.
  - Test without the app: `adb push build/autorouter/autorouter.dex /data/local/tmp/` then
    `adb shell CLASSPATH=/data/local/tmp/autorouter.dex app_process / io.github.deveshrai.kicadandroid.Autorouter in.dsn out.ses [passes [optimize]]`.
- **KiCad side** (kicad patch 0030): kiplatform/autorouter.h (JNI bridge; the class comes from the app's
  ClassLoader, held as a global ref, because FindClass on native threads only sees system classes),
  dialogs/dialog_autoroute.cpp (export DSN to the cache dir, route on a thread, poll every 250 ms,
  import each snapshot SES into one undo step with APPEND_UNDO, Keep/Discard, zone refill).
- **Results:** blinker (stripped of tracks): 20/20 connections, 0 vias, 162 mm, < 1 s on the Tab S12+;
  DRC 0 errors, 0 unconnected.  rp2350_ili9341 (hard: 185 connections, GND planes): Freerouting
  itself stops with 33 unrouted after 21 passes on the Mac (358 s); the tablet is about 3x slower per pass.
- Debug APKs install as org.kicad.kicad (a second "KiCad Android" icon); test release-signed builds
  on io.github.deveshrai.kicadandroid.
- Files pushed with adb are invisible to the system picker until scanned:
  `adb shell am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d file:///sdcard/...`.

## Integrated MCP server (P8, 10.99af)
Preferences > MCP Server turns on an MCP server inside KiCad (Streamable HTTP, JSON responses, no SSE)
at `http://127.0.0.1:27880/mcp` ("This device", e.g. Claude Code in Termux) or on the Wi-Fi address
("Another computer").  Clients send `Authorization: Bearer <token>`; the token is generated once and
kept in kicad_common.json (`mcp.*`); New Token replaces it.  The page shows the ready-made
`claude --mcp-config '...'` and `claude mcp add --transport http ...` lines with Copy buttons and a
live status line (listening / connected client, last request, last tool).
- **Code** (kicad patch 0031): include/api/mcp_server.h + common/api/mcp_server.cpp (HTTP/1.1 keep-alive
  server on a thread, JSON-RPC: initialize, ping, tools/list, tools/call; tools run on the main
  thread via CallAfter, so every change is a normal commit the user sees and can undo);
  common/dialogs/panel_mcp_server.cpp; KICAD_API_SERVER::HandleRequest() runs IPC API requests in
  process; api/src/kiapi_json.cpp converts JSON <-> API messages **inside libkiapi**, because
  libprotobuf.a is linked into several .so files and only kiapi's copy has the API descriptors
  (lookups from kicommon find nothing).  pcbnew/api/mcp_tools_pcb.cpp adds pcb_* tools while the
  board editor is open.
- **Tools** (all declared up front, because clients read the list once; editors attach handlers with
  SetToolHandler while open, and the tools say "open the board editor" otherwise): kicad_status,
  kicad_open_editor (project manager's editPCB/editSchematic actions; the GUI has no OpenDocument
  handler, only kicad-cli's server does), kicad_api (any IPC API command by name, args as JSON with .proto field
  names), kicad_api_commands, kicad_api_describe; pcb_board_summary, pcb_move_footprint,
  pcb_run_drc, pcb_autoroute (runs off the main thread, imports snapshots live).
- **Test from the Mac:** `adb forward tcp:27880 tcp:27880`, then curl JSON-RPC or
  `claude -p ... --strict-mcp-config --mcp-config '{"mcpServers":{"kicad":{"type":"http","url":"http://127.0.0.1:27880/mcp","headers":{"Authorization":"Bearer <token>"}}}}'`
  (tested with Claude Code 2.1.319: from a cold start it opened the board editor, autorouted the
  blinker 20/20, ran DRC 0/0 and reported, while the tablet showed it happening).  Remote mode tested from the Mac over Wi-Fi.
- Origin header check: when bound to 127.0.0.1, requests from web pages (non-localhost Origin) get 403.
- Next ideas: sch_* tools (ERC, annotate, update PCB from schematic), a board picture tool
  (RunBoardJobExportPng), Windows support (sockets are POSIX only).
