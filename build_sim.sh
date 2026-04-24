#!/bin/bash

export CADMIUM="$PWD/../cadmium_v2/include"

echo "CADMIUM = $CADMIUM"

if [ ! -f "$CADMIUM/cadmium/modeling/celldevs/grid/coupled.hpp" ]; then
    echo "Could not find coupled.hpp at:"
    echo "$CADMIUM/cadmium/modeling/celldevs/grid/coupled.hpp"
    exit 1
fi

# Clean up previous build directory and old simulation logs
if [ -d "build" ]; then rm -Rf build; fi
rm -f *.csv

# Create a fresh build directory
mkdir -p build
cd build || exit

# Clean the build folder just in case
rm -rf *

# Configure the project using CMake
cmake ..

# Compile the executables
make

# Return to the root project folder
cd ..
echo "Compilation done. Executable is located in the bin/ folder."
echo "Run a scenario with: ./bin/flood_sim config/<scenario>.json"