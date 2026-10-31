# Android build of ngspice as libngspice.so, which KiCad loads at run time.
#
# Same source revision as KiCad's registry port. XSPICE code models are not built yet:
# they need the cmpp preprocessor built for and run on the host during the build, which
# ngspice's autotools build does not support when cross-compiling.
# TODO(android): build a host cmpp first, then enable --enable-xspice and the .cm models.

vcpkg_check_linkage(ONLY_DYNAMIC_LIBRARY)

vcpkg_from_git(
    OUT_SOURCE_PATH SOURCE_PATH
    URL https://git.code.sf.net/p/ngspice/ngspice
    REF ebdaf58ec76a06ffaac7e0f138360dd1cf5ee4b6
)

# Android has pthreads in libc and no libpthread, so AC_CHECK_LIB fails and ngspice falls
# back to Win32 locking.  Search libc first and define HAVE_LIBPTHREAD when found.
vcpkg_replace_string("${SOURCE_PATH}/configure.ac"
    "AC_CHECK_LIB([pthread], [pthread_create])"
    "AC_SEARCH_LIBS([pthread_create], [pthread], [AC_DEFINE([HAVE_LIBPTHREAD], [1], [Define if pthreads are available])])")

vcpkg_find_acquire_program(BISON)
get_filename_component(BISON_DIR "${BISON}" DIRECTORY)
vcpkg_add_to_path(PREPEND "${BISON_DIR}")

vcpkg_make_configure(
    SOURCE_PATH "${SOURCE_PATH}"
    AUTORECONF
    OPTIONS
        --with-ngshared
        --enable-cider
        --disable-xspice
        --disable-openmp
        --disable-debug
        --without-x
        --without-readline
        --without-editline
)

vcpkg_make_install()

file(REMOVE_RECURSE
    "${CURRENT_PACKAGES_DIR}/share/ngspice/scripts/spinit.in"
    "${CURRENT_PACKAGES_DIR}/debug/share"
    "${CURRENT_PACKAGES_DIR}/debug/include")

vcpkg_install_copyright(FILE_LIST "${SOURCE_PATH}/COPYING")
