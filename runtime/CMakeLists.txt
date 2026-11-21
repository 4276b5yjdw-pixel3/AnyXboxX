# Runtime C++ d'AnyXboxX : DLL qui remplacent les bibliothèques de la console.
#
#   cmake -S runtime -B runtime/build -A x64
#   cmake --build runtime/build --config Release
#
# Les DLL sont produites dans runtime/build/bin, où le mode natif les cherche
# (ou dans le dossier donné par la variable ANYXBOXX_RUNTIME).
cmake_minimum_required(VERSION 3.20)
project(AnyXboxXRuntime LANGUAGES CXX)

if(NOT WIN32 OR NOT CMAKE_SIZEOF_VOID_P EQUAL 8)
  message(FATAL_ERROR "Le runtime d'AnyXboxX se compile pour Windows x64 uniquement.")
endif()

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
# Même CRT que Python (ucrtbase) : stderr est partagé avec le journal d'AnyXboxX.
set(CMAKE_MSVC_RUNTIME_LIBRARY "MultiThreadedDLL")
# « $<0:> » évite le sous-dossier Release/Debug des générateurs multi-configurations.
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin/$<0:>")

function(anyxboxx_dll name)
  add_library(${name} SHARED ${ARGN})
  set_target_properties(${name} PROPERTIES PREFIX "" OUTPUT_NAME ${name})
  target_include_directories(${name} PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/common")
  target_compile_definitions(${name} PRIVATE WIN32_LEAN_AND_MEAN NOMINMAX UNICODE _UNICODE)
  target_compile_options(${name} PRIVATE /W4 /WX /permissive- /utf-8)
endfunction()

anyxboxx_dll(xgameruntime xgameruntime/xgameruntime.cpp xgameruntime/xgameruntime.def)
anyxboxx_dll(xmem xmem/xmem.cpp xmem/xmem.def)
anyxboxx_dll(d3d12_xs d3d12_xs/d3d12_xs.cpp d3d12_xs/d3d12_xs.def)
