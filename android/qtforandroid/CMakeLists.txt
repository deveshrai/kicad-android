# Rebuilds Qt's Android platform plugin (qtforandroid) from toolchain/qtbase-src (branch
# kicad-android, Qt 6.12.0 + our patches) against the installed Qt, so the APK can ship it in
# place of the prebuilt one.  See scripts/build-qtforandroid.sh.
cmake_minimum_required(VERSION 3.22)
project(qtforandroid LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_AUTOMOC ON)
find_package(Qt6 REQUIRED COMPONENTS Core Gui CorePrivate GuiPrivate)

set(S "${QTBASE_SRC}/src/plugins/platforms/android")
file(GLOB SRCS "${S}/*.cpp")
list(REMOVE_ITEM SRCS "${S}/extract-dummy.cpp")

add_library(qtforandroid MODULE ${SRCS})
set_target_properties(qtforandroid PROPERTIES
    OUTPUT_NAME plugins_platforms_qtforandroid_${ANDROID_ABI}
    CXX_VISIBILITY_PRESET hidden)
target_compile_definitions(qtforandroid PRIVATE QT_PLUGIN
    VK_USE_PLATFORM_ANDROID_KHR)
target_include_directories(qtforandroid PRIVATE "${S}" "${QTBASE_SRC}/src/3rdparty/android")
target_link_libraries(qtforandroid PRIVATE Qt6::Core Qt6::CorePrivate Qt6::Gui Qt6::GuiPrivate
    EGL android jnigraphics log)
