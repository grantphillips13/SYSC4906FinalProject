cmake_minimum_required(VERSION 3.16)

set(projectName "flood_sim")

project(${projectName})
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/bin)

add_subdirectory(main)
