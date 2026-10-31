# Source this file: `source scripts/env.sh`
# Central definition of every toolchain path used by the Android port.

export KA_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." && pwd)"
export KA_TOOLCHAIN="$KA_ROOT/toolchain"

export JAVA_HOME="/Applications/Android Studio.app/Contents/jbr/Contents/Home"
export ANDROID_HOME="$HOME/Library/Android/sdk"
export ANDROID_SDK_ROOT="$ANDROID_HOME"
export ANDROID_NDK_VERSION="29.0.14206865"
export ANDROID_NDK_HOME="$ANDROID_HOME/ndk/$ANDROID_NDK_VERSION"
export ANDROID_NDK_ROOT="$ANDROID_NDK_HOME"

# Minimum supported Android API level (Android 10). Vulkan 1.1 is mandatory on
# 64-bit devices shipping with this level or newer.
export KA_ANDROID_API=29
export KA_ANDROID_ABI=arm64-v8a

export QT_VERSION="6.12.0"
export QT_HOST_PATH="$KA_TOOLCHAIN/qt/$QT_VERSION/macos"
export QT_ANDROID_PATH="$KA_TOOLCHAIN/qt/$QT_VERSION/android_arm64_v8a"

export VCPKG_ROOT="$KA_TOOLCHAIN/vcpkg"
export VCPKG_DISABLE_METRICS=1

export PATH="$KA_TOOLCHAIN/autotools/bin:$KA_TOOLCHAIN/venv/bin:$HOME/.cargo/bin:$ANDROID_HOME/platform-tools:$VCPKG_ROOT:$PATH"

# vcpkg autotools-based ports need a host pkg-config (built by scripts/install-autotools.sh)
export PKG_CONFIG="$KA_TOOLCHAIN/autotools/bin/pkgconf"
