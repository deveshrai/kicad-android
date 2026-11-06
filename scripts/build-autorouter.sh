#!/bin/bash
# Build the integrated autorouter: Freerouting's routing core (v2.5.0 with patches/freerouting
# applied on branch "android") plus android/autorouter/java, as one jar for the APK.
#
# Output: build/autorouter/autorouter.jar (for androiddeployqt's libs/), and
#         build/autorouter/autorouter.dex (for testing with app_process over adb).
#
# Freerouting needs Java 25 to build.  Android's D8 reads class files up to Java 24, but the
# bytecode did not change between 21 and 25, so the class files are relabelled as Java 21.
# Run scripts/check-autorouter-api.sh after a Freerouting update to find library calls that
# Android does not have.
set -euo pipefail
KA_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
source "$KA_ROOT/scripts/env.sh" >/dev/null

FR_TAG=v2.5.0
FR_SRC="$KA_ROOT/toolchain/freerouting-src"
FR_JAR="$KA_ROOT/toolchain/freerouting/freerouting-2.5.0.jar"   # for gson and annotations
OUT="$KA_ROOT/build/autorouter"
BT="$ANDROID_SDK_ROOT/build-tools/36.0.0"
ANDROID_JAR="$ANDROID_SDK_ROOT/platforms/android-35/android.jar"

if [ ! -d "$FR_SRC/.git" ]; then
    git clone -q --depth 1 --branch "$FR_TAG" https://github.com/freerouting/freerouting.git "$FR_SRC"
fi
if [ "$(git -C "$FR_SRC" rev-parse --abbrev-ref HEAD)" != android ]; then
    git -C "$FR_SRC" switch -q -c android "$FR_TAG" 2>/dev/null || git -C "$FR_SRC" switch -q android
    git -C "$FR_SRC" -c user.name="KiCad Android" -c user.email=build@localhost \
        am -q "$KA_ROOT"/patches/freerouting/*.patch
fi
if [ ! -f "$FR_JAR" ]; then
    mkdir -p "$(dirname "$FR_JAR")"
    curl -fsSL -o "$FR_JAR" \
        "https://github.com/freerouting/freerouting/releases/download/$FR_TAG/freerouting-2.5.0.jar"
fi

rm -rf "$OUT" && mkdir -p "$OUT/src" "$OUT/lib" "$OUT/classes"

# Sources: the router core without its GUI, web API and command line, plus our driver
rsync -a --exclude 'gui/' --exclude 'api/' --exclude 'cli/' \
    --exclude 'Freerouting.java' --exclude 'analytics/BigQueryClient.java' \
    --exclude 'logger/Log4j2ConfigurationFactory.java' --exclude 'startup/LoggingBootstrap.java' \
    "$FR_SRC/src/main/java/" "$OUT/src/"
rsync -a "$KA_ROOT/android/autorouter/java/" "$OUT/src/"
mkdir -p "$OUT/src/app/freerouting/constants"
cat > "$OUT/src/app/freerouting/constants/Constants.java" <<EOF
package app.freerouting.constants;

/** Build metadata constants. */
public final class Constants {
  public static final String FREEROUTING_VERSION = "${FR_TAG#v}";
  public static final String FREEROUTING_BUILD_DATE = "$(git -C "$FR_SRC" log -1 --format=%cs "$FR_TAG")";
}
EOF

# Gson goes into the jar (it is used at run time); the Swagger annotations are only compiled against
( cd "$OUT/lib" && unzip -q -o "$FR_JAR" 'com/google/gson/*' 'io/swagger/v3/oas/annotations/*' )
find "$OUT/src" -name "*.java" > "$OUT/sources.txt"
"$JAVA_HOME/bin/javac" --release 25 -nowarn -encoding UTF-8 -cp "$OUT/lib" -d "$OUT/classes" \
    -sourcepath "$OUT/src" @"$OUT/sources.txt" -XDsuppressNotes 2>&1 | grep -v '^Note:' || true
[ -f "$OUT/classes/io/github/deveshrai/kicadandroid/Autorouter.class" ]
cp -R "$OUT/lib/com" "$OUT/classes/"

python3 - "$OUT/classes" <<'EOF'
import os, sys
for root, _, files in os.walk(sys.argv[1]):
    for f in files:
        if f.endswith('.class'):
            p = os.path.join(root, f)
            b = bytearray(open(p, 'rb').read())
            if (b[6] << 8 | b[7]) > 65:
                b[6], b[7] = 0, 65
                open(p, 'wb').write(b)
EOF

( cd "$OUT/classes" && "$JAVA_HOME/bin/jar" cf "$OUT/autorouter.jar" . )
mkdir -p "$OUT/dex"
"$BT/d8" --release --min-api 29 --lib "$ANDROID_JAR" --output "$OUT/dex" "$OUT/autorouter.jar"
mv "$OUT/dex/classes.dex" "$OUT/autorouter.dex"
ls -la "$OUT/autorouter.jar" "$OUT/autorouter.dex"
