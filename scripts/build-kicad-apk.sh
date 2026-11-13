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

# operator new/delete on mimalloc; must load before libc++_shared (see android/kimalloc)
"$KA_ROOT/scripts/build-kimalloc.sh"
stage "$KA_ROOT/build/kimalloc/libkimalloc.so"; EXTRA+=("$LIBSTAGE/libkimalloc.so")

for f in "$KA_ROOT"/build/install/android/lib/libwx_*.so "$KA_ROOT"/deps/vcpkg_installed/arm64-android/lib/*.so; do
    stage "$f"; EXTRA+=("$LIBSTAGE/$(basename "$f")")
done

# gl4es (scripts/build-gl4es.sh): desktop GL 2.1 for the 3D viewer, dlopen()ed by glad
[ -f "$KA_ROOT/build/install/android/lib/libGL.so" ] || "$KA_ROOT/scripts/build-gl4es.sh"
stage "$KA_ROOT/build/install/android/lib/libGL.so"; EXTRA+=("$LIBSTAGE/libGL.so")

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

# Official symbol/footprint/template libraries, as their own asset tree with a fixed version so
# app updates do not re-extract them (KICAD_BUNDLE_LIBS=0 to leave them out).  The 3D models are
# not bundled; the setup wizard's Library Files page downloads them, and can update these
# libraries to a newer release (common/startwizard/startwizard_provider_library_files.cpp).
if [ "${KICAD_BUNDLE_LIBS:-1}" != 0 ]; then
    LIBS_SRC="$("$KA_ROOT/scripts/fetch-kicad-libs.sh" | tail -1)"
    mkdir -p "$OUT/assets/kicad-libs"
    ( cd "$LIBS_SRC" && find symbols footprints template -type f | sort > "$OUT/assets/kicad-libs/FILES.txt" )
    ( cd "$LIBS_SRC" && tar cf - symbols footprints template ) | ( cd "$OUT/assets/kicad-libs" && tar xf - )
    find "$OUT/assets/kicad-libs/symbols" "$OUT/assets/kicad-libs/footprints" \
         "$OUT/assets/kicad-libs/template" -type f -exec sh -c 'for f; do mv "$f" "$f.kad"; done' _ {} +
    cp "$LIBS_SRC/VERSION" "$OUT/assets/kicad-libs/VERSION"
fi
# KiCadRoutingTools and the Python it runs on (scripts/build-python-android.sh): the Python files
# as an asset tree extracted on first use, the native side as jniLibs (added after androiddeployqt,
# so Qt never loads them into KiCad's process; only the ":router" process does)
PYRT="$KA_ROOT/build/python-android/apk"
[ -f "$PYRT/jni/libkrtrunner.so" ] || "$KA_ROOT/scripts/build-python-android.sh"
cp -R "$PYRT/assets/python-router" "$OUT/assets/python-router"

# Qt binary patch: no full backing-store image copy per widget flush (scripts/patch-qtgui.sh)
"$KA_ROOT/scripts/patch-qtgui.sh"
QPLUG="$QT_ANDROID_PATH/plugins"

# Build lettering on top of the upstream version: 10.99a, 10.99b, ... (android/BUILD_LETTER)
LETTER="$(tr -d '[:space:]' < "$KA_ROOT/android/BUILD_LETTER")"
KVER_MAJOR="$(sed -n 's/.*KICAD_MAJOR_VERSION *"\([0-9]*\)".*/\1/p' "$BUILD/kicad_build_version.h")"
KVER_MINOR="$(sed -n 's/.*KICAD_MINOR_VERSION *"\([0-9]*\)".*/\1/p' "$BUILD/kicad_build_version.h")"
VERSION_NAME="${KVER_MAJOR}.${KVER_MINOR}${LETTER}"
# letters count up (a=1, b=2, ...); the upstream version scales it so a new upstream base sorts later
# Letter index: a..z = 1..26, aa..zz = 27..702 (three digits, so codes keep rising past z)
L1=$(( $(printf '%d' "'${LETTER:0:1}") - 96 ))
if [ ${#LETTER} -eq 1 ]; then LIDX=$L1; else LIDX=$(( L1 * 26 + $(printf '%d' "'${LETTER:1:1}") - 96 )); fi
VERSION_CODE=$(( (KVER_MAJOR * 100 + KVER_MINOR) * 1000 + LIDX ))
echo "APK version $VERSION_NAME ($VERSION_CODE)"

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
   "android-package-name": "$KA_APP_ID",
   "android-version-name": "$VERSION_NAME",
   "android-version-code": "$VERSION_CODE",
   "android-package-source-directory": "$KA_ROOT/android/package",
   "android-app-name": "$KA_APP_LABEL",
   "android-min-sdk-version": "$KA_ANDROID_API",
   "android-target-sdk-version": "35",
   "android-legacy-packaging": false,
   "android-deploy-plugins": "$QPLUG/styles/libplugins_styles_qandroidstyle_${ABI}.so;$QPLUG/platforms/libplugins_platforms_qtforandroid_${ABI}.so;$QPLUG/imageformats/libplugins_imageformats_qgif_${ABI}.so;$QPLUG/imageformats/libplugins_imageformats_qico_${ABI}.so;$QPLUG/imageformats/libplugins_imageformats_qjpeg_${ABI}.so;$QPLUG/iconengines/libplugins_iconengines_qsvgicon_${ABI}.so;$QPLUG/imageformats/libplugins_imageformats_qsvg_${ABI}.so",
   "permissions": [ { "name": "android.permission.INTERNET" },
                    { "name": "android.permission.MANAGE_EXTERNAL_STORAGE" },
                    { "name": "android.permission.READ_EXTERNAL_STORAGE" },
                    { "name": "android.permission.WRITE_EXTERNAL_STORAGE" } ],
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
    --android-platform "android-37.0" --gradle --${KICAD_APK_MODE:-debug} --jdk "$JAVA_HOME"

# Patch Qt's main-loop thread to start with a large stack (android/qt-patches/...QtThread.java;
# KiCad carves tool coroutine stacks out of it), then rebuild the package with the patched jar.
# Qt's loader loads qt_libs in order; kimalloc has to come before c++_shared so every later
# library (libc++_shared included) binds operator new/delete to it
LIBSXML="$OUT/res/values/libs.xml"
grep -q "$ABI;kimalloc</item>" "$LIBSXML"
perl -0pi -e "s|(<array name=\"qt_libs\">\s*)|\1<item>$ABI;kimalloc</item>\n        |" "$LIBSXML"
grep -A2 '<array name="qt_libs">' "$LIBSXML" | grep -q "$ABI;kimalloc"

# Legacy storage permissions only apply below Android 11/13; newer ones use MANAGE_EXTERNAL_STORAGE
perl -pi -e 's|(android:name="android.permission.READ_EXTERNAL_STORAGE")|$1 android:maxSdkVersion="32"|; s|(android:name="android.permission.WRITE_EXTERNAL_STORAGE")|$1 android:maxSdkVersion="29"|' "$OUT/AndroidManifest.xml"

# App icon (resources come from android/package/res; see android/icon for the sources)
grep -q 'android:icon=' "$OUT/AndroidManifest.xml" || \
    perl -0pi -e 's|(<application\b)|$1 android:icon="\@mipmap/ic_launcher"|' "$OUT/AndroidManifest.xml"
grep -q 'android:icon="@mipmap/ic_launcher"' "$OUT/AndroidManifest.xml"

# Profileable from the shell: simpleperf can sample a stuck release build (a hang report needs
# a stack).  It grants no access to the app's data and does not make the app debuggable.
grep -q '<profileable' "$OUT/AndroidManifest.xml" || \
    perl -0pi -e 's|(<application\b[^>]*>)|$1\n        <profileable android:shell="true"/>|' "$OUT/AndroidManifest.xml"
grep -q '<profileable android:shell="true"/>' "$OUT/AndroidManifest.xml"

PATCH_CLASSES="$KA_ROOT/build/qt-patches-classes"
rm -rf "$PATCH_CLASSES" && mkdir -p "$PATCH_CLASSES"
# QtThread: big main-loop stack.  QtMessageDialogHelper: Escape and BACK in message boxes.
# QtWindow: window surfaces as TextureViews, and the frame and title strip of dialogs
"$JAVA_HOME/bin/javac" --release 8 -nowarn -d "$PATCH_CLASSES" \
    -cp "$ANDROID_SDK_ROOT/platforms/android-35/android.jar:$QT_ANDROID_PATH/jar/Qt6Android.jar" \
    "$KA_ROOT"/android/qt-patches/org/qtproject/qt/android/*.java 2>/dev/null
test -f "$PATCH_CLASSES/org/qtproject/qt/android/QtWindow.class"
( cd "$PATCH_CLASSES" && zip -q -d "$OUT/libs/Qt6Android.jar" 'org/qtproject/qt/android/QtThread$*' \
      'org/qtproject/qt/android/QtWindow$*' || true
  zip -q "$OUT/libs/Qt6Android.jar" org/qtproject/qt/android/QtThread*.class org/qtproject/qt/android/QtWindow*.class \
      org/qtproject/qt/android/QtMessageDialogHelper*.class org/qtproject/qt/android/ButtonStruct.class \
      org/qtproject/qt/android/QtNativeDialogHelper.class )
# FileProvider paths (wx patch 18 opens files in other apps through it): androiddeployqt drops app
# resources that Qt's own java dir also has, so build from a copy of that dir with ours swapped in
QT_JAVA="$KA_ROOT/build/qt-android-java"
rm -rf "$QT_JAVA" && cp -R "$QT_ANDROID_PATH/src/android/java" "$QT_JAVA"
cp "$KA_ROOT/android/package/res/xml/qtprovider_paths.xml" "$QT_JAVA/res/xml/qtprovider_paths.xml"
perl -pi -e "s|^qtAndroidDir=.*|qtAndroidDir=$QT_JAVA|" "$OUT/gradle.properties"
grep -q "^qtAndroidDir=$QT_JAVA\$" "$OUT/gradle.properties"

# The router process: RouterService (android:process=":router") runs KiCadRoutingTools' steps,
# a foreground service so a long route survives the app going to the background
cp "$PYRT"/jni/*.so "$OUT/libs/$ABI/"
ROUTER_CLASSES="$KA_ROOT/build/router-classes"
rm -rf "$ROUTER_CLASSES" && mkdir -p "$ROUTER_CLASSES"
"$JAVA_HOME/bin/javac" --release 11 -nowarn -cp "$ANDROID_SDK_ROOT/platforms/android-35/android.jar" \
    -d "$ROUTER_CLASSES" "$KA_ROOT"/android/router/java/io/github/deveshrai/kicadandroid/*.java
( cd "$ROUTER_CLASSES" && rm -f "$OUT/libs/router.jar" && zip -q -r "$OUT/libs/router.jar" io )
grep -q 'FOREGROUND_SERVICE_SPECIAL_USE' "$OUT/AndroidManifest.xml" || \
    perl -0pi -e 's|(<application\b)|<uses-permission android:name="android.permission.FOREGROUND_SERVICE"/>\n    <uses-permission android:name="android.permission.FOREGROUND_SERVICE_SPECIAL_USE"/>\n    <uses-permission android:name="android.permission.POST_NOTIFICATIONS"/>\n    $1|' "$OUT/AndroidManifest.xml"
grep -q 'RouterService' "$OUT/AndroidManifest.xml" || \
    perl -0pi -e 's|(</application>)|    <service android:name="io.github.deveshrai.kicadandroid.RouterService" android:process=":router" android:exported="false" android:foregroundServiceType="specialUse">\n            <property android:name="android.app.PROPERTY_SPECIAL_USE_FGS_SUBTYPE" android:value="Runs the PCB autorouter on a board the user is editing"/>\n        </service>\n    $1|' "$OUT/AndroidManifest.xml"
grep -q 'android:process=":router"' "$OUT/AndroidManifest.xml"
# aapt's default ignore pattern drops asset directories starting with "_" (<dir>_*), which loses
# Python packages such as numpy/_core and the stdlib's __phello__; keep only the VCS/OS exclusions
grep -q 'ignoreAssetsPattern' "$OUT/build.gradle" || \
    perl -0pi -e "s|(aaptOptions \{)|\$1\n        ignoreAssetsPattern '!.svn:!.git:!.ds_store:!*.scc:!CVS:!thumbs.db:!picasa.ini:!*~'|" "$OUT/build.gradle"
grep -q 'ignoreAssetsPattern' "$OUT/build.gradle"

# Integrated autorouter (Freerouting's core plus its driver; scripts/build-autorouter.sh)
[ -f "$KA_ROOT/build/autorouter/autorouter.jar" ] || "$KA_ROOT/scripts/build-autorouter.sh"
cp "$KA_ROOT/build/autorouter/autorouter.jar" "$OUT/libs/autorouter.jar"

GRADLE_TASK=assembleDebug
[ "${KICAD_APK_MODE:-debug}" = release ] && GRADLE_TASK=assembleRelease
( cd "$OUT" && ./gradlew -q "$GRADLE_TASK" )

APK="$(find "$OUT/build/outputs/apk" -name "*.apk" | head -1)"
if [ -n "${KA_RELEASE_KEYSTORE:-}" ]; then
    # Published builds: a release key kept outside the repository.  The password is read from
    # the file next to it (KA_RELEASE_KEYSTORE.pass, one line ending in a newline; the key uses
    # the same password), never from the command line.
    SIGNED="$KA_ROOT/build/${KA_APP_LABEL// /-}-$VERSION_NAME.apk"
    SIGNED="${SIGNED//[()]/}"
    "$ANDROID_HOME/build-tools/35.0.0/apksigner" sign --ks "$KA_RELEASE_KEYSTORE" \
        --ks-pass "file:$KA_RELEASE_KEYSTORE.pass" \
        --out "$SIGNED" "$APK"
else
    SIGNED="$KA_ROOT/build/KiCad-debug.apk"
    "$ANDROID_HOME/build-tools/35.0.0/apksigner" sign --ks "$HOME/.android/debug.keystore" \
        --ks-pass pass:android --key-pass pass:android --out "$SIGNED" "$APK" 2>/dev/null
fi
ls -la "$SIGNED"
