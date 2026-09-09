# Validation record — 2026-09-09

This records software and numerical evidence, not physical acceptance or a generally validated CAD reconstruction service.

## Automated checks

26 pytest checks passed on macOS arm64 / Python 3.12.14. The suite covers exact 3D uniform tension, bending at two mesh sizes versus a Timoshenko beam, force and moment balance, strain energy, force/stiffness scaling, STEP round trip, connected custom CSG, invalid input/foreign-origin rejection, study persistence, archive hashes, and independently accepted/rejected solution submissions. The mocked numerical submission test is not GPU execution evidence. Two dependency deprecation warnings remain (Starlette HTTPX / AnyIO aliases).

The measured cantilever has approximately 0.98% coarse-mesh and 0.78% fine-mesh tip displacement error against the analytic beam model, and 0.20% mesh-to-mesh change. Predetermined gates are below 5% analytic error and below 2% mesh change. These are displacement checks; they do not validate peak stress convergence at the bracket's sharp corner. Exact values: `evidence/numerical-benchmark.json`.

## Actual local GPU evidence

A real in-app browser run selected its hardware adapter `apple · metal-3`, using the WebGPU sparse compute kernels. On the immutable 3,072-tetrahedron / 16,980-DOF bracket mesh it dispatched 3,560 iterations over three refinement passes. Total recorded solve and postprocessing time: 38.927 s; GPU orchestration time: 37.938 s. Float64 SciPy reference solve: 1.850 s. This small case is slower on the GPU; the feature is local GPU execution, not a demonstrated speedup.

| Gate | Measured | Outcome |
|---|---:|---|
| Full quadratic displacement relative L2 difference < 1e-5 | 1.13e-11 | Pass |
| Peak von Mises relative difference < 1e-4 | 1.34e-11 | Pass |
| Independently recomputed GPU relative residual < 1e-7 | 2.57e-10 | Pass |

Peak stress: 14.65856 MPa. Maximum displacement: 0.1193915 mm. Applied force: [0,0,-100] N on X=80 end face; fully fixed X=0 face; illustrative E=69,000 MPa, nu=0.33. `evidence/gpu-cpu-comparison.json` records IDs, hashes, metrics and device provenance. Run `python -m scripts.compare_gpu RUN_ID` to repeat against a saved GPU run. Device metadata is browser-reported; the backend verifies the displacement independently.

The first GPU attempt exposed a WGSL reserved-name compilation error; this was corrected before the successful run. No CPU fallback was used for the successful GPU result.

## Astra evidence

A real `gpt-6-astra` image request identified the synthetic L bracket and its two bores, declined to infer scale, and asked for overall dimensions, hole locations and hidden details. After exact example dimensions were supplied, a second real request returned a valid structured bracket proposal with explicit synthetic provenance assumptions. These are actual authenticated calls, not canned assistant responses. Evidence: `evidence/astra-image-inspection.json` and `evidence/astra-dimensioned-proposal.json`.

The test reference is a deliberately labelled synthetic CAD render. It is not a customer photograph and does not establish performance on arbitrary real images. General geometry support consists of brackets, plates, shafts, ordered box/cylinder CSG and imported single-solid STEP; arbitrary feature reconstruction is outside this version.

## Interactive and document checks

The real browser exercised image upload, dimension annotation, note editing, undo/redo, face selection, fixed-face application, real GPU simulation and displayed execution metadata. Further final handoff checks are recorded below when complete. The CPU example PDF was rendered and inspected page by page. Reports distinguish unaveraged stress peaks from smoothed viewport colors and preserve model/mesh hashes and analysis assumptions.

## Remaining acceptance work

Actual camera hardware capture, other browsers/GPUs, GPU device-loss recovery, representative customer photos, complex industrial STEP files, very fine meshes and physical part/material acceptance have not been established. Hosted Sites operation is a plan; geometry service, hosted Astra access, user isolation and migrated persistence are not implemented. See `SITES-PUBLISHING-PLAN.md`.
