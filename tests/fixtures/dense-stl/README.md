# Dense STL corpus inputs

These three gzip files retain the frozen synthetic CAD surfaces used by the axial import validation in `evidence/import-validation.json`: a tube, a 2 mm open channel, and an asymmetric two-bore plate. `manifest.json` includes the original specifications, raw STL SHA-256 hashes and CAD reference responses. They contain no customer geometry.

`python -m scripts.validate_dense_stl` verifies those hashes, subdivides each triangle uniformly until the source exceeds 80,000 triangles, writes actual binary STL bytes, and exercises the production upload/review/meshing path. Subdivision preserves the original piecewise-planar surface; it does not add finer CAD curvature. The check then compares selected sections, topology, measured surface samples, volume, and CPU/P2 axial response. This is not a dense freeform/industrial corpus, global surface certificate, stress-convergence study or physical calibration.
