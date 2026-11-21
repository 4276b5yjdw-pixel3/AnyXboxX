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

# Module Task de libHttpClient (MIT) : XTaskQueue et XAsync, servis par xgameruntime.
set(TASK_DIR "${CMAKE_CURRENT_SOURCE_DIR}/third_party/libhttpclient-task")
add_library(anyxboxx_task STATIC
  ${TASK_DIR}/source/AsyncLib.cpp
  ${TASK_DIR}/source/TaskQueue.cpp
  ${TASK_DIR}/source/ThreadPool_win32.cpp
  ${TASK_DIR}/source/WaitTimer_win32.cpp)
target_include_directories(anyxboxx_task PUBLIC "${TASK_DIR}/include" PRIVATE "${TASK_DIR}/source")
target_compile_definitions(anyxboxx_task PRIVATE WIN32_LEAN_AND_MEAN NOMINMAX)
target_compile_options(anyxboxx_task PRIVATE /W3 /utf-8 /permissive-)

anyxboxx_dll(xgameruntime xgameruntime/xgameruntime.cpp xgameruntime/served_interfaces.cpp
             xgameruntime/task_queue_interface.cpp xgameruntime/user_interface.cpp
             xgameruntime/system_interface.cpp xgameruntime/game_config.cpp
             xgameruntime/registry.cpp xgameruntime/save_store.cpp xgameruntime/save_interface.cpp
             xgameruntime/local_storage_interface.cpp xgameruntime/package_interface.cpp
             xgameruntime/xgameruntime.def)
target_link_libraries(xgameruntime PRIVATE anyxboxx_task)
anyxboxx_dll(xmem xmem/xmem.cpp xmem/xmem.def)
anyxboxx_dll(d3d12_xs d3d12_xs/d3d12_xs.cpp d3d12_xs/d3d12_xs.def)
