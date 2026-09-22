# Synthetic STL regression fixture

`torque-tube.stl.gz` is an OpenFEA-generated test solid: a 120 mm long tube
along X, outer radius 6 mm and inner radius 4 mm, with a 10 × 20 × 4 mm
loading bar at (110, -10, -2) mm. OpenCASCADE/Gmsh exported the surface at a
requested 4 mm mesh size. It is synthetic project geometry, not an external asset.

The frozen bytes reproduce a Gmsh surface-parameterization failure that leaves
partial geometry behind. The STL import must reload the classified source
before its topology-only fallback; otherwise it generates zero tetrahedra.

Decompressed SHA-256:
`1f51a8109ca1a7c9a7378e745d149ff21fc791dfe53124b27823ff07957e363e`.
The gzip timestamp is zero for deterministic packaging.
