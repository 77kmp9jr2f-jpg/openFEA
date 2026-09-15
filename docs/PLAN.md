# OpenFEA working prototype

Build a local, open-source engineering workspace for general 3D mechanical parts. Astra is the named AI assistant and a separately authenticated proprietary service; modelling, meshing, solving and exports also work without it.

Completion gates:
- Image upload/camera capture, persistent arrows, boxes, notes and dimensions.
- A live Astra image/specification conversation with explicit missing questions and a reviewable CAD proposal.
- Parametric brackets, plates and shafts, additive/subtractive box/cylinder recipes, and single-solid STEP import; no promise of arbitrary photo reconstruction.
- Real OpenCASCADE solids and Gmsh tetrahedral meshes, exportable STEP/STL/MSH.
- Select model faces, apply global XYZ forces and fixed supports, choose material, run quadratic 3D linear-elastic FEA.
- Run the actual sparse system on the user’s hardware GPU via WebGPU, independently verify it and provide an explicit CPU reference option.
- Document a concrete ChatGPT Sites publishing path without assuming native Python runs in a Worker.
- Display stress, displacement and exaggerated deformation, plus reaction/residual checks and assumptions.
- Export a reproducible report and documentation bundle; preserve immutable geometry and simulation IDs.
- Verify numerical results against analytic tension and bending cases, test failure gates and browser interaction, inspect current evidence in a saved visual review, commit locally.

Currently implemented analysis scope: one connected solid; small-strain static elasticity; optional transversely isotropic print equivalent. No assemblies/contact, plasticity, buckling, fatigue, transient loads, certified material data, or printed-coupon calibration. Photographic proposals are unmeasured until the user supplies/accepts specifications.

## Shipped on print-stl-workspace

- STL import with scale, watertightness, shell and defect checks; selectable surface patches via `classifySurfaces`.
- Homogenized print model (orientation, walls, skins, infill) that changes stiffness, mass, results and reports. Not a slicer. Not coupon-calibrated. See [PRINT-STL.md](PRINT-STL.md).
- Pin-and-compare table for two print configs; job cancel; CI, CONTRIBUTING, example coupon; product name OpenFEA.

## Outstanding requested scope

- First coupon analysis on CPU with trust guidance: shipped on `print-stl-workspace` (`56f0faa`). See [MAKING-FEA-COMMON.md](MAKING-FEA-COMMON.md).
- Own-part + agent path: machine-readable readiness, documented `/api/agent` contract, residual/confirm gates, same guidance and hashes. See [AGENT.md](AGENT.md).
- Finish browser verification of the conversational proposal through apply, confirmation, GPU solve, saved-study reload and a fresh report/review when Astra is available again.
- Evaluate current image-generation/image-to-3D tools for sketch-to-mesh against known CAD examples (separate research task; still pending).
- Broader reliability: additional GPUs, camera hardware, and larger industrial STLs.
- Keep ChatGPT Sites publishing at the planning stage. Push and deployment require explicit user authorization.
