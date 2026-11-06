# Sources of the Android build

The APK is built from the upstream projects below at the listed revisions, with the patch
series in `patches/` applied on top, by the scripts in `scripts/`.  Together with this
repository, these make up the complete corresponding source of the published binaries.

| Component | Upstream | Revision | Our changes | Licence |
|---|---|---|---|---|
| KiCad | https://gitlab.com/kicad/code/kicad (mirror: github.com/KiCad/kicad-source-mirror) | `113c71d59d19b2d92775118d8f38393227af6de4` (master, 2026-10-30) | `patches/kicad/*.patch` | GPL-3.0-or-later |
| wxWidgets (wxQt port) | https://github.com/wxWidgets/wxWidgets | `73d90e3fd20f92c7b5c7cf04cc1e0567913e53ce` (master, 2026-10-30) | `patches/wxwidgets/*.patch` | wxWindows Library Licence 3.1 |
| Qt | https://www.qt.io (binary SDK 6.12.0 for Android arm64 and macOS host) | 6.12.0 | the Android platform plugin is rebuilt from qtbase with `patches/qtbase/*.patch`; `scripts/patch-qtgui.sh` NOPs one `QImage::detach()` call in `libQt6Gui` | LGPL-3.0 |
| qtbase (plugin sources) | https://github.com/qt/qtbase | `025bdad181de241e81bf853c8a2d7bf3d19261a9` (v6.12.0 line) | `patches/qtbase/*.patch` | LGPL-3.0 |
| gl4es | https://github.com/ptitSeb/gl4es | `bc4314d8369f169d3fa81c5ed1b46b3dba4e74a5` | none (built unmodified by `scripts/build-gl4es.sh`) | MIT |
| vcpkg ports (boost, cairo, curl, OpenCASCADE, ngspice, protobuf, ...) | https://github.com/microsoft/vcpkg and https://gitlab.com/kicad/packaging/kicad-vcpkg-registry | baselines in `deps/vcpkg-configuration.json` | overlay ports and the Android triplet in `deps/` | each port's own licence |
| mimalloc (operator new/delete shim, `android/kimalloc`) | https://github.com/microsoft/mimalloc | v3.5.3 release tarball (SHA-512 pinned in `scripts/build-kimalloc.sh`) | none; the shim is `android/kimalloc/kimalloc.cpp` | MIT |
| Freerouting (integrated autorouter) | https://github.com/freerouting/freerouting | `b647a2f824cfbc54bc4dcaee71b03b7cd945eb76` (tag v2.5.0) | `patches/freerouting/*.patch`; only the routing core is built (no GUI, web API or CLI), with the driver in `android/autorouter/java` | GPL-3.0 |
| Gson (inside the autorouter jar) | https://github.com/google/gson | 2.14.0 (taken from the Freerouting 2.5.0 release jar) | none | Apache-2.0 |
| KiCad symbol/footprint/template libraries | https://gitlab.com/kicad/libraries | tag `10.0.8` (`scripts/fetch-kicad-libs.sh`) | none | CC-BY-SA-4.0 with the KiCad library exception |

Build order: `scripts/build-deps.sh`, `scripts/build-wxqt-android.sh`, `scripts/build-qtforandroid.sh`,
`scripts/build-gl4es.sh`, `scripts/build-autorouter.sh`, `scripts/build-kicad-android.sh`, `scripts/build-kicad-apk.sh`.
See `docs/HANDOVER.md` for the toolchain (NDK r29, SDK, JDK) and details.

To recreate the patched trees, clone each upstream at the revision above and apply its series in
order with `git am patches/<component>/*.patch`.
