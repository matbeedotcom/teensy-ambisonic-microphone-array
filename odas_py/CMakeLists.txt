cmake_minimum_required(VERSION 3.12)
project(odas_py)

set(CMAKE_CXX_STANDARD 11)

# Save user-provided paths before find_package
set(USER_Python3_INCLUDE_DIRS "${Python3_INCLUDE_DIRS}")
set(USER_Python3_LIBRARIES "${Python3_LIBRARIES}")

# Find Python
find_package(Python3 COMPONENTS Interpreter Development REQUIRED)

# Override with user paths if cross-compiling
if(CMAKE_CROSSCOMPILING AND USER_Python3_INCLUDE_DIRS)
    set(Python3_INCLUDE_DIRS "${USER_Python3_INCLUDE_DIRS}")
    message(STATUS "Overriding Python include (cross-compile): ${Python3_INCLUDE_DIRS}")
endif()
if(CMAKE_CROSSCOMPILING AND USER_Python3_LIBRARIES)
    set(Python3_LIBRARIES "${USER_Python3_LIBRARIES}")
    message(STATUS "Overriding Python library (cross-compile): ${Python3_LIBRARIES}")
endif()

# Find NumPy headers
if(NOT NUMPY_INCLUDE_DIR)
    execute_process(
        COMMAND "${Python3_EXECUTABLE}" -c "import numpy; print(numpy.get_include())"
        OUTPUT_VARIABLE NUMPY_INCLUDE_DIR
        OUTPUT_STRIP_TRAILING_WHITESPACE
    )
endif()

# Convert Windows path to Unix path for cross-compilation
if(CMAKE_CROSSCOMPILING OR (CMAKE_SYSTEM_NAME STREQUAL "Windows" AND CMAKE_HOST_SYSTEM_NAME STREQUAL "Linux"))
    # Convert C:\path to /mnt/c/path for WSL
    string(REPLACE "\\" "/" NUMPY_INCLUDE_DIR "${NUMPY_INCLUDE_DIR}")
    string(REGEX REPLACE "^([A-Za-z]):" "/mnt/\\1" NUMPY_INCLUDE_DIR "${NUMPY_INCLUDE_DIR}")
    string(TOLOWER "${NUMPY_INCLUDE_DIR}" NUMPY_INCLUDE_DIR)
    message(STATUS "Converted NumPy path for cross-compilation: ${NUMPY_INCLUDE_DIR}")
endif()

# Set ODAS paths
set(ODAS_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../odas")
set(ODAS_INCLUDE_DIR "${ODAS_ROOT}/include")
set(ODAS_DEMO_DIR "${ODAS_ROOT}/demo/odaslive")

# Determine build directory and library type - check which one exists
# On Windows, prefer MinGW build; on Linux, prefer native build
if(WIN32 AND EXISTS "${ODAS_ROOT}/build-mingw/libodas.dll.a")
    set(ODAS_BUILD_DIR "${ODAS_ROOT}/build-mingw")
    set(ODAS_LIB_PATH "${ODAS_BUILD_DIR}/libodas.dll.a")
    set(USE_MINGW_BUILD TRUE)
elseif(EXISTS "${ODAS_ROOT}/build/lib/libodas.so")
    set(ODAS_BUILD_DIR "${ODAS_ROOT}/build")
    set(ODAS_LIB_PATH "${ODAS_BUILD_DIR}/lib/libodas.so")
    set(USE_MINGW_BUILD FALSE)
elseif(EXISTS "${ODAS_ROOT}/build/lib/libodas.a")
    set(ODAS_BUILD_DIR "${ODAS_ROOT}/build")
    set(ODAS_LIB_PATH "${ODAS_BUILD_DIR}/lib/libodas.a")
    set(USE_MINGW_BUILD FALSE)
elseif(EXISTS "${ODAS_ROOT}/build/libodas.a")
    set(ODAS_BUILD_DIR "${ODAS_ROOT}/build")
    set(ODAS_LIB_PATH "${ODAS_BUILD_DIR}/libodas.a")
    set(USE_MINGW_BUILD FALSE)
elseif(EXISTS "${ODAS_ROOT}/build-windows/libodas.a")
    set(ODAS_BUILD_DIR "${ODAS_ROOT}/build-windows")
    set(ODAS_LIB_PATH "${ODAS_BUILD_DIR}/libodas.a")
    set(USE_MINGW_BUILD FALSE)
elseif(EXISTS "${ODAS_ROOT}/build-mingw/libodas.dll.a")
    # MinGW as last resort (can only be used when building with MinGW toolchain)
    set(ODAS_BUILD_DIR "${ODAS_ROOT}/build-mingw")
    set(ODAS_LIB_PATH "${ODAS_BUILD_DIR}/libodas.dll.a")
    set(USE_MINGW_BUILD TRUE)
    message(WARNING "Using MinGW ODAS library - this may only work when building with MinGW toolchain")
else()
    message(FATAL_ERROR "ODAS library not found! Please build ODAS first.")
endif()

set(ODAS_LIB_DIR "${ODAS_BUILD_DIR}")
message(STATUS "ODAS Library Path: ${ODAS_LIB_PATH}")

message(STATUS "ODAS Root: ${ODAS_ROOT}")
message(STATUS "ODAS Include: ${ODAS_INCLUDE_DIR}")
message(STATUS "ODAS Library: ${ODAS_LIB_DIR}")
message(STATUS "Python Include: ${Python3_INCLUDE_DIRS}")
message(STATUS "NumPy Include: ${NUMPY_INCLUDE_DIR}")

# Python extension module - NO ODASLIVE DEMO CODE
Python3_add_library(_odas_core MODULE
    src/odas_modules.c
)

target_include_directories(_odas_core PRIVATE
    ${Python3_INCLUDE_DIRS}
    ${NUMPY_INCLUDE_DIR}
    ${ODAS_INCLUDE_DIR}
    ${ODAS_INCLUDE_DIR}/odas
)

# Add fftw3 include path for MinGW builds
if(USE_MINGW_BUILD)
    target_include_directories(_odas_core PRIVATE
        ${ODAS_ROOT}/fftw-mingw-build/install/include
    )
endif()

# No libconfig needed - we're not using odaslive demo code!

# Link ODAS library
target_link_libraries(_odas_core PRIVATE
    ${ODAS_LIB_PATH}
)

# Link Python library - handle cross-compilation
if(CMAKE_CROSSCOMPILING AND WIN32)
    # For cross-compilation, manually specify the Python library
    target_link_libraries(_odas_core PRIVATE
        -L/mnt/c/Users/mail/anaconda3/libs
        -lpython312
    )
else()
    target_link_libraries(_odas_core PRIVATE
        ${Python3_LIBRARIES}
    )
endif()

# Add platform-specific libraries
if(USE_MINGW_BUILD AND WIN32)
    target_link_libraries(_odas_core PRIVATE
        winmm
        wsock32
        ws2_32
    )
endif()

if(UNIX)
    target_link_libraries(_odas_core PRIVATE
        m
        pthread
    )
endif()

# Set output properties
set_target_properties(_odas_core PROPERTIES
    PREFIX ""
    OUTPUT_NAME "_odas_core"
)

if(WIN32)
    set_target_properties(_odas_core PROPERTIES SUFFIX ".pyd")
else()
    set_target_properties(_odas_core PROPERTIES SUFFIX ".so")
endif()