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

## Implemented locally

- STL import with scale, watertightness, shell and defect checks; selectable surface patches via `classifySurfaces`.
- Homogenized print model (orientation, walls, skins, infill) that changes stiffness, mass, results and reports. Not a slicer. Not coupon-calibrated. See [PRINT-STL.md](PRINT-STL.md).
- Pin-and-compare table for two print configs; job cancel; CI, CONTRIBUTING, example coupon; product name OpenFEA.

## Outstanding requested scope

### Integration repair and next workflow pass (2026-09-20)

- [x] Correct arbitrary-angle stiffness rotation; synchronize job cancellation; align the 500,000-DOF GPU contract; disclose comparison context changes. Regression tests reproduce the reviewed defects.
- [x] Remove automatic P1 downgrade. Oversized quadratic systems request a coarser mesh until a separately reviewed interpolation option has numerical evidence.
- [x] Install Linux Gmsh GLU dependency in CI. A fresh remote run remains pending an authorized push.
- [x] Preserve original/working STL provenance, reject empty STEP downloads, retain preprocessing warnings and require review of altered geometry.
- [x] Require real-part setup confirmation; add operation-specific cancellation through the WebGPU loop.
- [x] Bind print settings to Astra interview/proposals and restore pinned comparisons; show print axes alongside the model.
- [x] Run numerical/API/build checks and the real browser conversation/GPU/save/report path, review the integration, commit and merge into local main. Source `1a6e8d7`, research `087abcb`, evidence `5bfa601`; the merge preserves that verified tree without conflicts.
- [ ] Continue image-to-mesh research and geometry/convergence/calibration work. Physical specimen validation and hosted Sites release remain outside current software acceptance.

- First coupon analysis on CPU with trust guidance: shipped on `print-stl-workspace` (`56f0faa`). See [MAKING-FEA-COMMON.md](MAKING-FEA-COMMON.md).
- Own-part + agent path: machine-readable readiness, documented `/api/agent` contract, residual/confirm gates, same guidance and hashes. See [AGENT.md](AGENT.md).
- Conversational print workflow verified on September 20: live missing-input interview, complete print proposal, preview/apply/confirm, actual Apple WebGPU, CPU parity, archive reproduction and saved comparison reload. Final automated checks: 76 backend tests and five frontend regressions passed; TypeScript/Vite production build passed. See [VALIDATION.md](VALIDATION.md).
- Evaluate current image-generation/image-to-3D tools for sketch-to-mesh against known CAD examples. The separate research task completed as commit `50914d8`: optional concept visualization is useful to trial; production image-to-3D integration is deferred pending a known-CAD benchmark. See [IMAGE-TO-3D-RESEARCH.md](IMAGE-TO-3D-RESEARCH.md). Generated geometry still requires dimensions, topology inspection and comparison to ground truth.
- Broader reliability: additional GPUs, camera hardware, and larger industrial STLs.
- Keep ChatGPT Sites publishing at the planning stage. Push and deployment require explicit user authorization.

## Next acceptance items

1. Add representative thin-wall, curved and complex STL/STEP fixtures with geometry and displacement convergence evidence. Preserve an explicit accuracy budget when preprocessing alters a surface.
2. Compare equivalent-solid mass with slicer filament usage, then calibrate stiffness against measured printed coupons in multiple orientations. Keep illustrative pattern factors labelled until that evidence exists.
3. Exercise another GPU/browser, device loss and larger quadratic systems. The 500,000-DOF request contract is covered; a real solve at that limit is not established.
4. Execute the proposed image-to-3D benchmark on known CAD after selecting providers and an explicit spending budget. The research report is complete; no assets or paid trials were generated.
5. Run updated Linux CI after an explicitly authorized push. Keep Sites hosting in planning until service isolation, hosted authentication and persistence are implemented and separately approved for release.
