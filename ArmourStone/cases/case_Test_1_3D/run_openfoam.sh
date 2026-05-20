#!/bin/bash

source /usr/lib/openfoam/openfoam2206/etc/bashrc

set -e

cd /work/cases/case_Test_1_3D

echo "Running blockMesh..."
blockMesh > log.blockMesh 2>&1

echo "Running checkMesh..."
checkMesh > log.checkMesh 2>&1

echo "Running topoSet..."
topoSet > log.topoSet 2>&1

echo "Running simpleFoam..."
simpleFoam > log.simpleFoam 2>&1

echo "Writing cell centres..."
postProcess -func writeCellCentres -latestTime > log.writeCellCentres 2>&1 || true

echo "Creating ParaView file..."
touch case_Test_1_3D.foam

echo "Done."
