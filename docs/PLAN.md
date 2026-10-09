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

Latest local maintenance verification: **116 backend tests**, **17 frontend tests**, and the production build passed on October 9, 2026. See [VALIDATION.md](VALIDATION.md#repository-maintenance-verification--2026-10-09) for the checked source, environment, warnings and continuity notes. The [GitHub CI workflow](https://github.com/77kmp9jr2f-jpg/openFEA/actions/workflows/ci.yml) reports remote Linux results separately; it contains no deployment step.

## Outstanding requested scope

### Integration repair and next workflow pass (2026-09-20)

- [x] Correct arbitrary-angle stiffness rotation; synchronize job cancellation; align the 500,000-DOF GPU contract; disclose comparison context changes. Regression tests reproduce the reviewed defects.
- [x] Remove automatic P1 downgrade. Oversized quadratic systems request a coarser mesh until a separately reviewed interpolation option has numerical evidence.
- [x] Install Linux Gmsh GLU dependency in CI. Check the GitHub Actions run for the exact pushed commit to establish remote Linux verification.
- [x] Preserve original/working STL provenance, reject empty STEP downloads, retain preprocessing warnings and require review of altered geometry.
- [x] Require real-part setup confirmation; add operation-specific cancellation through the WebGPU loop.
- [x] Bind print settings to Astra interview/proposals and restore pinned comparisons; show print axes alongside the model.
- [x] Run numerical/API/build checks and the real browser conversation/GPU/save/report path, review the integration, commit and merge into local main. Source `1a6e8d7`, research `087abcb`, evidence `5bfa601`; the merge preserves that verified tree without conflicts.
- [x] Complete the image-to-mesh research assessment and the first known-CAD import/refinement corpus: tube, open channel and perforated plate through CAD, STEP and STL. All 15 CPU/P2 cases and 94 predefined gates pass; this is axial validation with two mesh levels, not general convergence or physical calibration.
- [x] Gate readiness using actual quadratic DOFs, preserve browser autosave through startup outages, restore studies atomically and provide a retry after readiness failures. Browser recovery checks and the dense historical-model capacity gate passed.
- [x] Repair STL meshing after partial surface parameterization; extend numerical evidence with channel bending and tube torsion at three CAD levels plus frozen STL imports. All eight cases and 38 response/refinement/equilibrium gates pass; initial failures are retained.
- [x] Replace bounding-box print fractions with actual layer-contour perimeter/skin/core accounting. Compare three synthetic inputs with OrcaSlicer deposition; preserve historical reproduction and disclose method changes. Verify actual GPU/CPU parity, report reproduction and saved comparison reload. Stiffness remains globally homogenized and uncalibrated.
- [x] Repair dense/source topology and winding checks; replace coarse vertex welding with guarded reduction. All three redundant dense-STL fixtures (tube, channel, two-bore plate) pass 69 geometry, review, meshing and axial-response checks under declared surface/volume budgets. Preserve initial failures and require re-upload of historically welded sources before new meshing.
- [x] Bound pending GPU acquisition, compilation and readbacks by cancellation, device loss and a deadline; release late devices and allow explicit retry. Verify real hardware cancellation/retry and a 157,239-DOF plate against the retained CPU solution. Retain the separate poor-quality tube convergence failure.
- [x] Repair short edges left by count-targeted STL reduction, bound cleanup movement and reject reversed surface triangles. Re-uploading the failed tube improves minimum mesh quality 117-fold; its 82,491-DOF actual GPU solve now matches CPU. Preserve the established lossless cleanup and all 69 dense-corpus gates; retain failed alternatives as evidence.
- [x] Extend print-usage comparison across orientation, one/three/five walls, 20/60% infill and two nozzle/layer profiles. Retain 27 measured cases and three slicer rejections, verify settings/placement/artifact hashes, and clarify part-only usage and printability limits in preview/reports. No empirical correction or stiffness calibration is adopted.
- [x] Preserve the full conversation in new analysis snapshots and reports, including questions and review cards. Keep Astra's recent context separately bounded to ten messages with those fields included. Verify a 38-message browser conversation through live Astra, actual GPU solve, saved-study reload and executed archive reproduction; historical truncated runs remain unchanged.
- [x] Keep annotation history within the restored study, freeze reference edits during builds/solves, and prevent delayed startup/example loads or comparison responses from replacing a newer study's state. Reproduce the failures, verify six controlled lifecycle probes and real browser editing/build/restore behavior, and preserve the original completed study.
- [x] Assess the preserved 1.44-million-triangle original STL in isolated storage. Retain the production count rejection and three alternative surface-fidelity failures; improve actionable import diagnostics without loosening limits or adopting a failed reducer. See [ORIGINAL-STL-VALIDATION.md](ORIGINAL-STL-VALIDATION.md).
- [x] Diagnose the three oblique slicer rejections and measure separate support-enabled variants. Preserve model/support mass separation, add advisory first-layer footprint guidance to preview/new reports, verify actual archive reproduction and browser display, and confirm unchanged stiffness/usage on independent controls.
- [x] Verify the 157,239-DOF plate in Chrome on the same Apple GPU; compare all solution DOFs against CPU and the in-app browser, retain saved-study reload, and execute the exported large-plate CPU reproduction. Reject and document two independent Blender reduction configurations for the original STL without changing acceptance limits.
- [x] Give Astra the saved run's print method, settings and usage separately from current draft controls; correct obsolete bounding-box guidance. Verify three context regressions and two live replies distinguishing historical box estimates from current contours. Reject two fixed PyMeshLab reductions of the original STL under the unchanged surface gate.

- First coupon analysis on CPU with trust guidance: shipped on `print-stl-workspace` (`56f0faa`). See [MAKING-FEA-COMMON.md](MAKING-FEA-COMMON.md).
- Own-part + agent path: machine-readable readiness, documented `/api/agent` contract, residual/confirm gates, same guidance and hashes. See [AGENT.md](AGENT.md).
- Conversational print workflow verified on September 20: live missing-input interview, complete print proposal, preview/apply/confirm, actual Apple WebGPU, CPU parity, archive reproduction and saved comparison reload. Final automated checks: 76 backend tests and five frontend regressions passed; TypeScript/Vite production build passed. See [VALIDATION.md](VALIDATION.md).
- Evaluate current image-generation/image-to-3D tools for sketch-to-mesh against known CAD examples. The separate research task completed as commit `50914d8`: optional concept visualization is useful to trial; production image-to-3D integration is deferred pending a known-CAD benchmark. See [IMAGE-TO-3D-RESEARCH.md](IMAGE-TO-3D-RESEARCH.md). Generated geometry still requires dimensions, topology inspection and comparison to ground truth.
- Broader reliability: additional GPUs, camera hardware, and larger industrial STLs.
- Keep ChatGPT Sites publishing at the planning stage. Push and deployment require explicit user authorization.

## Next acceptance items

1. Enable supported ingestion of the assessed original 1.44-million-triangle part via source CAD or a feature-preserving reduction; its current rejection is retained, not bypassed. Two Blender configurations fail count or surface checks, and two topology/normal-preserving PyMeshLab configurations also exceed the surface budget. Original CAD/STEP is the preferred next input; other settings/methods remain unassessed. Broaden original/freeform tessellations and independent tiny-fillet/bore ground truth. The three frozen CAD surfaces with redundant subdivision pass explicit budgets and axial checks; this does not certify unsampled geometry or self-intersections, and retained facets limit boundary refinement. General stress convergence remains unproven.
2. Extend the [30-case slicer matrix and three supported oblique cases](SLICER-MATRIX.md) to other printer families, wall generators, infill patterns and broader support-aware toolpaths. The initial 27 measured cases differ by -14.37% to +7.09%, and orientation rankings can disagree; the three original oblique rejections remain retained alongside the separate supported measurements. Physical mass and stiffness coupons across orientations remain necessary. Keep nominal bead-envelope limits, globally homogenized stiffness and illustrative pattern factors explicit; spatial wall/infill mechanics need separate validation before adoption.
3. Exercise another GPU hardware family and physical driver loss. Chrome and the in-app browser now agree on the same Apple GPU, and the large-plate export has been reproduced on CPU. Mocked loss/deadline tests and real Apple GPU cancellation/retry pass. The 157,239-DOF plate and freshly reduced 82,491-DOF tube match CPU; the historical 84,324-DOF tube failure remains unchanged. Further conditioning/mesh guidance is needed for arbitrary inputs. The 500,000-DOF request contract is covered; a real solve at that limit is not established.
4. Execute the proposed image-to-3D benchmark on known CAD after selecting providers and an explicit spending budget. The research report is complete; no assets or paid trials were generated.
5. Check updated Linux CI for each authorized push and resolve any failures. Keep Sites hosting in planning until service isolation, hosted authentication and persistence are implemented and separately approved for release.
