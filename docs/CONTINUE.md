# Continue the KiCad Android port

You are picking up the KiCad-on-Android port in this repository.  Read `docs/HANDOVER.md` first
(state, devices, build letters, test setup, rules), then `docs/CHANGES.md` (what exists).

## Standing rules (also in HANDOVER and the agent's memory)

- **Builds:**
  - Kill the emulator before any build (`adb -e emu kill`).
  - Boot it yourself afterwards with `scripts/emulator.sh`.
  - Bump the build letter with `scripts/bump-build.sh` (current: 10.99ar; next: as).
- **Devices:** ask the user to save before any `adb install` on a physical device.
  - The Fold: `RZGL62ZE1AZ`, screenshots with `scripts/fold-shot.sh`.
  - The tablet: `R5GL8486SDD`.
- **Commits:**
  - KiCad patches carry an `Assisted-by: Claude` trailer.
  - Export patches with `git format-patch` into `patches/<component>/`.
  - Never open merge requests or issues upstream.
- **gl4es:** use it unmodified; adapt on the KiCad/wx side.
- **Multi-touch tests:** `tools/touchinject` (`adb input` is single-touch).
- **Releases:**
  - Development builds use `org.kicad.kicad`.
  - Public releases use `io.github.deveshrai.kicadandroid`, signed with
    `~/.android/kicad-android-release.jks`.
  - Publish to github.com/deveshrai/kicad-android; the recipe is in HANDOVER, "Publishing a release".

## Open work, in the user's priority order

1. **Waiting on the user:**
   - How routing feels (P1).
   - Hands-on checks of the touch gestures (P4) and of the blue text-handle fix (P6).
2. **P7: autorouting.  10.99ak: Route > Autoroute is a tool for KiCadRoutingTools (bundled
   Python) and Freerouting** (see HANDOVER, "Autoroute tool").
   - Follow-ups:
     - 10.99al: docking, the editor lock, fixes, and the manual (docs/AUTOROUTE.md);
     - kicad_screenshot showing stale frame widgets (see HANDOVER 10.99al);
     - via-cost tuning for 2-layer boards (KRT makes B.Cu cost 3x);
     - differential pairs and length matching (KRT's route_diff.py and length matching are
       bundled but not in the UI);
     - presets;
     - check that Freerouting optimize-only improves hand-routed nets;
   - Earlier, 10.99ae: Freerouting inside the app.
   - Route > Autoroute Board... runs Freerouting 2.5.0's core inside the app (see HANDOVER,
     "Integrated autorouter").  The blinker routes in under a second, with DRC clean.
   - Possible follow-ups: route only the selected nets, a passes or time limit, a progress
     notification when the app is in the background.
   - Pour-aware routing: filled pours currently reach the router as copper over the layer (84/107
     routed instead of 107/107 on the ESP32-S3 board); unfill or ignore pours while routing.
3. **P8: integrated MCP server. Done in 10.99af** (Preferences > MCP Server; see HANDOVER).
   - 10.99ag: a whole board designed over MCP (work/esp32s3-uno), with fixes for re-entrant tool
     calls during progress yields and stale DRC rules.
   - 10.99aj: fixes from another agent's schematic session (see HANDOVER, "Agent feedback
     fixes"): document specifiers filled in, editors reload files changed on disk,
     kicad_screenshot, kicad_open_project.
   - Follow-ups: schematic tools (ERC, annotate, update PCB), Windows sockets;
     the GUI DRC dialog still uses stale rules after API rule changes (reinit on API change).
4. **P9: import and export third-party symbols, footprints and 3D models. Done in 10.99ah**
   (File > Import / Export Library Package, plus MCP tools; see HANDOVER).  Tested with SnapEDA's
   ESP32-S31-WROOM-1-N16R16V (download in work/snapeda-esp32-s31, gitignored).
   - Follow-ups: try Ultra Librarian / SamacSys / Digi-Key zips (their layouts differ; the
     importer sorts by extension, so they should work); a "library package" entry in the symbol
     and footprint editors' library context menus; delete a package again.
5. **P10: UI sweep.** Fields too big, too small, or not scaling.  Check at the Fold's 2.625 scale.
   Known so far (10.99an fixed the Plot dialog under the status bar):
   - The drill dialog has no background.
   - Panels cover the canvas on the Fold.
   - The soft keyboard covers the focused field.
6. **P11: other desktop-GL code.**  10.99ap: the raytracer works and 3D image export works
   (see HANDOVER).  Left:
   - the 3D model preview in footprint properties with a real model (none on the tablet)
   - the OpenGL GAL fallback
   - raytracing shows black for blocks not rendered yet
   - files KiCad writes don't reach MediaStore, so other apps' pickers miss them until a scan
7. **Later:**
   - touch gestures in the 3D viewer
   - long-press as right click
   - 3D models are downloadable since 10.99aq (setup wizard > Library Files); Configure Paths
     works since 10.99ar

Start by giving the user a short status summary and asking which item to take, unless they have
already said.

## State after 10.99an (2026-11-13)
10.99an is published: dialogs have a frame and a draggable title bar with a close cross (HANDOVER,
"Dialog frames and Googlebook OS"), dialogs fit between the status bar and the navigation bar or
taskbar, and the README, badges, release notes and repo description say the app is for Android
and Googlebook OS, with a laptop-and-tablet hero (`scripts/make-hero.py`).
- **Not tested on a Googlebook;** the APK is arm64 only.  Say "for Android and Googlebook OS" in
  every published text from now on.
- **Dialog frame follow-ups:** (10.99ar added resizing and kicad_screenshot frames) once, right after launch on the tablet, Preferences showed a black band under its title
  bar that went away when the dialog was moved (a stale first frame?); not seen again.
- **P10 items still open:**
  - (10.99ao fixed the hotkey names, the launcher labels, the layer pair presets and the
    Drawing Sheet Editor's Properties width.)
  - The drill dialog has no background; panels cover the canvas on the Fold; the soft keyboard
    covers the focused field (on the emulator it also opens for grid cell editors with a
    hardware keyboard attached).
- **Open:**
  - A freeze seen once after BACK and relaunch with dialogs open; not reproduced.
- **Tablet:** a stray debug app `org.kicad.kicad` (versionName 10.99am) is installed; uninstalling
  it was denied.  The user said (2026-11-13) they will remove it themselves.  Don't launch it.
