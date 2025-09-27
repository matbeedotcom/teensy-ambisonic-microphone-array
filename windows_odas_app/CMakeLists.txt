cmake_minimum_required(VERSION 3.16)
project(TetrahedralMicArray VERSION 1.0.0 LANGUAGES C)

# Set C standard
set(CMAKE_C_STANDARD 99)
set(CMAKE_C_STANDARD_REQUIRED ON)

# Windows-specific settings
if(WIN32)
    add_definitions(-D_WINDOWS -DWIN32)
    set(CMAKE_WINDOWS_EXPORT_ALL_SYMBOLS ON)
endif()

# Set output directories
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin)
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib)

# Set ODAS library paths
set(ODAS_MAIN_LIBRARY "${CMAKE_SOURCE_DIR}/../odas/build-mingw/libodas.dll.a")
set(ODAS_OBJECTS_LIBRARY "${CMAKE_SOURCE_DIR}/../odas/build-mingw/CMakeFiles/odas.dir/objects.a")

if(NOT EXISTS ${ODAS_MAIN_LIBRARY})
    message(FATAL_ERROR "ODAS main library not found at ${ODAS_MAIN_LIBRARY}. Please build ODAS first.")
else()
    message(STATUS "Found ODAS main library: ${ODAS_MAIN_LIBRARY}")
endif()

if(NOT EXISTS ${ODAS_OBJECTS_LIBRARY})
    message(FATAL_ERROR "ODAS objects library not found at ${ODAS_OBJECTS_LIBRARY}. Please build ODAS first.")
else()
    message(STATUS "Found ODAS objects library: ${ODAS_OBJECTS_LIBRARY}")
endif()

# Windows/Cross-compilation defines (matching ODAS build)
if(CMAKE_SYSTEM_NAME STREQUAL "Windows" OR CMAKE_CROSSCOMPILING)
    add_definitions(-D_WINDOWS -DWIN32)
    # For cross-compilation, avoid including Linux system headers
    include_directories(BEFORE SYSTEM)
endif()

# Include ODAS headers
include_directories(
    ${CMAKE_SOURCE_DIR}/../odas/include
    ${CMAKE_SOURCE_DIR}/../odas/include/odas
    ${CMAKE_SOURCE_DIR}/include
)


# Add FFTW include directories (from our MinGW build)
include_directories(${CMAKE_SOURCE_DIR}/../odas/fftw-mingw-build/install/include)

# Add source files
set(SOURCES
    src/main.c
    src/audio_capture.c
    src/doa_processing.c
    src/array_geometry.c
    src/wasapi_guids.c
)

# Create executable
add_executable(tetrahedral_mic_array ${SOURCES})

# Link libraries
target_link_libraries(tetrahedral_mic_array
    ${ODAS_MAIN_LIBRARY}
    ${ODAS_OBJECTS_LIBRARY}
    ${CMAKE_SOURCE_DIR}/../odas/fftw-mingw-build/install/lib/libfftw3f.dll.a
    winmm     # Windows Multimedia API for audio
    winpthread # Windows pthread implementation
    ole32      # COM library for WASAPI
    uuid       # GUIDs for WASAPI
    mmdevapi   # Windows Multimedia Device API for WASAPI
    ksuser     # Kernel streaming user-mode API
    strmiids   # DirectShow IIDs (includes audio IIDs)
)

# Add FFTW library directory
target_link_directories(tetrahedral_mic_array PRIVATE
    ${CMAKE_SOURCE_DIR}/../odas/fftw-mingw-build/install/lib
)

# Copy configuration files to output directory
file(COPY config/ DESTINATION ${CMAKE_BINARY_DIR}/bin/config)

# Install target
install(TARGETS tetrahedral_mic_array DESTINATION bin)
install(DIRECTORY config/ DESTINATION config)