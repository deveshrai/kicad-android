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

## Library packages: import and export (P9, 10.99ah)
Project manager **File > Import Library Package...** / **Export Library Package...**, and MCP
tools kicad_import_library_package / kicad_export_library_package (kicad patch 0033,
kicad/library_package_import.{h,cpp}).
- **Import:**
  - **Unpacking:** PROJECT_ARCHIVER::Unarchive unpacks into a staging folder in the user cache dir. WX_FILENAME::ResolveArchiveEntryPath refuses entries that would land outside it (zip slip).
  - **Sorting the files:**
    - `.kicad_sym`, and `.lib` with its `.dcm` (Legacy), become symbol libraries.
    - `.kicad_mod` files are grouped by their parent `.pretty` folder, or under the package name if loose.
    - `.step`, `.stp`, `.wrl` and `.wrz` go to `<pkg>.3dshapes`.
    - Anything else (datasheets, other CAD formats) is counted and left out.
  - **Package name:** the zip's single top-level folder (SnapEDA's `<part>-KiCad.zip` holds `<part>/`), else the zip name.
  - **Destination:** `${KICAD10_3RD_PARTY}/libraries/<pkg>` for all projects (Documents/KiCad/10.99/3rdparty on Android), or `<project>/libraries/<pkg>` for this project. URIs and model paths are normalized to `${KICAD10_3RD_PARTY}` or `${KIPRJMOD}`.
  - **Model paths:** each footprint's `(model "...")` is matched against the package's models, first by file name, then by stem (a `.wrl` reference finds the `.step`). A package with one footprint and one model, where the footprint names no model, gets one added, with a note.
  - **Footprint fields:** symbols' Footprint fields are rewritten to the nickname each footprint library actually got (nickname clashes get `_2` and so on).
  - **Re-import:** a row whose description is "Imported from <zip>" is updated, not duplicated. A same-zip row in the other scope keeps the same nickname, since the project row shadows the global one.
  - **Reloading:**
    1. LoadGlobalTables or ProjectChanged.
    2. PreloadLibraries on the sch and pcb kifaces.
    3. ReloadLibraryEntry plus a **synchronous** LoadLibraryEntry for the package's own libraries. Otherwise an MCP client that places the symbol right away races the background preload ("symbol not found").
    4. MAIL_RELOAD_LIB to the open library frames.
- **Export:** a symbol library (KiCad's own 10.x libraries are `.kicad_symdir` folders of one-symbol files, which are merged into one `.kicad_sym`), plus every footprint its symbols' Footprint fields name (only from KiCad `.pretty` libraries), plus their models. Model paths are resolved with the project's variables and rewritten to `<name>.3dshapes/<file>` inside the zip. Models not on the device are summed up in one note.
- **Tested on the tablet (work/library-packages/test_import.py, over MCP):**
  - **SnapEDA ESP32-S31-WROOM-1-N16R16V, imported:** symbol (61 pins), footprint (69 pads) and STEP model all loaded, and the 3D render shows the module on its pads. The footprint's model path pointed at /Users/dstein/dev/...; it is rewritten.
  - **Scopes:** global and project.
  - **Round trips:** S31 export, and stock RF_Module export (85 symbols merged from the symdir, 43 footprints), each re-imported with all libraries loaded.
  - **GUI menus:** the Android file picker (SAF) for open and save, and the scope question.
- **Known:**
  - The GUI has no handler for the IPC API's DeleteLibraryTableEntry. To remove a test row, edit the table file.
  - The wxSingleChoiceDialog (export library list) draws without a title bar (P10).

## Agent feedback fixes (10.99aj, 2026-11-09)
Another Claude Code session working on the user's RP2350A schematic over MCP wrote up what failed. The user also reported a grainy schematic and a black 3D viewer. KiCad patches 0034-0037.
- **Schematic API "missing" (AS_UNHANDLED):**
  - The eeschema handlers were all there. Requests without a full `document` reached no handler: the schematic handler wants type, project name and path, the board handler wants the board file name. "the requested project  is not open" was the same thing.
  - `kicad_api` now fills document specifiers from the open editors, at the top level or in `header`. The type comes from the command's package. A common command naming no type is tried on each open editor.
  - AS_UNHANDLED errors now say what's missing. Code: `KiapiJsonToMessage(..., KIAPI_DOCUMENT_DEFAULTS, ...)` in api/src/kiapi_json.cpp, called from MCP_SERVER::CallApi.
- **Edits on disk not shown:**
  - `DOCUMENT_FILE_WATCHER` (common/document_file_watcher.cpp) polls the editor's files every second and reports a change once it has held for two polls. It waits while a modal dialog or interactive tool is up.
  - The editor reloads (ReloadFromDisk) and shows an info bar. With unsaved edits it asks Reload / Keep My Edits first.
  - Saves and ReloadFromDisk take a new baseline, so neither is reported.
  - Tested on the tablet: a pushed edit shows up within 4 s, the dialog works, and our own SaveDocument isn't reloaded.
  - `RevertDocument` works too now, since it's no longer missing its document.
- **New MCP tools:**
  - `kicad_screenshot`: a PNG of the app, about 1 s. It's a Qt grab of the active frame and its dialogs, with each TextureView GPU window drawn in from `TextureView.getBitmap()` on the Android UI thread (KIPLATFORM::UI::GrabAppImage). `max_width` defaults to 1400.
  - `kicad_open_project`: takes a .kicad_pro or its folder. KICAD_MANAGER_FRAME::LoadProject asks about unsaved editors itself.
- **Black RunBoardJobExportRender:** fields left out of the request (lights, zoom) now keep the job's defaults. They used to be zeroed.
- **Grainy schematic (not new; it's the modern GAL at 1.75x):**
  - The canvas renders at full resolution (swapchain 2142x1391 = 1224x795 x 1.75) with High Quality AA, i.e. 2x supersampled layer targets.
  - The SDF shaders cut edges hard in a supersampled target, so pixels only had 5 coverage levels; a screencap had exactly 70/115/159/203/248. Stroke text one device pixel wide looked stepped.
  - Fix: the fragment shaders ramp edges over one target texel (dFdx/dFdy, `edgeRamp()`), never wider than before. After the fix the same crop has about 50 levels and axis-aligned strokes are still crisp.
  - Not changed: the minimum stroke width is one device pixel (0.57 logical px at 1.75x), as on desktop. A logical-pixel minimum would make text bolder; consider it if the user still finds it faint.
- **3D viewer black when opened a second time (per app run, board change or not):**
  - gl4es keeps one global GL state and can't see EGL context switches made outside it (NOX11; its NewGLState/ActivateGLState aren't exported, and EGL_WRAPPER doesn't track state either).
  - GL_CONTEXT_MANAGER now gives every context after the first its own gl4es instance: `android_dlopen_ext(path from dladdr, ANDROID_DLEXT_FORCE_LOAD)` on the same libGL.so in the APK.
  - It points glad at that instance on LockCtx and in the new `LoadGL()`. The three gladLoaderLoadGL() call sites use LoadGL().
  - The instances come from the APK rather than from copies in app storage. (The 10.99aj note
    said Android blocks dlopen from app data; that's wrong: the router process loads numpy and
    scipy from there. Only exec of app files is blocked.)
  - About 2.5 MB per opening; instances are never unloaded.
  - The footprint properties 3D preview gets its own instance the same way; untested.
- **Memory note:** with the ESP32-S3 board and the 3D viewer, the app's PSS is about 4.6 GB: 2.7 GB "Unknown" (mimalloc arenas), 1.25 GB GL mtrack and 0.39 GB EGL. It stays flat across viewer opens. Worth a look in the UI/perf sweep.

## Library Files page and Run Setup Wizard (10.99aq, 2026-11-13)
The user's request: 3D models as an option, and an update option for the bundled libraries (they
first asked to drop the bundled libraries, then kept them once that saved only 65 MB of 437).
KiCad patch 0044.  Checked on the emulator (fresh data) and on the tablet (page shown).
- **Bundling:** unchanged; `KICAD_BUNDLE_LIBS=0` still leaves the libraries out.  The 3D models are
  not bundled.
- **`STARTWIZARD_PROVIDER_LIBRARY_FILES`** (`common/startwizard/`, Android only, before the
  library tables page):
  - Shown once: `NeedsUserInput()` until `<stock>/.library-files-page-shown` exists (written by
    Finish/ApplyDefaults); `OfferOnRerun()` true.
  - Options: download the 3D models; update to the newest release of the installed series (GitLab
    tags API on kicad-symbols, `^10.` -> highest x.y.z; same release as installed = "already
    newest", no download); install archives.
  - Release shown: `<stock>/.libraries-release` (after an update), else the bundled stamp
    `.libs-extracted`, else 10.0.8.
  - Downloads: `KICAD_CURL_EASY` to `<user cache>/library-downloads`, then unpacked into
    `<stock>/.staging`; `commitStaging()` swaps symbols/, footprints/, 3dmodels/, blocks/ whole
    (old one renamed, restored on failure) and merges template/.  Library set and 3D models are
    committed independently.  Archives the user picks are merged straight into the stock folder.
  - `mapEntry()` sorts archive entries by content; a `sym-lib-table`/`fp-lib-table` is taken only
    if it points at `${KICAD*_SYMBOL_DIR}`/`_FOOTPRINT_DIR}` (not a project's own table).
    Zip, tar and tar.gz by magic bytes (wxZipInputStream, wxZlibInputStream + wxTarInputStream).
  - Progress: worker thread, wxProgressDialog polled from the main thread, Cancel honoured.
  - Afterwards: a chained "KiCad" row is added to existing global tables that lack one.  It must
    not throw: an earlier `LoadGlobalTables()` call before the tables existed stopped the later
    pages' Finish, so the global tables were never created and the wizard came back.
  - Measured: 3D 663 MB download, 3231 MB installed, about 1 minute on the emulator's network;
    10.0.8 is the newest 10.0 release (2026-11-13).
- **Preferences > Run Setup Wizard** (`KICAD_MANAGER_ACTIONS::runSetupWizard`):
  `STARTWIZARD::CheckAndRun( frame, true )` shows pages that need input or `OfferOnRerun()`
  (Library Files; Updates & Privacy, filled from the current settings); Cancel changes nothing;
  the welcome text says so.
- **HTTPS on Android:** OpenSSL can't use `/system/etc/security/cacerts` as CAPATH (files are named
  by the old MD5 subject hash), so `KICAD_CURL_EASY` passes the concatenated system certificates
  as `CURLOPT_CAINFO_BLOB`.  This also fixes every other curl use (PCM, update checks).
- **Library tables page:** its intro wrapped to the panel's width, which is wider than the page,
  so lines were cut off; on Android it wraps at 600 DIP.  Not re-checked on a fresh install.

## P11: raytracing, STEP export, dialogs above the taskbar (10.99ap, 2026-11-13)
KiCad patch 0043, wx patch 0034, qtbase patch 0006.  Checked on the tablet.
- **Raytracing crashed** (SIGSEGV in gl4es `glDrawPixels`, `raster.c:596`): the raytracer
  writes into a pixel unpack buffer and calls `glDrawPixels(..., 0)`; gl4es reads the 0 as a
  client pointer.  On Android `RENDER_3D_RAYTRACE_GL` keeps the pixels in a `std::vector`
  (`mapPixels()`/`unmapPixels()`) and draws them as a textured quad in window coordinates
  (`drawClientPixels()`).
  - The quad came out black until another, untextured glBegin/glEnd draw followed it before
    the texture was unbound (found with a red test square).  glFlush after the quad did not
    help, nor did vertex arrays.  So one transparent pixel is drawn after it.  Not understood
    inside gl4es; gl4es stays unmodified.
  - The pixels are valid (logged), the alpha test reference is 0.2, the viewport is right.
  - While a render runs, blocks not rendered yet are black instead of showing the preview.
  - Export Image from the 3D viewer writes the raytraced view (1376x816 for a 1404x835
    request).  Copy to clipboard does nothing visible (Android's clipboard takes no images).
- **STEP export from the board editor** ran kicad-cli as a child process: `execvp(base.apk!
  /lib/arm64-v8a/kicad-cli.so)` fails (error 2).  On Android `DIALOG_EXPORT_STEP` runs
  `EXPORTER_STEP` in-process on the open board (`exportInProcess()`), with the parameters from
  `fillJob()` (shared with the job editor), and shows the messages in a message box.
  - Checked: the STEP of work/rp2350's scratch copy is 95.000 x 65.000 mm, holes 2.7 mm at
    (106,66) (189,66) (106,119) (189,119), corner radius 8 mm, body 1.51 mm (the dielectric of the
    1.6 mm stackup; copper and mask are off by default).  Imported into the user's SolidCraft
    (Insert > Insert STEP): Properties gave 95.00 x 65.00 x 1.51 mm, 168 vertices, 9136.88 mm3.
  - The 3D models aren't on the tablet, so components are skipped ("Could not add 3D model").
  - **Other apps' pickers did not list the new STEP** until a media scan
    (`am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d file://...`).  Files that
    KiCad writes are not added to MediaStore; worth a `MediaScannerConnection.scanFile()` after
    exports.
- **Footprint Properties reached under the taskbar** (OK/Cancel hidden), two causes:
  - wxQt passed top-level size hints, which include the frame in wx, as the widget's
    (client) minimum size, so the window stayed a title bar taller than its cap (wx 0034).
  - QtWindow's queued fit reports could arrive after a newer geometry from Qt and undo it;
    each geometry now has a serial and stale reports are dropped, and the fit respects the
    window's minimum size, passed with the geometry (qtbase 0006).
- **3D preview in Footprint Properties:** shows the footprint; no model on the tablet to check.

## P10: hotkey names, launcher labels, layer pair presets, sheet properties (10.99ao, 2026-11-13)
KiCad patch 0042, wx patch 0033.  Checked on the emulator (the user was using the tablet).
- **Hotkeys list cut names short in the middle** ("Move B...rd Down", "PCB ...itor", "D...n"),
  only some of them, in wide columns.  Cause: `wxDataViewCustomRendererBase::WXCallRender` makes
  a left-aligned cell's text rect exactly `GetTextExtent()` wide (QFontMetrics advance of the
  whole string, with kerning), and `wxControl::Ellipsize()` then compares against the generic
  `GetPartialTextExtents()`, which sums single-character widths (no kerning) and came out a few
  px wider for strings with kerning pairs.  wx 0033: on wxQt the generic `wxTextMeasure` measures
  each prefix as a whole (up to 512 characters).  Only `src/generic/textmeasure.cpp` changes, so
  no KiCad rebuild; wx is a shared library.
- **Launcher labels:** on Android a tap on a launcher's name or description starts it (upstream
  keeps them inert on desktop).  Deferred and looked up by id, like the button's own click.
- **Select Copper Layer Pair:** the presets grid gets a minimum height of four rows (with no
  presets its best size was the header alone).
- **Drawing Sheet Editor:** the Properties pane is at least 320 DIP wide on Android (the saved
  default is 150 px).
- **Seen on the emulator:** the drawing sheet canvas is black until the first touch.

## Dialog frames and Googlebook OS (10.99an, 2026-11-13)
Dialogs were bare rectangles: Android has no window manager for the windows inside an activity,
so nothing drew a frame or a title, and a dialog could not be moved.  qtbase patch 0005 and
`android/qt-patches/org/qtproject/qt/android/QtWindow.java`; KiCad patch 0041.

- **Where:** in Qt's Android platform plugin and its `QtWindow` view, not in wxQt.  Every
  `Qt::Dialog` window gets the frame, wx dialogs and Qt's own alike, and no wx or KiCad rebuild
  was needed.  (Doing it in wxDialog with an inner content widget, like wxFrame's central
  widget, means overriding the client area maths throughout wxQt.)
- **C++ (`qandroidplatformwindow.cpp`):**
  - `wantsDecoration()`: a top-level `Qt::Dialog` of a Qt application, not frameless, not
    `CustomizeWindowHint` without `WindowTitleHint`, not maximized or full screen.
    `QT_ANDROID_NO_WINDOW_DECORATION=1` turns it off.
  - `frameMargins()` returns the title strip (1.75 lines of the app font, at least 30 dp) and a
    1 dp border, in whole device independent pixels.  QWidget picks them up as its frame strut,
    so `frameGeometry()`, `pos()` and `move()` (which wxQt uses for top-level windows) include
    them and `geometry()` stays the client area.  DIALOG_SHIM's Android clamp therefore fits the
    whole frame inside the main window.
  - `setGeometry()` still gives QtWindow the client rect; a frame-inclusive position (from
    `QWindow::setFramePosition()` or a widget moved before it had a window) is shifted by the
    margins first.
  - `setWindowTitle()` and `updateDecoration()` pass the title, the margins and colours from the
    application palette to Java.  A margin change after the window is shown is reported as a
    geometry change, since QWidget only reads the margins in move and resize events.
  - Natives `decorationGeometry(id, x, y, w, h)` (`handleGeometryChange` with QtWindow's new
    client rect, after a drag or a fit, below) and `decorationClose(id)` (`handleCloseEvent`),
    both queued to the GUI thread.
- **Java (`QtWindow.java`, a full copy of Qt 6.12's file):**
  - The view is the client rect grown by the margins; `onMeasure`/`onLayout` put the children
    (surface, QtEditText, native views, child windows) in the client area; `onDraw` paints the
    border, the strip, the title (ellipsized) and a cross.
  - Touches that start on the strip drag the window (raw coordinates, touch slop first, clamped
    so the strip stays below the status bar and reachable); a tap on the cross closes it.  Other
    touches and generic motion events are offset into client coordinates before
    `QtInputDelegate`; hover over the frame is swallowed.
  - `fitInParent()`, after each geometry from Qt and on attach: Qt places dialogs inside the
    screen, which on Android includes the system bars, so tall dialogs reached under the status
    bar (the "Plot dialog under the status bar" item).  A decorated window is moved, and made
    smaller if it doesn't fit, to stay between the status bar and the navigation bar or taskbar
    (`getSafeInsets`, not the IME), and Qt is told the new rect.  If Qt asks again for the size
    it just shrank, it gets it (no tug of war with a minimum size).
  - `getLocationOnScreen()` returns the client area's corner, since Qt's text handles and edit
    popup add Qt coordinates to it.
  - It also holds the TextureView change (window surfaces are always TextureViews) that the
    bytecode patch `android/qt-patches/bytecode/patch_qtwindow.py` used to make; that script is
    gone, and `scripts/build-kicad-apk.sh` replaces `QtWindow*.class` in the jar.
- **KiCad 0041:**
  - The startup wizard called `SetWindowStyleFlag( wxRESIZE_BORDER )`, which drops
    `wxCAPTION` (no title bar on any platform); it now adds the flag to its style.
  - "Ω⋅m" uses U+00B7 on Android: Android's fonts have no U+22C5.
  - `KIPLATFORM::UI::GetUsableScreenRect()` (Android): the top-level frame's screen rect less
    its QWindow's `safeAreaMargins()`.  DIALOG_SHIM's Android fit uses it instead of the frame's
    whole rect, so a dialog's size and minimum size are capped to the room between the status
    bar and the navigation bar, and it is centred there.  Before, Symbol Properties on the
    emulator was 1570 px tall in a 1600 px screen and its title sat under the status bar.
- **Checked on the emulator (2026-11-13; the tablet was not connected):** Preferences has the
  strip with title and cross; dragging moves it and taps inside land on the right control
  afterwards; the cross closes it with a mouse click; reopened, it fits inside the main window;
  typing in its filter box works with touch and mouse focus.  Message boxes are Android
  AlertDialogs and keep their own look.
- **Known gaps:** no resizing from the edges; `kicad_screenshot` composes from widgets and does
  not draw the frame; the strip colours are taken when the dialog is shown, not on a live theme
  change.
- **Googlebook OS:** README, badges, release notes and the repo description now say the app is
  for Android and Googlebook OS (the user's request).  Not tested on a Googlebook; the APK is
  arm64 only.  The README hero (`docs/media/hero-laptop-tablet.png`, drawn by
  `scripts/make-hero.py` from app-window screenshots) shows a laptop and a tablet.

## Crash fixes: submenus and tree selection (10.99am, 2026-11-12)
The user reported a crash on 10.99al; the tablet's crash buffer (`adb logcat -b crash -d`) held
two different ones, each seen more than once.

- **Submenu crash (11-10 22:56 and 23:27, schematic editor context menu, mouse or pen hover):**
  - **Stack:** null read in QMenuSloppyState::setSubMenuPopup, from
    QMenu::internalDelayedPopup() (the submenu hover timer).
  - **Cause:** QAndroidPlatformWindow::setVisible() ended with QPlatformWindow::setVisible(),
    which flushes *all* window system events.  A pointer move queued at that moment was delivered
    inside QWidget::show() of the submenu.  The parent menu handled it (pointer on a separator or
    off the items, sloppy state off), closed the submenu and cleared activeMenu, which
    internalDelayedPopup() used next without a check.
  - **Fix:** qtbase patch 0004: send the expose event and flush with
    QEventLoop::ExcludeUserInputEvents.  Input events stay queued for the event loop, so no
    window show or hide re-enters widget code with input any more.
  - **Check:** not reproduced on demand (about 60 timed hovers with a virtual mouse on 10.99al,
    the window is a few ms wide); on 10.99am the same sweeps open and close the submenus normally.
  - **Virtual mouse on a device without root:** `adb shell uinput -` takes JSON commands
    (register / delay / inject).  Pointer acceleration depends on speed, so keep one step size
    and rate (2 units every 4 ms is about 2 px per unit on the tablet).
- **Tree crash (11-09 15:02, 11-11 09:07 and 13:14):**
  - **Stack:** wxTreeCtrl::GetItemData from the wxTreeEvent constructor, from
    wxQTreeWidget::EmitSelectChangeEvent in the deferred (CallAfter) wxEVT_TREE_SEL_CHANGED.
    This is not the 10.99ai crash, although the top frame is the same.
  - **Cause:** wxQt caches the item for the next selection event (m_currentItem) and deletes
    items with the QTreeWidget's signals blocked, so the cache is not updated.  After
    DeleteAllItems() it points at a deleted item until the current item changes again; a
    selection change without a new current item (clearing the selection, selecting in a
    wxTR_MULTIPLE tree, or an event that was already queued) then read freed memory.
  - **Fix:** wx patch 0027: forget an item when it is deleted, and take the event's item from
    the selection when the cached one is gone.
  - **Check:** by reading the code against the three traces; which KiCad tree the user was in is
    not known (candidates: project tree, DRC rule editor, toolbar customization).
- **Installing on the tablet:** the app there is the release ID.  `build/KiCad-debug.apk` is
  `org.kicad.kicad` and installs as a second app; build the release APK (see "Publishing a
  release") and install that.

## Fixes from the crash hunt (10.99am, 2026-11-13)
After the two crash fixes the app was swept on the tablet for more (every board editor action
through the API, then by hand).  No further crash that a user can reach; the findings, with
causes, are in `build/findings-am.md`.  KiCad patch 0040, wx patches 0028 to 0032.

- **Keys (wxQt):**
  - **wxEVT_CHAR_HOOK** was never sent (wx 0032).  It is what closes a dialog on Escape while a
    grid has the focus.  Qt offers an unaccepted key press to each parent widget with the same
    event object, so `QtHandleKeyEvent` sends the hook for the first of them only (it compares
    the event pointer, timestamp and key).
  - **Key events carry the window id** (wx 0031).  wxPropertyGrid binds its editors' key
    handlers by id; without it Escape did not cancel an edit in the Properties panel.
- **Message boxes (Escape and BACK):**
  - A wxMessageDialog is a QMessageBox, which Qt shows as an Android AlertDialog from
    `QtMessageDialogHelper.java`, not cancelable once it has buttons.
  - `android/qt-patches/org/qtproject/qt/android/QtMessageDialogHelper.java` replaces the class:
    cancelable when there is an escape button (Cancel; else the only button; else No), and
    cancelling reports that button's id.  `scripts/build-kicad-apk.sh` compiles it against
    android.jar and Qt6Android.jar and zips it over the stock classes (the file also holds
    `ButtonStruct` and `QtNativeDialogHelper`).
  - `scripts/build-qtforandroid.sh` only rebuilds the platform plugin (.so), not the jar, so
    Java fixes go in `android/qt-patches`, not `patches/qtbase`.
- **Narrow strings are UTF-8 (wx 0029):** wx's Android stand-ins for mbstowcs/wcstombs copied one
  byte per character, so wxConvLibc read source literals as Latin-1 ("kΩ" showed as "kâ¦").
- **Tree icons (wx 0030):** wxQt's tree never called `setIconSize()`, so the images covered the
  start of the item text (Project Files tree).
- **No size grip in dialogs (wx 0028).**
- **Launchers:** `COMMON_CONTROL::Execute` starts the Gerber Viewer, Calculator Tools and the
  Drawing Sheet Editor in-process on Android (there is no executable to run).
  - The calculator skips its `SetSizeHints/SetSize/Centre` so it stays maximized: a second
    `Maximize()` is a no-op in wxQt once the Qt window state says "maximized".
  - `GERBVIEW_FRAME` handles `wxID_CLOSE` (the File menu has Close, not Quit, in-process).
- **Frames shown modally (`KIWAY_PLAYER::ShowModal()`):**
  - It maximizes the frame *before* showing it.  Qt's Android window applies the maximized
    geometry in `setVisible(true)` only, so `Maximize()` on a visible frame changes the state
    and not the size (the same reason the calculator must not be resized after maximizing).
  - The footprint chooser loads no window state, so it opened at its fitted size over the menu
    bar.  On Android it skips its saved-rect `SetSize()` and focuses its filter box with
    `CallAfter` in `Show()` (the first-paint focus did not take).
  - After the loop it gives the focus to the caller's canvas.  `SetFocus()` on a frame focuses
    the frame's own widget in wxQt, hotkeys come from the canvas, and with touch nothing hovers
    over the canvas to take the focus back: keys were dead until the canvas was tapped.
  - Tapping outside a modal frame also took its key focus away; moot now that it fills the window.
- **3D viewer see-through after Home and back:** `OglMakeFrameOpaque()` before `SwapBuffers()`.
- **MCP:** `kicad_open_editor` rejects editor names other than `pcb` and `schematic`.
- **Checked on the tablet (2026-11-13):** all of the above; Escape and BACK at "Save Changes?"
  cancel it; the schematic editor prompts to save after a real edit.
- **Not fixed:**
  - API-only crashes: `RunAction` of an action that needs a parameter (the `dd*` drag-and-drop
    actions, `pcb_control.cpp:192`) without one.
  - BACK on the 3D viewer sends the app to the background.
  - A freeze seen once after BACK and relaunch with dialogs open; not reproduced.
- **Driving the UI from adb:** give a dialog 3 to 5 s before sending keys, and take a
  screenshot per step.  Two "bugs" in this round were keys sent too early.

## Autoroute tool docked, fixes and manual (10.99al, 2026-11-10)
KiCad patch 0039; user manual in `docs/AUTOROUTE.md`, with screenshots in `docs/media/autoroute`.
- **Panel and hosts:**
  - The tool is AUTOROUTE_PANEL (pcbnew/autoroute/autoroute_panel.cpp), held by an
    AUTOROUTE_HOST: DIALOG_AUTOROUTE (modal), or DOCKED_AUTOROUTE_HOST.
  - The docked host is an AUI pane, Left layer 5, row 0, position 0, in the Properties column.
    Properties is hidden while the pane shows and comes back on close. PCB_EDIT_FRAME befriends
    both for m_auimgr.
  - AUTOROUTE_PANEL::OpenTool() opens the last-used form. The choice is a file,
    `cache/autoroute/docked`. Dock to Side / Undock toggle it.
  - The dialog form gives its tabs their content's min size; only the Settings tab scrolls.
- **Lock (docked):**
  - From Start until Keep, Discard or New Run, lockEditor() does the following:
    - cancels the interactive tool and clears the selection;
    - disables every other AUI pane, the toolbars included, and the menu bar's tops;
    - pushes event blockers: on the canvas for left/right clicks and keys (wheel and gestures
      still zoom), and on the frame for keys outside the panel.
  - PCB_EDIT_FRAME::CanAcceptApiCommands() and the MCP pcb_move_footprint/pcb_run_drc return busy
    while `AUTOROUTE_PANEL::IsEditorLocked()`.
  - canCloseWindow refuses while locked. Verified: pcb_move_footprint and kicad_api answered busy
    during a docked run, and moving a part worked straight after Keep.
- **Fixes:**
  - Crash (SIGSEGV in DIALOG_AUTOROUTE::clearHighlight from ~EDA_BASE_FRAME): a finished run's
    tool was still open when kicad_open_project switched projects. The panel now leaves a frame
    that IsBeingDeleted alone, and kicad_open_project refuses while any modal dialog is open.
    MCP keep/discard close the tool.
  - kicad_screenshot drew Qt's QMessageBox at its widget position. Android shows it as a native
    AlertDialog centred on the app, so it's now drawn centred.
  - Progress lines with "(N ripped)" weren't parsed, so the counter stuck.
  - The log box stopped after 400 lines: the job keeps a 400-line deque, so the panel now counts
    by GetLogTotal().
  - Freerouting optimize-only runs hit its pre-flight guard "optimizer only runs on completely
    routed boards". Autorouter.java turns `optimizer.enablePreflightGuards` off when routing is off.
  - Labels are wrapped by hand (wrapText): wxStaticText::Wrap() after SetLabel doesn't take on
    wxQt.
- **Not reproduced in 10.99ak** (dropped from known issues):
  - the "Board Changed on Disk" Reload button: it reloaded 1,609 tracks fine with unsaved edits;
  - stale pcb_run_drc after a reload or a revert;
  - DRC markers counting as unsaved edits.
- **Still open:**
  - kicad_screenshot can show stale frame widgets: the docked panel's setup view and ungreyed
    toolbars during a run, while the screen is right. The manual's screenshots are adb screencaps
    cropped to the app window (crop 2800x1536 at y=128 on the tablet).
  - Freerouting's optimize changed little on the boards tried: one segment on its own 2-layer
    result.
- **Manual's example board:** `work/rp2350` (on the tablet as Download/rp2350-autoroute, with a
  scratch copy in Download/rp2350-manual).
  - Fan out U1 and J1, then route everything: about 8 min on the tablet, 43 of 58 nets.
  - After the GND pours refill: 19 of 179 connections left, and 11 starved-thermal DRC errors.
  - The display bus (GPIO14-22 between U1 and J3, as a bus): 17 s, 8 of 9 nets.

## Autoroute tool (10.99ak, 2026-11-10)
The user found Freerouting weak even on easy boards. Route > Autoroute is now a tool for both
routers. KiCad patch 0038, Freerouting patch 0003, `android/router`, `scripts/build-python-android.sh`.
- **KiCadRoutingTools (KRT, github.com/drandyhaas/KiCadRoutingTools, MIT, tag v0.23.9):**
  - It's 200k lines of Python (numpy, scipy, shapely) around a 6.6k-line Rust A* core, so it runs
    unchanged on bundled Python rather than being ported.
  - Survey and benchmarks: memory `autorouter-krt-decision`.
- **Build (`scripts/build-python-android.sh`, about 10 min from scratch, every step skips itself
  when done):**
  - python.org's Python 3.14.10 for Android, with numpy 2.5.4, scipy 1.18.1 and shapely 2.2.0
    cross-built by cibuildwheel (`--platform android`, NDK 27.3, API 29).
  - numpy needs `longdouble_format = 'IEEE_QUAD_LE'` in a meson cross file.
  - scipy: `-D_without-fortran=true` against OpenBLAS 0.3.34 built with C_LAPACK (CMake; the
    Makefile build was refused by the sandbox). It needs API 29 (`clog`/`cpow` are API 26+), and
    patch `patches/python/scipy-0001` drops ducc's thread pinning (no `pthread_*affinity_np` in
    bionic).
  - shapely needs GEOS 3.15.0, built with the NDK.
  - The KRT Rust core needs `-DMI_LOCAL_DYNAMIC_TLS=1 -ftls-model=local-dynamic` for mimalloc, or
    bionic refuses to dlopen it ("TLS symbol ... IE access model").
  - Output: `build/python-android/apk/jni` (libkrtrunner.so plus CPython's renamed libs) and
    `apk/assets/python-router` (145 MB, about 2,350 files). VERSION is a content hash, so an
    unchanged rebuild doesn't re-unpack.
  - The stage also runs from adb: see the script's header.
- **APK (`scripts/build-kicad-apk.sh`):**
  - The jniLibs are copied in after androiddeployqt, so Qt never loads them into KiCad's process.
  - `router.jar` carries RouterService and RouterControl.
  - The manifest gets the service (`android:process=":router"`, foreground, specialUse) and the
    FOREGROUND_SERVICE and POST_NOTIFICATIONS permissions.
  - **aapt drops asset directories whose names start with `_`** by default (numpy/_core,
    `__phello__`), so the script sets `ignoreAssetsPattern` in build.gradle. The APK is about 430 MB.
- **Runtime:**
  - KIPLATFORM::ROUTER_PROCESS (libs/kiplatform/os/android/router_process.cpp) unpacks the assets
    to `files/python-router` on the first run (about 1 min on the tablet).
  - It starts one step at a time via RouterService. The step's work directory gets `pid` and
    `exit`, and output goes to its log.
  - Pause/resume are SIGSTOP/SIGCONT (Process.sendSignal); stop is a kill. Liveness is read from
    `/proc/<pid>/cmdline`, read to EOF because /proc files report a length of 0.
  - Each step is a fresh process; numpy can't be re-initialised.
  - libkrtrunner sets `PyConfig.executable`: python.org's Android build otherwise sends
    stdout/stderr to logcat (`_android_support`, "embedded in an app" means an empty
    sys.executable).
- **The run engine (pcbnew/autoroute/autoroute_job.cpp, AUTOROUTE_JOB and AUTOROUTE_SETTINGS):**
  - **Steps:**
    - Planes: KiCad zones over the board outline, made in C++ for either router.
    - KRT fan-out per part: qfn_fanout, or bga_fanout for BGA/WLCSP names.
    - KRT route.py, or Freerouting.
  - **KRT steps chain board files:**
    - The first exports with SavePcbCopy, which writes in.kicad_pro and in.kicad_dru.
    - Each step's result is imported at once: tracks and vias are diffed by KIID and new zones
      added, all one undo step via APPEND_UNDO.
    - Always passed: `--no-fix-drc-settings --keep-input-copper`; `--escalation off|board|fab`
      from the Rules setting (default board).
  - **Chosen nets:** routed with `KICAD_RIP_PREEXISTING=0 KICAD_FINALIZE_RIP=0
    KICAD_RECONCILE_RIP_ESCALATION=0`. Without them KRT rips any blocking net, fan-out stubs
    included, and routes it in full. All three were needed: one route of 6 nets otherwise rewrote
    +3V3 from 18 to 140 segments. Settings has a "let the router move other nets" opt-in.
  - **"Only between these parts":** PART_FILTER takes the routed nets' pads on other parts off
    their nets while the board is exported (SavePcbCopy or the DSN export), then restores them.
  - **Freerouting:**
    - Options go through Autorouter.setOptions: only these nets, inactive layers,
      route-or-optimize-only, fan-out, passes, via cost.
    - The Freerouting patch adds `Item.onlyNets`, checked where hasIgnoredNets() skips net classes,
      and `StoppableThread.setPaused()`, which blocks threads in their stop checks.
- **UI (pcbnew/dialogs/dialog_autoroute.cpp):**
  - Tabs Route, Fan Out, Planes, Optimize and Settings; the run button's label follows the tab.
  - The run view and results replace the tabs in the same modal dialog, so the board can't be
    edited while a run is active (the frame is disabled, so the IPC API also answers busy). It sits
    at the editor's right edge.
  - The results list unrouted nets; a tap highlights the net and zooms to it.
  - Keep refills zones; Discard is an undo; New Run keeps the result and goes back to the tabs.
  - **`OptOut(this)`:** DIALOG_SHIM's control-state persistence restored the last router and tab
    over MCP's settings. The dialog keeps its own last settings (static).
- **MCP:**
  - `pcb_autoroute` (settings as JSON, see AUTOROUTE_SETTINGS::FromJson; `wait`) opens the tool
    via CallAfter and returns once the run starts.
  - `pcb_autoroute_status` reports the state, steps, progress, log tail and the nets still open.
  - `pcb_autoroute_control` does pause, resume, stop, keep and discard.
  - The old `optimize` argument maps to optimize_after; `max_passes` is ignored.
- **Tested on the tablet (RP2350A copies under Download/, "RP2350A Dev Board ... test"):**
  - Fan out U1, then route everything: 11 min. 31 connections open, matching the Mac; the app's
    DRC finds nothing beyond the unrouted ones.
  - Six GPIO nets between U1 and U5 as a bus: 29 s. Only those nets got copper; J3 untouched.
  - Pause/resume/stop work for both routers. Freerouting stop keeps what was routed (93 of 166),
    and discard undoes it.
  - Freerouting optimize-only of two nets: it left the board intact, but changed nothing either;
    not proven to improve anything yet.
- **Known issues:** see 10.99al above; the wide run view and the 10.99aj bugs listed here are
  fixed there or didn't reproduce.

## Crash fix: tree item data on wxQt (10.99ai)
The user hit a crash on 2026-11-07 (10.99ah) in the PCB editor's Tools > DRC Rule Editor.
- **Stack:** SIGSEGV in `__dynamic_cast`, from RULE_EDITOR_DIALOG_BASE::saveRuleTreeState, from onRuleTreeItemLeftUp (the end of a drag in the rule tree).
- **Cause:** the drag moves each item's data to a new item (SetItemData(new, d); SetItemData(old, nullptr)). The wx docs say SetItemData doesn't free the old data, but wxQt kept the data in a wxSharedPtr per item. The second call therefore deleted d, and the new item pointed at freed memory.
- **Fix:** wx patch 0026 detaches the old data instead of deleting it. Deleting an item still frees its data.
- **Check:** tools/wx-tests/tree_item_data_move.cpp with ASan crashes on the old desktop wxQt and passes with the patch.
- **Symbolizing a tablet crash:**
  1. `adb logcat -d -b crash`.
  2. Find the APK entry holding the frame's offset (python zipfile header_offset; libraries are stored uncompressed).
  3. Run `llvm-addr2line -f -C -i -e build/kicad-android/<dir>/<lib>.so <pc>`.

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
    JMX, virtual threads, java.net.http).  Check every entry: a missing class is only harmless when
    its use is off the routing path or inside a `catch (Throwable)`.  10.99ae missed
    java.io.ObjectInputFilter, which broke routing with optimization on (fixed in 10.99ag by
    patch 0002, which checks the same allowlist in SafeObjectInputStream.resolveClass()).
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
- **Full-board test (10.99ag), work/esp32s3-uno:** an ESP32-S3 Uno board built entirely over MCP
  (schematic, net classes, rules, placement, routing, pours, DRC, Gerbers, 3D render; 465 tool calls,
  log in mcp-log.jsonl.gz).  Things it found, all fixed in 10.99ag:
  - Re-entrancy: KiCad's progress dialogs yield with YieldFor(TIMER), but wxQt's yield processes
    all Qt events, so MCP CallAfter requests ran inside a zone fill or DRC; a DRC nested in a fill
    spun the main thread for good.  RunOnMainThread() now re-posts (100 ms later, from a helper
    thread) while wxEventLoopBase::GetActive()->IsYielding() (patch 0032).  Other CallAfter users
    on wxQt can hit the same thing.
  - pcb_run_drc reinitializes the DRC engine first: SetBoardDesignRules / SetNetClasses /
    SetCustomDesignRules don't, so DRC kept the rules from when the board was opened (patch 0032;
    the GUI DRC dialog still has that problem after API changes, upstream too).
  - Freerouting's SafeObjectInputStream used java.io.ObjectInputFilter (absent on Android), which
    broke routing with optimization (freerouting patch 0002).
  - Route before pouring: a filled GND pour reaches the router as copper over the layer, and it
    routed 84/107 instead of 107/107.  Upstream KiCad behaves the same; worth handling in
    pcb_autoroute (ignore or temporarily unfill pours) later.
  - Project text variables resolve ${KICAD10_3DMODEL_DIR}, so a project can carry its own 3D
    models (SetTextVariables with a DOCTYPE_PROJECT document) while Configure Paths is broken.
  - IPC ProjectSpecifier paths must match exactly, trailing slash included (take them from the
    schematic document in kicad_status).
- Release APKs are `<profileable android:shell="true"/>` (10.99ag), so a stuck process can be
  sampled with `adb shell simpleperf record -p <pid> --call-graph dwarf` (not yet tried).
- Next ideas: sch_* tools (ERC, annotate, update PCB from schematic), a board picture tool
  (RunBoardJobExportPng), Windows support (sockets are POSIX only).
