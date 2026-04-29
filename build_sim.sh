#!/bin/bash

set -e

if [ -z "$CADMIUM" ]; then
	export CADMIUM="$PWD/../cadmium_v2/include"
fi

if [ ! -f "$CADMIUM/cadmium/modeling/celldevs/asymm/coupled.hpp" ]; then
	echo "Could not find Cadmium headers at:"
	echo "$CADMIUM"
	exit 1
fi

if [ -d "build" ]; then rm -Rf build; fi
mkdir -p build
cd build || exit
rm -rf *
cmake ..
make
cd ..
echo Compilation done. Executable in the bin folder