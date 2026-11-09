# Continue the KiCad Android port

You are picking up the KiCad-on-Android port in this repository.  Read `docs/HANDOVER.md` first
(state, devices, build letters, test setup, rules), then `docs/CHANGES.md` (what exists).

## Standing rules (also in HANDOVER and the agent's memory)

- **Builds:**
  - Kill the emulator before any build (`adb -e emu kill`).
  - Boot it yourself afterwards with `scripts/emulator.sh`.
  - Bump the build letter with `scripts/bump-build.sh` (current: 10.99aj; next: ak).
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
2. **P7: integrated autorouter. Done in 10.99ae; tune it if the user asks.**
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
   Known so far:
   - The Plot dialog sits under the status bar, and its buttons are clipped.
   - The drill dialog has no background.
   - Panels cover the canvas on the Fold.
   - The soft keyboard covers the focused field.
6. **P11: other desktop-GL code.**  Find the remaining desktop-OpenGL users and make them work on
   Android:
   - the 3D model preview in footprint properties
   - the raytracer's display pass
   - the OpenGL GAL fallback
   - 3D screenshots
7. **Later:**
   - touch gestures in the 3D viewer
   - long-press as right click
   - downloading 3D models on demand (now more pressing: Configure Paths is broken, and the
     ESP32-S3 board needed its models copied in by hand plus a project text variable)

Start by giving the user a short status summary and asking which item to take, unless they have
already said.
