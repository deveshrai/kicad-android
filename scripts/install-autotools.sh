#!/usr/bin/env bash
# Builds GNU autotools into toolchain/autotools (no Homebrew/sudo needed).
# Required by vcpkg ports that run autoreconf (libbacktrace, and others).
set -euo pipefail
source "$(dirname "$0")/env.sh"

PREFIX="$KA_TOOLCHAIN/autotools"
WORK="$KA_TOOLCHAIN/autotools-src"
mkdir -p "$PREFIX" "$WORK"
export PATH="$PREFIX/bin:$PATH"

build() { # name version ext [url-base]
    local n="$1" v="$2" ext="${3:-tar.gz}" base="${4:-https://ftpmirror.gnu.org/$1}"
    [ -f "$WORK/.done-$n-$v" ] && return
    cd "$WORK"
    curl -fsSLO "$base/$n-$v.$ext"
    tar xf "$n-$v.$ext"
    cd "$n-$v"
    ./configure --prefix="$PREFIX" -q
    make -s -j"$(sysctl -n hw.ncpu)"
    make -s install
    touch "$WORK/.done-$n-$v"
}

build m4 1.4.20 tar.xz
build autoconf 2.72 tar.xz
build automake 1.18.1 tar.xz
build libtool 2.5.4 tar.xz
build autoconf-archive 2024.10.16 tar.xz
build pkgconf 2.3.0 tar.xz https://distfiles.ariadne.space/pkgconf
ln -sf pkgconf "$PREFIX/bin/pkg-config"

# vcpkg looks for `libtoolize`; GNU libtool installs it under that name.
ls "$PREFIX/bin"
