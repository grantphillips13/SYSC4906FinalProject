#!/bin/bash

export CADMIUM="$PWD/../cadmium_v2/include"

echo "CADMIUM = $CADMIUM"

if [ ! -f "$CADMIUM/cadmium/modeling/celldevs/grid/coupled.hpp" ]; then
    echo "Could not find coupled.hpp at:"
    echo "$CADMIUM/cadmium/modeling/celldevs/grid/coupled.hpp"
    exit 1
fi

if [ -d "build" ]; then rm -Rf build; fi
mkdir -p build
cd build || exit
rm -rf *
cmake ..
make
cd ..
echo "Compilation done. Executable in the bin folder"