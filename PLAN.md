# KiCad for Android — Port Plan

Target (phase 1): **Android tablets with keyboard + mouse**, arm64-v8a, Android 10+ (API 29).
Touch-first UI is explicitly out of scope until the KBM build is usable.

Upstream: `kicad/` = shallow clone of kicad-source-mirror @ `113c71d5` (2026-10-30), local branch `android`.

## 1. What upstream KiCad looks like today (audit, 2026-10-31)

| Area | State on master | Android impact |
|---|---|---|
| Language/build | C++20, CMake ≥ 3.22, ~2.2M LOC | NDK r29 clang handles it |
| GUI toolkit | wxWidgets 3.2+/3.3 (gtk/msw/osx; CMake already recognises a `qt` port) | **No Android wx port. Critical path.** |
| Canvas | GAL backends: OpenGL, Cairo, **Modern (RHI: Vulkan / Metal)** | Vulkan exists on Android → only need a `VK_KHR_android_surface` path. Cairo = software fallback. |
| 3D viewer | Direct desktop OpenGL + CPU raytracer | Defer; raytracer as fallback |
| Python | Build-time interpreter only (no SWIG/embedded Python any more) | Nothing to port |
| Plugins | IPC API (protobuf + nng) to external processes | Disable initially |
| `kicad-cli` | Links full wx GUI + `gal` | No "headless first" shortcut without wx |
| Fonts | All lookups go through one class, `include/font/fontconfig.h` | Android has no fontconfig → clean seam |
| Platform glue | `libs/kiplatform/{port/wx*, os/*}` | Add `port/wxqt` + `os/android` |
| Web view | `common/widgets/webview_panel.cpp`, PCM, remote symbols | Stub first, Android WebView later |
| Deps | boost, cairo, curl, harfbuzz, freetype, OCCT, ngspice, libgit2, sqlite, icu, nng, protobuf, zstd, glm | All cross-compile; driven by vcpkg `arm64-android` |

## 2. Key decision: the GUI toolkit

**Recommendation: wxWidgets' Qt port (wxQt) on Qt 6 for Android.**

- KiCad has ~1000+ files written against wx (480 in `dialogs/` alone). Rewriting the UI is not realistic; we have to supply a wx backend.
- Qt 6 has mature Android support: activity lifecycle, IME, hardware keyboard/mouse, clipboard, HiDPI, `ANativeWindow` access for Vulkan.
- wxQt exists in wxWidgets master and KiCad's CMake already knows about it. Generic wx code (AUI, PropGrid, STC, RichText, Grid) is port-independent.
- Licensing: Qt LGPLv3 + KiCad GPLv3 is compatible.
- Risk: wxQt is the least-used wx port, and its Android docs are ancient (Qt 5.2, NDK r9). We'll be fixing wxQt bugs, and should upstream them.

Rejected alternatives: writing a native "wxAndroid" port (years of work); a new UI in Rust/Compose/Flutter (rewrites every dialog and tool).

## 3. Where Rust fits

Rust goes at the **platform boundary**, behind C ABIs, where Android differs from desktop and where JNI makes C++ painful. We are not rewriting KiCad core in Rust; it is cross-platform C++ that already builds.

| Component | Why Rust | Seam |
|---|---|---|
| `kiandroid` platform crate (`platform/`) | JNI via `jni` crate, safe lifetimes | `libs/kiplatform/os/android/*.cpp` call `extern "C"` |
| – paths/env | app-private dirs, external storage | `kiplatform/environment.h` |
| – secrets | Android Keystore | `kiplatform/secrets.h` |
| – file access | Storage Access Framework (`content://`) to fd/temp file bridge | file dialogs + `kiplatform/io.h` |
| – open URL / share | Intents | `wxLaunchDefaultBrowser` hooks |
| Font provider | Parse `/system/etc/fonts.xml`, scan `/system/fonts`, user + embedded fonts | replaces `common/font/fontconfig.cpp` under `#ifdef __ANDROID__` |
| Library content manager (later) | Download/update symbol/footprint/3D libraries on demand (GBs, can't ship in APK) | PCM-style |

Bootstrap: fontconfig is cross-compiled via vcpkg initially, so the Rust font provider is a replacement, not a blocker.

## 4. Phases

### Phase 0 — Toolchain & dependencies  ← *in progress*
- [x] Android SDK cmdline-tools, NDK r29 (29.0.14206865), platform 35
- [x] CMake 4.x + Ninja (venv), Rust 1.99 + `aarch64-linux-android`
- [x] vcpkg + `deps/vcpkg.json` (KiCad's manifest minus wx/python/opengl, plus vulkan-headers/fontconfig), custom `arm64-android` triplet (static, API 29)
- [ ] Qt 6.12 (macOS host + android_arm64_v8a) via aqtinstall
- [ ] All vcpkg deps build for arm64-android (expect overlay-port fixes: ngspice, OCCT, libgit2, nng)

### Phase 1 — wxQt on desktop first (fast iteration)
Shake out wxQt problems on macOS with a debugger before going to a device.
- Build wxWidgets master `--with-qt` against desktop Qt 6.
- Build KiCad on macOS against wxQt (Cairo GAL), add `libs/kiplatform/port/wxqt`.
- Fix and log wxQt gaps (patch queue in `patches/wxwidgets/`, upstream when possible).
- Exit: pcbnew + eeschema open, render and edit a demo project on desktop wxQt.

### Phase 2 — Cross-compile for Android
- wxQt for Android (CMake build against Qt for Android, `wxUSE_WEBVIEW=0`, OpenGL off initially).
- KiCad Android CMake toolchain profile: `kiplatform/os/android`, disable 3D OpenGL viewer, IPC API, update check, sentry, spacenav.
- First target: `kicad-cli` binary run via `adb shell` with `QT_QPA_PLATFORM=offscreen`. It validates the whole core (file I/O, DRC/ERC, plotting, fonts) on device.

### Phase 3 — App on device (KBM)
- Gradle/androiddeployqt APK; single process hosting kicad + kifaces (pcbnew/eeschema as `.so` loaded by `KIWAY`, which already works this way).
- Canvas: Cairo GAL first, then Modern GAL via `VK_KHR_android_surface` (`QWindow` to `ANativeWindow`).
- Rust platform crate: paths, SAF file dialogs, fonts, secrets, intents.
- KBM polish: right-click, middle-drag pan, wheel zoom, hotkeys (capture Meta/Esc before Android does), pointer capture.
- Lifecycle: save state on `onStop`, survive config changes, multi-window/freeform.

### Phase 4 — Content & distribution
- Libraries on demand (symbols/footprints/3D), templates, demos.
- Signing, AAB, size budget, crash reporting.

### Phase 5 — Touch (later)
Gesture mapping in GAL tools, larger hit targets, touch-friendly dialogs and toolbars.

## 5. Repo layout

```
KiCadAndroid0/
  PLAN.md
  scripts/env.sh          toolchain paths (source me)
  scripts/build-deps.sh   vcpkg cross-compile of deps
  deps/                   vcpkg manifest, registry config, triplets
  platform/               Rust crate(s): kiandroid
  android/                Gradle project (Phase 3)
  patches/                wxWidgets / KiCad patch queues
  kicad/                  upstream clone, branch `android` (gitignored here)
  toolchain/              downloaded SDKs (gitignored)
```

## 6. Open risks
1. **wxQt maturity**: the biggest unknown. Phase 1 exists to measure it quickly.
2. **OCCT / ngspice** on Android: both build, but may need overlay ports. Can be disabled temporarily (STEP export, simulator).
3. **Vulkan driver quality** on tablets (Mali/Adreno/Xclipse): keep Cairo fallback working.
4. **Library size**: the default libraries are several GB; they need on-demand download.
5. **Upstream churn**: master moves fast; keep Android changes small, behind `__ANDROID__`/`__WXQT__`, rebase often.
