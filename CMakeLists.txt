cmake_minimum_required(VERSION 3.16)

project(flood_sim LANGUAGES CXX)

# Final executable goes under bin/
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_SOURCE_DIR}/bin)

# Keep variable style consistent with the modeled project
set(projectName ${PROJECT_NAME})

# Pull in the main/ folder
add_subdirectory(main)
