# What we changed to run KiCad on Android

KiCad already builds on Windows, macOS and Linux.  This port adds Android while staying close to
upstream: there are no forks, only patch series against exact upstream revisions (`SOURCES.md`).
This document explains the changes by area.  Each patch has a full commit message with the details.

```
┌──────────────────────────────────────────────────────────────┐
│ KiCad (eeschema, pcbnew, 3D viewer, ...)   patches/kicad     │
├───────────────┬──────────────────────────────┬───────────────┤
│ kiplatform    │ wxWidgets: wxQt port         │ GAL canvas    │
│ port/wxqt     │ patches/wxwidgets            │ Vulkan (RHI)  │
│ os/android    ├──────────────────────────────┤ 3D: GL 2.1 →  │
│               │ Qt 6.12 for Android          │ gl4es → GLES  │
│               │ patches/qtbase + jar patches │               │
├───────────────┴──────────────────────────────┴───────────────┤
│ Android (NDK r29, arm64, API 29+)                            │
└──────────────────────────────────────────────────────────────┘
```

## 1. Toolkit: wxWidgets on Qt

KiCad's whole UI is written against wxWidgets, and wx has no Android port.  Its Qt port (wxQt)
does run on Qt for Android, but it is the least-used wx port, so most of the work was fixing it
(`patches/wxwidgets`, 34 patches):

- **Build:**
  - cross-compiling from macOS (0003, 0005)
  - wxGLCanvas on OpenGL ES (0001, 0004)
  - wxWebView for wxQt (0002)
- **Input:**
  - mouse wheel axis and delta (0006)
  - mouse buttons stuck down after touch (0009)
  - Return/Enter in char events (0015)
  - Escape routed through `wxDialog::Close()` (0016)
  - `wxEVT_CHAR_HOOK`, which wxQt never sent (0032), and the window id in key events (0031)
  - touch events on scrolled windows (0021)
- **Windows and dialogs:**
  - an in-window menu bar (0008)
  - dialogs that keep working while their parent is disabled (0012)
  - status bar layout (0010)
  - combo box sizing (0013)
  - no size grip in dialogs (0028)
  - room for the icons in trees (0030)
  - top-level size hints that leave out the frame, as Qt expects (0034)
  - a frame and a title bar for dialogs, which you drag to move the dialog: Qt's Android plugin
    reports them as the window's frame margins (qtbase 0005), and the replacement `QtWindow`
    class in `android/qt-patches` draws them
- **Android integration:**
  - the system document picker, with files returned as paths (0011, 0023)
  - opening files in other apps through a FileProvider (0018)
  - the default browser (0020)
  - hiding the soft keyboard when focus leaves a text field (0014)
- **Crash fixes:**
  - drawing an invalid bitmap (0007)
  - moving focus in a scroll area (0017)
  - painting when `QPainter::begin()` failed (0022)
  - null pointers in `DoGetPosition()` (0024)
  - tree item data freed twice (0026), and deleted tree items in selection events (0027)
- **Fonts:** Android sizes fonts in pixels, so wx reported a 2 pt size and editors were unreadable
  (0019).
- **Text:** narrow strings are UTF-8 on Android (0029); partial text extents that include
  kerning, so data view cells don't ellipsize text that fits (0033).
- **Files:** `wxFileName::Mkdir()` starts below the deepest existing directory (0025).

## 2. Platform layer: `kiplatform`

KiCad keeps its OS-specific code behind `libs/kiplatform`.  We added:

- **`port/wxqt`:** UI helpers written directly against Qt (kicad 0001):
  - the Vulkan window that sits over each canvas and forwards input to it (0008, 0014)
  - a virtual pointer, because Android apps can't move the mouse pointer (0019)
  - touch-to-mouse injection through Qt's window-system interface (0029)
- **`os/android`:**
  - app paths
  - the environment
  - secrets in the Android Keystore
  - printing
  - JVM access

## 3. App structure and data

- **Libraries:** Android apps are libraries loaded by Java, so `kicad` builds as a shared library.
  The editors (kifaces) are `lib_*.so` files found with `dladdr` (0005).
- **Stock data:** KiCad's stock data (templates, schemas, ...) and the symbol and footprint
  libraries ship as APK assets.  They are unpacked on first start, into versioned trees
  (0005, 0011, 0012).
- **Storage:** projects live in shared Documents, and the app asks once for all-files access (0018).
- **Lock files:** a killed session's lock files are reclaimed on the next start (0021).
- **Coroutine stacks:** KiCad's tool framework runs tools as coroutines.  Their stacks are carved
  out of a larger Qt main-loop thread stack (0006, plus a patched `QtThread` class in
  `android/qt-patches`).
- **Allocator:** `operator new`/`delete` use mimalloc (`android/kimalloc`), which loads before
  `libc++_shared`.
- **Version:** builds are named after their build letter, e.g. 10.99z (0023).

## 4. Drawing: the canvas on Vulkan

KiCad's "Modern" GAL draws through Qt's RHI, which already has a Vulkan backend.  On Android:

- **Surface:**
  - each canvas gets its own Vulkan window, composited as a TextureView so it stacks correctly
    with dialogs and popups (0008, 0014; `android/qt-patches/.../QtWindow.java` replaces `QtWindow`)
  - the window is sized to the canvas viewport (0009)
  - two RHI fixes for surfaces whose size is off by a rounding step, or never reaches the
    requested size (0015, 0017)
  - at a fractional display scale (the Galaxy Tab's 1.75) the shaders get the rounded backing
    size, and even-width grid dots and lines centre on a pixel edge in the supersampled target,
    so the grid is sharp and even (0046)
- **Speed:**
  - pointer motion is coalesced, so the interactive router keeps up with the pointer (0026)
  - a Qt backing store hands its pixels to the compositor directly, instead of copying the whole
    window every frame (qtbase 0002; `scripts/patch-qtgui.sh`)

## 5. The 3D viewer: OpenGL 2.1 on GLES

The 3D viewer uses fixed-function desktop OpenGL, which Android doesn't have.
[gl4es](https://github.com/ptitSeb/gl4es), unmodified, provides it as `libGL.so` on top of the
GLES context of Qt's `QOpenGLWidget`.  KiCad keeps the library loaded, and loads its 3D model
plugins straight from the APK (0027).  Raytracing draws its image as a textured quad, as gl4es's
`glDrawPixels` can't read a pixel buffer (0043).

The board editor exports STEP, GLB and the other 3D formats in-process: an Android app can't run
kicad-cli as a separate program (0043).

## 6. Input on a tablet

- **Mouse and keyboard:**
  - hotkeys
  - presses that arrive without a motion event (0010)
  - zoom about the pointer, since "center and warp cursor" can't move the pointer on Android (0028)
- **Touch on the canvas (0029):**
  - one finger is the left mouse button; its press waits briefly, so a second finger can still
    make the touch a gesture
  - two fingers pan and pinch-zoom
  - a three-finger tap zooms to fit
- **Text handles:** Android's text selection handles are hidden when focus leaves the text field
  (qtbase 0003).
- **Message boxes:** Escape and the BACK key act as the box's Cancel button (a replacement
  `QtMessageDialogHelper` class in `android/qt-patches`).
- **Menus:** showing a window no longer delivers queued input events in the middle of the call,
  which crashed submenus (qtbase 0004).

## 7. KiCad fixes found along the way

These aren't Android specific:

- Footprint filter: also match symbols whose pins are numbered without digits (0022).
- Symbol properties: a datasheet picked in the dialog is embedded into the symbol itself, instead
  of into a throwaway copy (0025).
- Field properties: the value editor is at least one text line high (0024).

## How it was checked

- **Desktop comparison:** Gerber and drill output from the Android build is identical to the
  macOS build of the same sources, apart from the header date and version.  This was checked with
  stored and with refilled zones.
- **Devices:** a Samsung Galaxy Z Fold 8, a Samsung tablet and the Android emulator.  Multi-finger
  gestures were tested with `tools/touchinject`, which injects multi-touch over adb.
