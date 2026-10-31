# wxQt smoke-test APK. Build with scripts/build-wxsmoke.sh.
cmake_minimum_required( VERSION 3.22 )
project( wxsmoke LANGUAGES CXX )

set( CMAKE_CXX_STANDARD 17 )

# wx::wxcore links these Qt modules publicly. TODO: find_dependency() in wxWidgetsConfig.cmake
find_package( Qt6 REQUIRED COMPONENTS Core Gui Widgets OpenGL OpenGLWidgets Test PrintSupport )
find_package( wxWidgets 3.3 REQUIRED CONFIG )

qt_add_executable( wxsmoke smoke.cpp )
target_link_libraries( wxsmoke PRIVATE wx::wxcore wx::wxbase Qt6::Widgets )

# androiddeployqt only bundles Qt's own dependencies; list the wx shared libraries.
file( GLOB WX_SHARED_LIBS "${wxWidgets_DIR}/../../libwx_*.so" )
list( JOIN WX_SHARED_LIBS "," WX_SHARED_LIBS_CSV )

set_target_properties( wxsmoke PROPERTIES
    QT_ANDROID_EXTRA_LIBS "${WX_SHARED_LIBS_CSV}"
    QT_ANDROID_PACKAGE_NAME "org.kicad.wxsmoke"
    QT_ANDROID_APP_NAME "wx smoke"
    QT_ANDROID_MIN_SDK_VERSION 29
    QT_ANDROID_TARGET_SDK_VERSION 35
    )
