#!/bin/bash
# Build Python 3.14 for Android with numpy, scipy and shapely, plus KiCadRoutingTools and its
# Rust core, into build/python-android/stage. The stage is what the app (or `adb shell`) runs:
#
#   stage/krtpython        launcher: runs like `python3 ...` (Py_BytesMain)
#   stage/lib              libpython3.14.so and its libraries
#   stage/home/lib/python3.14   the standard library (PYTHONHOME=stage/home)
#   stage/site             numpy, scipy, shapely (PYTHONPATH=stage/site)
#   stage/krt              KiCadRoutingTools, with rust_router/grid_router.so for Android
#
# Run on the tablet (feasibility test):
#   cd stage/krt && LD_LIBRARY_PATH=../lib PYTHONHOME=../home PYTHONPATH=../site \
#     ../krtpython py_router/route.py in.kicad_pcb out.kicad_pcb
#
# Every step skips itself when its output exists; delete the output to redo it.
set -euo pipefail
source "$(dirname "$0")/env.sh"

PY_VER=3.14.10
NUMPY_VER=2.5.4
SCIPY_VER=1.18.1
SHAPELY_VER=2.2.0
GEOS_VER=3.15.0
OPENBLAS_VER=0.3.34
KRT_TAG=v0.23.9
# cibuildwheel picks its own NDK (27.x) for the Python ABI; GEOS and OpenBLAS use the same one.
NDK_PY="$ANDROID_HOME/ndk/27.3.13750724"
API=29

W="$KA_ROOT/build/python-android"
SRC="$W/src"; PFX="$W/prefix"; WHL="$W/wheels"; STAGE="$W/stage"
TC="$NDK_PY/toolchains/llvm/prebuilt/darwin-x86_64/bin"
CMAKE="$KA_TOOLCHAIN/venv/bin/cmake"; NINJA="$KA_TOOLCHAIN/venv/bin/ninja"
mkdir -p "$SRC" "$PFX" "$WHL"

# Host tools: cibuildwheel (cross-builds wheels against python.org's Android Python).
if [ ! -x "$W/venv/bin/cibuildwheel" ]; then
  python3 -m venv "$W/venv"
  "$W/venv/bin/pip" -q install cibuildwheel
fi

fetch() {  # url file
  [ -f "$SRC/$2" ] || curl -fsSL -o "$SRC/$2" "$1"
}
fetch "https://www.python.org/ftp/python/$PY_VER/python-$PY_VER-aarch64-linux-android.tar.gz" python-android.tar.gz
fetch "https://download.osgeo.org/geos/geos-$GEOS_VER.tar.bz2" geos.tar.bz2
fetch "https://github.com/OpenMathLib/OpenBLAS/releases/download/v$OPENBLAS_VER/OpenBLAS-$OPENBLAS_VER.tar.gz" openblas.tar.gz
for p in numpy:$NUMPY_VER scipy:$SCIPY_VER shapely:$SHAPELY_VER; do
  n=${p%%:*}; v=${p#*:}
  if [ ! -f "$SRC/$n-$v.tar.gz" ]; then
    url=$(curl -fsSL "https://pypi.org/pypi/$n/$v/json" | python3 -c \
      "import json,sys; print([u['url'] for u in json.load(sys.stdin)['urls'] if u['packagetype']=='sdist'][0])")
    curl -fsSL -o "$SRC/$n-$v.tar.gz" "$url"
  fi
done

[ -d "$SRC/python" ] || { mkdir -p "$SRC/python"; tar xzf "$SRC/python-android.tar.gz" -C "$SRC/python"; }

# GEOS (for shapely) and OpenBLAS with its C LAPACK (for scipy; no Fortran compiler needed).
android_cmake() {  # src build extra-args...
  local s=$1 b=$2; shift 2
  "$CMAKE" -S "$s" -B "$b" -G Ninja -DCMAKE_MAKE_PROGRAM="$NINJA" \
    -DCMAKE_TOOLCHAIN_FILE="$NDK_PY/build/cmake/android.toolchain.cmake" \
    -DANDROID_ABI=arm64-v8a -DANDROID_PLATFORM=24 -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_SHARED_LINKER_FLAGS="-Wl,-z,max-page-size=16384" -DCMAKE_INSTALL_PREFIX="$PFX" "$@" > "$b.log" 2>&1
  "$CMAKE" --build "$b" -j"$(sysctl -n hw.ncpu)" >> "$b.log" 2>&1
  "$CMAKE" --install "$b" >> "$b.log" 2>&1
}
if [ ! -f "$PFX/lib/libgeos_c.so" ]; then
  tar xjf "$SRC/geos.tar.bz2" -C "$SRC"
  android_cmake "$SRC/geos-$GEOS_VER" "$W/geos-build" -DANDROID_STL=c++_shared -DBUILD_TESTING=OFF \
    -DBUILD_BENCHMARKS=OFF -DBUILD_GEOSOP=OFF -DBUILD_DOCUMENTATION=OFF
fi
if [ ! -f "$PFX/lib/libopenblas.so" ]; then
  tar xzf "$SRC/openblas.tar.gz" -C "$SRC"
  android_cmake "$SRC/OpenBLAS-$OPENBLAS_VER" "$W/openblas-build" -DTARGET=ARMV8 -DNOFORTRAN=1 -DC_LAPACK=ON \
    -DBUILD_SHARED_LIBS=ON -DBUILD_STATIC_LIBS=OFF -DBUILD_TESTING=OFF -DUSE_OPENMP=0 -DNUM_THREADS=8
fi

# Wheels. numpy's meson can't run its long-double probe when cross-compiling, so give the answer.
printf "[properties]\nlongdouble_format = 'IEEE_QUAD_LE'\n" > "$W/android-props.ini"
wheel() {  # name version config-settings
  local n=$1 v=$2 cfg=$3
  ls "$WHL"/$n-$v-*.whl > /dev/null 2>&1 && return
  rm -rf "$SRC/$n-$v"; tar xzf "$SRC/$n-$v.tar.gz" -C "$SRC"
  for p in "$KA_ROOT"/patches/python/$n-*.patch; do
    [ -f "$p" ] && patch -s -d "$SRC/$n-$v" -p1 < "$p"
  done
  CIBW_BUILD=cp314-android_arm64_v8a CIBW_TEST_SKIP='*' CIBW_BUILD_FRONTEND=build CIBW_BEFORE_BUILD='' \
  CIBW_ENVIRONMENT="ANDROID_API_LEVEL=$API PIP_FIND_LINKS=$WHL PKG_CONFIG_PATH=$PFX/lib/pkgconfig LDFLAGS=-L$PFX/lib" \
  CIBW_CONFIG_SETTINGS="$cfg setup-args=--cross-file=$W/android-props.ini build-dir=build" \
  PATH="$HOME/.local/bin:$PATH" \
    "$W/venv/bin/cibuildwheel" --platform android --output-dir "$WHL" "$SRC/$n-$v" > "$W/$n-build.log" 2>&1
}
wheel numpy "$NUMPY_VER" "setup-args=-Dallow-noblas=true"
wheel shapely "$SHAPELY_VER" "setup-args=-Dpkg_config_path=$PFX/lib/pkgconfig"
wheel scipy "$SCIPY_VER" "setup-args=-D_without-fortran=true setup-args=-Dblas=openblas setup-args=-Dlapack=openblas setup-args=-Duse-pythran=false setup-args=-Dpkg_config_path=$PFX/lib/pkgconfig"

# KiCadRoutingTools and its Rust core. mimalloc must use local-dynamic TLS, or Android's linker
# refuses to dlopen the module ("TLS symbol ... using IE access model").
if [ ! -d "$SRC/krt" ]; then
  git clone -q --depth 1 --branch "$KRT_TAG" https://github.com/drandyhaas/KiCadRoutingTools.git "$SRC/krt"
fi
KRT_SO="$SRC/krt/rust_router/target/aarch64-linux-android/release/libgrid_router.so"
if [ ! -f "$KRT_SO" ]; then
  (cd "$SRC/krt/rust_router" && \
   PYO3_CROSS_LIB_DIR="$SRC/python/prefix/lib" PYO3_CROSS_PYTHON_VERSION=3.14 \
   RUSTFLAGS="-C link-arg=-Wl,-z,max-page-size=16384" \
   CC_aarch64_linux_android="$TC/aarch64-linux-android$API-clang" AR_aarch64_linux_android="$TC/llvm-ar" \
   CFLAGS_aarch64_linux_android="-DMI_LOCAL_DYNAMIC_TLS=1 -ftls-model=local-dynamic" \
   CARGO_TARGET_AARCH64_LINUX_ANDROID_LINKER="$TC/aarch64-linux-android$API-clang" \
   cargo build -q --release --target aarch64-linux-android)
fi

# Launcher.
LAUNCHER="$W/krtpython"
if [ ! -f "$LAUNCHER" ]; then
  printf '#include <Python.h>\nint main(int argc, char** argv) { return Py_BytesMain(argc, argv); }\n' > "$W/krtpython.c"
  "$TC/aarch64-linux-android$API-clang" -O2 -fPIE -pie -I"$SRC/python/prefix/include/python3.14" "$W/krtpython.c" \
    -L"$SRC/python/prefix/lib" -lpython3.14 -Wl,-z,max-page-size=16384 -o "$LAUNCHER"
fi

# Stage: stripped, without test suites.
rm -rf "$STAGE"; mkdir -p "$STAGE/lib" "$STAGE/home/lib" "$STAGE/site" "$STAGE/krt"
cp -a "$SRC/python/prefix/lib/"*.so* "$STAGE/lib/"
cp -a "$SRC/python/prefix/lib/python3.14" "$STAGE/home/lib/"
rm -rf "$STAGE/home/lib/python3.14/test" "$STAGE/home/lib/python3.14/idlelib" "$STAGE/home/lib/python3.14/tkinter" \
       "$STAGE/home/lib/python3.14/turtledemo" "$STAGE/home/lib/python3.14/ensurepip"
for w in "$WHL"/*.whl; do unzip -q -o "$w" -d "$STAGE/site"; done
find "$STAGE/site" -type d -name tests -prune -exec rm -rf {} +
rsync -a --exclude .git --exclude tests --exclude 'rust_router/target' --exclude docs --exclude movie3d \
  --exclude kicad_files --exclude __pycache__ "$SRC/krt/" "$STAGE/krt/"
rm -f "$STAGE/krt/rust_router/grid_router.so"
cp "$KRT_SO" "$STAGE/krt/rust_router/grid_router.so"
cp "$LAUNCHER" "$STAGE/krtpython"
find "$STAGE" -name "*.so" -type f -exec "$TC/llvm-strip" --strip-unneeded {} \;
"$TC/llvm-strip" "$STAGE/krtpython"
du -sh "$STAGE"

# ---- APK pieces (used by scripts/build-kicad-apk.sh) ----
# jni/: the router process's native libraries, packaged as jniLibs: libkrtrunner.so (RouterService's
# JNI side, android/router/jni) and CPython's own libraries, which keep their _python names so
# they never clash with KiCad's OpenSSL or SQLite.
APKW="$W/apk"
rm -rf "$APKW"; mkdir -p "$APKW/jni" "$APKW/assets/python-router"
"$TC/aarch64-linux-android$API-clang" -O2 -shared -fPIC -I"$SRC/python/prefix/include/python3.14" \
  "$KA_ROOT/android/router/jni/krtrunner.c" -L"$SRC/python/prefix/lib" -lpython3.14 \
  -Wl,-z,max-page-size=16384 -o "$APKW/jni/libkrtrunner.so"
for l in libpython3.14.so libssl_python.so libcrypto_python.so libsqlite3_python.so; do
  cp "$STAGE/lib/$l" "$APKW/jni/"
done
"$TC/llvm-strip" --strip-unneeded "$APKW/jni/"*.so

# assets/python-router/: everything else, extracted on first use like kicad-data (FILES.txt lists
# the files, VERSION triggers re-extraction, a ".kad" suffix keeps aapt from touching them).
A="$APKW/assets/python-router"
( cd "$STAGE" && tar cf - home site krt ) | ( cd "$A" && tar xf - )
( cd "$A" && find home site krt -type f | sort > FILES.txt )
find "$A/home" "$A/site" "$A/krt" -type f -exec sh -c 'for f; do mv "$f" "$f.kad"; done' _ {} +
# The stamp is a hash of the contents, so a rebuild that changes nothing does not re-unpack.
HASH="$( cd "$A" && find home site krt -type f | sort | xargs shasum | shasum | cut -c1-16 )"
echo "py$PY_VER-numpy$NUMPY_VER-scipy$SCIPY_VER-shapely$SHAPELY_VER-krt$KRT_TAG-$HASH" > "$A/VERSION"
du -sh "$APKW/jni" "$A"
