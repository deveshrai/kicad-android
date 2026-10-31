#!/usr/bin/env python3
"""
Patch Qt 6.12 for Android's QtWindow.class so window surfaces are always TextureViews.

QtWindow.lambda$createSurface$7(int useTextureView, boolean onTop, int depth, boolean opaque)
starts with   iload_1 ; ifne +24   choosing QtTextureView over QtSurface (a SurfaceView).
Even with QT_ANDROID_SURFACE_CONTAINER_TYPE=TextureView the native side requests a SurfaceView
for Vulkan windows, which then sits behind the activity window where KiCad's other frames
cover it.  A TextureView is composited in the view hierarchy, and its SurfaceTexture-backed
Surface works for Vulkan too.  Replacing iload_1 with iconst_1 (same length) always takes the
TextureView branch.

Usage: patch_qtwindow.py <QtWindow.class in> <QtWindow.class out>
"""
import sys

ILOAD_1, ICONST_1, IFNE = 0x1B, 0x04, 0x9A
pattern = bytes([ILOAD_1, IFNE, 0x00, 0x18])

data = open(sys.argv[1], "rb").read()

if data.count(pattern) != 1:
    sys.exit("QtWindow.class: surface container branch not found exactly once (Qt version changed?)")

data = data.replace(pattern, bytes([ICONST_1, IFNE, 0x00, 0x18]))
open(sys.argv[2], "wb").write(data)
