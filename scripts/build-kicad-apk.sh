#!/usr/bin/env bash
# Packages the Android KiCad build (build/kicad-android) into a debug-signed APK with
# androiddeployqt.  The app's entry point is libkicad_<abi>.so (the kicad project manager);
# the kifaces (lib_pcbnew.so, lib_eeschema.so, ...) and all shared deps ship beside it.
set -euo pipefail
source "$(dirname "$0")/env.sh"

BUILD="$KA_ROOT/build/kicad-android"
OUT="$KA_ROOT/build/kicad-apk"
LIBSTAGE="$KA_ROOT/build/kicad-apk-libs"
ABI="$KA_ANDROID_ABI"
STRIP="$ANDROID_NDK_ROOT/toolchains/llvm/prebuilt/darwin-x86_64/bin/llvm-strip"

rm -rf "$OUT" "$LIBSTAGE"
mkdir -p "$OUT/libs/$ABI" "$LIBSTAGE"

# Debug info makes the kifaces several GB; package stripped copies
stage() { cp "$1" "$LIBSTAGE/" && "$STRIP" --strip-debug "$LIBSTAGE/$(basename "$1")"; }

stage "$BUILD/kicad/libkicad_${ABI}.so"
mv "$LIBSTAGE/libkicad_${ABI}.so" "$OUT/libs/$ABI/"

EXTRA=()
while IFS= read -r f; do
    [ "$(basename "$f")" = "libkicad_${ABI}.so" ] && continue
    stage "$f"; EXTRA+=("$LIBSTAGE/$(basename "$f")")
done < <(find "$BUILD" -name "*.so" -not -path "*/CMakeFiles/*")

for f in "$KA_ROOT"/build/install/android/lib/libwx_*.so "$KA_ROOT"/deps/vcpkg_installed/arm64-android/lib/*.so; do
    stage "$f"; EXTRA+=("$LIBSTAGE/$(basename "$f")")
done

EXTRA_CSV="$(IFS=,; echo "${EXTRA[*]}")"

# KiCad stock data as APK assets; kiplatform extracts it on first launch (see
# libs/kiplatform/os/android/environment.cpp).  FILES.txt lists every file because the NDK
# cannot enumerate asset subdirectories; VERSION triggers re-extraction after updates.
SHARE="$KA_ROOT/build/install/kicad-android/usr/local/share/kicad"
rm -rf "$KA_ROOT/build/install/kicad-android"
DESTDIR="$KA_ROOT/build/install/kicad-android" cmake --install "$BUILD" >/dev/null
mkdir -p "$OUT/assets/kicad-data"
cp -R "$SHARE" "$OUT/assets/kicad-data/kicad"
( cd "$OUT/assets/kicad-data" && find kicad -type f | sort > FILES.txt )
# aapt decompresses *.gz assets and drops the extension (images.tar.gz -> images.tar);
# a neutral suffix keeps every file byte-for-byte.  Extraction strips it again.
find "$OUT/assets/kicad-data/kicad" -type f -exec mv {} {}.kad \;
date +%s > "$OUT/assets/kicad-data/VERSION"
QPLUG="$QT_ANDROID_PATH/plugins"

cat > "$OUT/deployment-settings.json" <<EOF
{
   "description": "KiCad for Android",
   "qt": { "$ABI": "$QT_ANDROID_PATH" },
   "qtDataDirectory": { "$ABI": "." },
   "qtLibExecsDirectory": { "$ABI": "libexec" },
   "qtLibsDirectory": { "$ABI": "lib" },
   "qtPluginsDirectory": { "$ABI": "plugins" },
   "qtQmlDirectory": { "$ABI": "qml" },
   "sdk": "$ANDROID_SDK_ROOT",
   "sdkBuildToolsRevision": "36.0.0",
   "ndk": "$ANDROID_NDK_ROOT",
   "toolchain-prefix": "llvm",
   "tool-prefix": "llvm",
   "useLLVM": true,
   "toolchain-version": "clang",
   "ndk-host": "darwin-x86_64",
   "abi": "$ABI",
   "architectures": { "$ABI": "aarch64-linux-android" },
   "android-extra-libs": "$EXTRA_CSV",
   "android-package-name": "org.kicad.kicad",
   "android-app-name": "KiCad",
   "android-min-sdk-version": "$KA_ANDROID_API",
   "android-target-sdk-version": "35",
   "android-legacy-packaging": false,
   "android-deploy-plugins": "$QPLUG/styles/libplugins_styles_qandroidstyle_${ABI}.so;$QPLUG/platforms/libplugins_platforms_qtforandroid_${ABI}.so;$QPLUG/imageformats/libplugins_imageformats_qgif_${ABI}.so;$QPLUG/imageformats/libplugins_imageformats_qico_${ABI}.so;$QPLUG/imageformats/libplugins_imageformats_qjpeg_${ABI}.so;$QPLUG/iconengines/libplugins_iconengines_qsvgicon_${ABI}.so;$QPLUG/imageformats/libplugins_imageformats_qsvg_${ABI}.so",
   "permissions": [ { "name": "android.permission.INTERNET" } ],
   "application-binary": "kicad",
   "qml-skip-import-scanning": true,
   "rcc-binary": "$QT_HOST_PATH/libexec/rcc",
   "extraPrefixDirs": [ "$QT_ANDROID_PATH", "$LIBSTAGE" ],
   "extraLibraryDirs": [ "$LIBSTAGE" ],
   "zstdCompression": false,
   "stdcpp-path": "$ANDROID_NDK_ROOT/toolchains/llvm/prebuilt/darwin-x86_64/sysroot/usr/lib/"
}
EOF

"$QT_HOST_PATH/bin/androiddeployqt" --input "$OUT/deployment-settings.json" --output "$OUT" \
    --android-platform "android-37.0" --gradle --debug --jdk "$JAVA_HOME"

APK="$(find "$OUT/build/outputs/apk" -name "*.apk" | head -1)"
"$ANDROID_HOME/build-tools/35.0.0/apksigner" sign --ks "$HOME/.android/debug.keystore" \
    --ks-pass pass:android --key-pass pass:android --out "$KA_ROOT/build/KiCad-debug.apk" "$APK" 2>/dev/null
ls -la "$KA_ROOT/build/KiCad-debug.apk"
