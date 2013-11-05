INCLUDE(FindPkgConfig)
PKG_CHECK_MODULES(PC_MAC mac)

FIND_PATH(
    MAC_INCLUDE_DIRS
    NAMES mac/api.h
    HINTS $ENV{MAC_DIR}/include
        ${PC_MAC_INCLUDEDIR}
    PATHS ${CMAKE_INSTALL_PREEFIX}/include
          /usr/local/include
          /usr/include
)

FIND_LIBRARY(
    MAC_LIBRARIES
    NAMES gnuradio-mac
    HINTS $ENV{MAC_DIR}/lib
        ${PC_MAC_LIBDIR}
    PATHS ${CMAKE_INSTALL_PREFIX}/lib
          ${CMAKE_INSTALL_PREFIX}/lib64
          /usr/local/lib
          /usr/local/lib64
          /usr/lib
          /usr/lib64
)

INCLUDE(FindPackageHandleStandardArgs)
FIND_PACKAGE_HANDLE_STANDARD_ARGS(MAC DEFAULT_MSG MAC_LIBRARIES MAC_INCLUDE_DIRS)
MARK_AS_ADVANCED(MAC_LIBRARIES MAC_INCLUDE_DIRS)

