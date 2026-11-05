# Continue the KiCad Android port

You are picking up the KiCad-on-Android port in this repository.  Read `docs/HANDOVER.md` first
(state, devices, build letters, test setup, rules), then `docs/CHANGES.md` (what exists).

## Standing rules (also in HANDOVER and the agent's memory)

- **Builds:**
  - Kill the emulator before any build (`adb -e emu kill`).
  - Boot it yourself afterwards with `scripts/emulator.sh`.
  - Bump the build letter with `scripts/bump-build.sh` (current: 10.99z; next: aa).
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
2. **P7: import and export third-party symbols, footprints and 3D models.**
   - Test with SnapEDA's ESP32-S31-WROOM-1-N16R16V, including its 3D model.
3. **P8: UI sweep.** Fields too big, too small, or not scaling.  Check at the Fold's 2.625 scale.
   Known so far:
   - The Plot dialog sits under the status bar, and its buttons are clipped.
   - The drill dialog has no background.
   - Panels cover the canvas on the Fold.
   - The soft keyboard covers the focused field.
   - New Project via the Android save picker loses the typed name (`.kicad_pro.kicad_pro`).
4. **P9: other desktop-GL code.**  Find the remaining desktop-OpenGL users and make them work on
   Android:
   - the 3D model preview in footprint properties
   - the raytracer's display pass
   - the OpenGL GAL fallback
   - 3D screenshots
5. **Later:**
   - touch gestures in the 3D viewer
   - long-press as right click
   - downloading 3D models on demand

Start by giving the user a short status summary and asking which item to take, unless they have
already said.
