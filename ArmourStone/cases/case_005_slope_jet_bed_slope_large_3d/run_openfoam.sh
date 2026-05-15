#!/bin/bash

source /usr/lib/openfoam/openfoam2206/etc/bashrc

set -e

cd /work/cases/case_005_slope_jet_bed_slope_large_3d

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
touch case_005_slope_jet_bed_slope_large_3d.foam

echo "Done."
