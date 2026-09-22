# Validation record — updated 2026-09-22

This records software and numerical evidence, not physical acceptance or a generally validated CAD reconstruction service.

## Import and recovery acceptance — 2026-09-22

`python -m scripts.validate_imports` completed 15 CPU/P2 solves and all 94 predetermined gates passed. The independent synthetic dimensions define a 60 mm tube (OD20/ID12), a 60 × 24 × 16 mm open channel with 2 mm walls/floor, and a 60 × 40 × 6 mm plate with two asymmetric bores. Each fixture compares two CAD meshes, one STEP round trip and two remeshes of the same frozen STL. Every end patch receives uniform axial traction sharing a total 100 N; the opposite end is fixed. Material is synthetic isotropic E=210,000 MPa, ν=0. Face coverage, force distribution and retained mesh hashes were independently checked.

| Evidence | Maximum observed | Gate |
|---|---:|---:|
| Prismatic displacement error (tube/channel) | 1.908% | 3% |
| Two-level displacement/energy change | 1.509% | 2% |
| STEP/STL displacement/energy difference from fine CAD | 0.116% | 5% |
| Relative residual | 2.16e-12 | 1e-7 |

`evidence/import-validation.json` records specifications, source hashes, IDs, setup, runtime versions, solve times, volume and every check. The recorded solves total approximately 341 seconds on this machine. Volume gates explicitly refer to the **input solid** (CAD or STL). Tetrahedral volume error is recorded separately; its largest observed value is 1.2355% for the coarse curved tube and is not a post-hoc acceptance gate. The zero-Poisson-ratio axial channel is a linear-field patch test, not evidence of thin-wall bending or freedom from locking. Two mesh levels do not establish asymptotic convergence. The source STLs contain roughly 3,900–4,200 triangles, so these cases do not exercise dense-STL simplification. No stress, anisotropic printing, GPU or physical acceptance is claimed by this corpus.

Readiness now counts the actual quadratic mesh DOFs before enabling Run. Boundary tests cover 500,000/500,001 DOFs and reading historical model metadata without rewriting it. The existing 120,064-tetrahedron dense STL model `4bd01a02f42f441ba22d5b6752b1f2f7` requires 684,333 quadratic DOFs: the API and production browser display the coarser-mesh action and keep Run disabled even after confirmation. Its historical P1 result remains readable; no new solve or geometry mutation was performed.

Browser lifecycle checks used a real local API outage and the development frontend. Before the repair, restarting after an offline reload lost the browser snapshot to default values. After the repair, autosave stays paused until successful initialization, and restarting/reloading restores the original bracket model `f5f0cb3a22034e0f8b67f1b4733b5573`, annotation, live conversation and GPU result `af02566402df43b2b0125ff688188e74`. A deliberately unavailable saved result leaves the current workspace intact; a subsequent width edit survives reload, proving autosave continues. A failed readiness request displays Retry readiness and can recover after the engine returns. These checks reuse saved results and make no new GPU or Astra execution claim.

Current automated verification: 78 backend tests, five frontend regressions and the TypeScript/Vite build pass. The two known dependency deprecation warnings and the existing bundle-size advisory remain. Remote CI, camera hardware, other GPUs, physical coupons and Sites hosting remain outside this local evidence.

## Integration acceptance — 2026-09-20

The print-branch review defects were reproduced with independent tests and repaired. Added checks cover arbitrary-angle strain/stress tensor covariance, the 500,000-DOF submission boundary, no implicit P1 downgrade, queued and running-child cancellation, comparison context differences, preserved STL originals, reloadable preprocessing review, P1/P2 archive reproduction, and complete print-proposal revision/provenance binding. Frontend checks cover independent Astra/solve cancellation, cancellation before a job ID arrives, GPU readback resource cleanup and legacy geometry defaults. All 76 backend tests and five frontend regressions pass. TypeScript/Vite build passes; dependency deprecation and bundle-size advisories remain. CI now installs Gmsh's GLU dependency, but the updated Linux workflow has not run remotely because no new push is authorized.

A fresh browser journey uploaded the synthetic 40 × 10 × 8 mm coupon through **Import STL file**, verified empty supports/loads and unchecked confirmation, built model `9737ceeb435f40c6855ecef6bacf518a`, and asked live Astra for missing inputs. Astra returned questions and no proposal. Explicit demonstration PLA, gyroid/20%, three walls, 0.4 mm line width, 0.2 mm layers, four top/bottom layers, rotation [30,45,20]°, face 9 fixed and total [0,0,-4] N on face 7 produced proposal `ded6df2125624dfb85e07f66aea996e7`. Preview showed support/force markers and rotated print axes before application. Apply left confirmation unchecked. The confirmed real WebGPU run is `4d162ab8d809467ea43bf764c5c8479a`.

- Device: browser-reported `apple · metal-3`; 807 P2 tetrahedra / 4,455 DOFs; 2,320 dispatched iterations / three refinements.
- Server-recomputed relative residual: 5.864917129e-10.
- Maximum displacement: GPU 0.1548826113116278 mm; CPU 0.15488261131261874 mm; relative difference 6.39794e-12.
- Exported ZIP contains original/working STL, transformation metadata, live interview, applied print proposal and solver source. Its reproduction script actually executed in a fresh directory and matched the CPU value.
- Changing only infill to 35% cleared result, confirmation and proposal provenance. A second confirmed GPU run `0eefa5259a6a4a82b01ed3ec4b34b417` yielded 0.1272 mm displacement, 2.075 g and residual 1.57e-9. The comparison identified equal geometry, mesh, material, supports, loads and interpolation. Explicitly saving, reloading the browser, and reopening the saved study restored both comparison runs and conversation.
- The current narrow in-app browser viewport was inspected; labels scale with part dimensions and preview scroll shows the model immediately. Camera hardware, other GPUs, full dense-mesh GPU performance and physical coupon calibration remain unverified.

The four-page GPU PDF was rendered and inspected page by page. Section flow avoids overflow-only pages. Attached reference imagery is labelled as study context; it is not proof of geometry reconstruction. Historical print-warning boilerplate is clarified in presentation without rewriting the immutable result JSON.

Evidence: `evidence/integration-2026-09-20/`. Current [saved visual review](http://127.0.0.1:8850/reviews/?id=514b555beb024e83b7955783e44a31dc), ID `514b555beb024e83b7955783e44a31dc`, binds source `1a6e8d7`; its three rendered frames and revision were inspected. [All reviews](http://127.0.0.1:8850/reviews/). Human review remains open. This is software verification on a known synthetic coupon, not dimensional reconstruction or printed-part strength validation. Historical evidence below remains scoped to its stated revision/date; this pass completes the formerly pending conversational print application/GPU/save/report path.

## Automated checks

54 pytest checks passed on macOS arm64 / Python 3.12 on September 14 after the OpenFEA rename (`d088ce0` on `print-stl-workspace`). The suite covers exact 3D uniform tension, bending at two mesh sizes versus a Timoshenko beam, force and moment balance, strain energy, force/stiffness scaling, STEP round trip, connected custom CSG, STL watertightness and print-stiffness comparison, job cancel, invalid input/foreign-origin rejection, study persistence, archive hashes, independently accepted/rejected solution submissions, and the proposal checks described below. The mocked numerical submission test is not GPU execution evidence. Two dependency deprecation warnings remain (Starlette HTTPX / AnyIO aliases).

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

## STL and print path

Automated: open vs closed STL, reject non-STL, refuse to mesh an open shell, 100% vs sparse homogenization, rotation of the soft axis, selectable faces on an imported box, print solve residual `< 1e-7`, compare deltas, HTTP job cancel. See `tests/test_stl_print.py` and [PRINT-STL.md](PRINT-STL.md).

Browser (built app at `http://127.0.0.1:8000/`, CPU reference solver, example print coupon, 807 quadratic tetrahedra / 4,455 DOFs):

- Gyroid 20%, 3 walls: 54.3% solid equivalent, 2.15 g, 1.11 mm max displacement, residual 1.8e-11.
- Gyroid 60%, 3 walls, same mesh: 77.1%, 3.06 g, 0.821 mm. Compare table showed those deltas plus in-plane / layer moduli.
- Cancel on a finer bracket remesh surfaced `The job was cancelled.`

This is software evidence that print settings change the equivalent solid. It is not printed-coupon calibration and not peak-stress convergence.

## Interactive and document checks

The real browser exercised image upload, dimension annotation, note editing, undo/redo, face selection, fixed-face application, real GPU simulation and displayed execution metadata. Further final handoff checks are recorded below when complete. The CPU example PDF was rendered and inspected page by page. Reports distinguish unaveraged stress peaks from smoothed viewport colors and preserve model/mesh hashes and analysis assumptions.

## Remaining acceptance work

Actual camera hardware capture, other browsers/GPUs, GPU device-loss recovery, representative customer photos, complex industrial STEP files, very fine meshes and physical part/material acceptance have not been established. Hosted Sites operation is a plan; geometry service, hosted Astra access, user isolation and migrated persistence are not implemented. See `SITES-PUBLISHING-PLAN.md`.

## Completed handoff study

The final synthetic reference-to-report journey was exercised in the real browser: a dimension mark was created, labelled and moved to the base; live Astra returned a structured proposal; Apply & build created CAD revision `f5f0cb3a22034e0f8b67f1b4733b5573`; fixed face 1 and loaded face 9 were selected through the UI; the confirmed GPU run `af02566402df43b2b0125ff688188e74` completed. This mesh has 3,070 tetrahedra and 16,974 DOFs. The GPU portion took 14.684 s, with 19.3 s recorded for solve plus final postprocessing. Its backend-verified relative residual is 7.74e-9.

The report package was extracted into a separate temporary directory and its included `reproduce.py` actually executed. Full displacement relative difference: 5.06e-11; peak stress relative difference: 7.12e-11. All 18 manifest entries verified. The four-page PDF was rendered and each page visually inspected, including the reference and annotation text. The final report, package, original result and verification are in `evidence/demo/`.

The saved study preserves reference, annotations, chat, material, fixtures, forces, CAD ID and run ID. A browser reload restored the reference/chat/CAD successfully. Stress and displacement views, explicit deformation exaggeration, reset camera and save-study controls were exercised. During development, a transient interaction stall after hot reload required reloading; the built app is the final handoff surface. No mobile-sized viewport or physical camera test is claimed. The final TypeScript/Vite build passed; the bundled Three.js chunk triggers a non-blocking bundle-size advisory.

The built app was opened at `http://127.0.0.1:8000/`, its saved-study picker restored the full completed study, and its results/Stress controls displayed the saved run with no captured console errors. Current screenshots are preserved in the Co-review record `af7148a48b474b5ab72689e2c71e6f3b`, bound to source revision `d6f8148`; its exact page was opened and the reference, built result, GPU detail and report evidence options were verified. Screenshot data returned as JPEG was transcoded to PNG for the review importer; the page content was not edited.

- Review: http://127.0.0.1:8848/reviews/?id=af7148a48b474b5ab72689e2c71e6f3b
- All reviews: http://127.0.0.1:8848/reviews/

Human review remains open; verification does not mark the design accepted.

## Conversational setup checkpoint

The 19 additional automated checks cover complete proposal application without automatic confirmation, changed context and CAD revisions, invented or conflicting face assignments, explicit material/force inputs, structured answer validation, the apply endpoint, provenance tampering, and an actual archived CPU reproduction preserving its proposal and interview transcript. The complete 52-test suite and TypeScript/Vite build passed again on September 14 after the STL/print path. The existing bundle-size advisory remains.

Two live Astra calls were exercised in the browser on September 9. An ambiguous heavy-load request returned three questions with no setup proposal. Explicit illustrative material, rear X=0 restraint and total [0,0,-150] N on the selected X=80 face returned proposal `cebc9a619837423188d290b01629635d`, bound to CAD revision `f5f0cb3a22034e0f8b67f1b4733b5573`. Inputs and replies are preserved in `evidence/conversational/`. Changing Young's modulus disabled the proposal; restoring the original value allowed preview, with Run simulation disabled during preview.

This September 9 checkpoint was pending at the time. The September 20 integration acceptance above completes a fresh conversational print proposal, preview, application, GPU solve, saved comparison reload and report handoff. It uses new run IDs and does not retroactively broaden the older evidence.
