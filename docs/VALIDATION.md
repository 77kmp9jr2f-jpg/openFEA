# Validation record — updated 2026-09-22

This records software and numerical evidence, not physical acceptance or a generally validated CAD reconstruction service.

## GPU recovery and larger-system verification — 2026-09-22

Pending adapter/device acquisition, shader compilation, pipeline creation and readbacks now participate in the solve's cancellation and 150-second deadline. Device loss and uncaptured GPU errors interrupt pending operations. All allocated buffers and the device are released; a device arriving after cancellation is destroyed. Each explicit retry requests a fresh adapter. This removes waits that could keep the UI busy despite cancellation or loss. The [WebGPU working group's ordering discussion](https://github.com/gpuweb/gpuweb/issues/4177) also cautions that device destruction is not a faithful physical driver-loss simulation; this record makes no such claim.

All nine initial lifecycle regression cases reproduced a failure before the repair. Adapter-wait coverage was added afterward. **15 frontend tests now pass**, including ten GPU lifecycle checks; the CI command includes both files. Two targeted backend checks confirm independent residual rejection and the supported submission-length contract. TypeScript/Vite production build passes with the existing bundle-size advisory. An independent read-only review found the missing CI inclusion (repaired) and no further concrete runtime defect.

Actual production-browser execution used the imported synthetic two-bore plate from the dense-STL corpus: **31,333 P2 tetrahedra / 157,239 DOFs**, minimum mesh quality 0.0529. GPU run `2830d44d7b9444dcaf618d24ca7bbf8a` used browser-reported Apple `metal-3`, 7,200 dispatched iterations and three refinements. Its independently recomputed residual is **1.3898e-9**. The full quadratic displacement field differs from the retained float64 CPU reference by **1.0885e-9** relatively; peak stress differs by 1.1286e-9. Identical setup, interpolation and mesh hashes were checked before comparison. All existing 1e-5 displacement / 1e-4 stress / 1e-7 residual gates pass. This compares implementations on one mesh, not physical or stress-convergence acceptance.

GPU orchestration took 15.152 seconds; recorded solve plus verification/postprocessing took 25.562 seconds, compared with the retained CPU solve's 116.678 seconds. The GPU figure excludes the separate preparation job and transfer; these are not controlled end-to-end speedup measurements. Saving and reloading restored the exact run/report identity. Export verifies all 27 manifest entries, including the original/working STL, mesh, current GPU source and reduction module. Archive reproduction was not rerun for this larger case; independent reproduction evidence for the existing dense import and print paths appears later in this record.

The 84,324-DOF imported tube supplies adverse-mesh evidence: minimum quality 1.407e-6. Cancelling during actual GPU iteration restored the reviewed setup and enabled Run. The next explicit GPU attempt reached the iteration/refinement limit but had relative residual **0.211**, so it was rejected and no result was accepted. Its passing CPU axial check does not establish GPU convergence. The final build also displays plain cancellation/retry guidance while preserving an earlier completed result. No tolerance was relaxed and no automatic CPU substitution was added.

Evidence: [inputs and hashes](../evidence/gpu-large-inputs.json), [GPU/CPU comparison](../evidence/gpu-large-comparison.json), [recovery observations](../evidence/gpu-recovery.json), [archive integrity](../evidence/gpu-large-archive.json), and `gpu-large-*.png`. Other GPUs/browsers, physical driver loss and an actual 500,000-DOF solve remain unverified.

## Guarded dense-STL import — 2026-09-22

The frozen tube, channel and two-bore plate surfaces were subdivided, written as binary STL, uploaded through the production reducer, explicitly accepted, meshed and solved with CPU/P2. All **69 declared checks pass**. Source topology is checked before reduction; accepted outputs preserve shell count, edge/winding validity and Euler characteristic, stay within 1% volume change, and bound the declared bidirectional surface samples within 0.01% of the longest dimension (0.006 mm here). This is a sample budget, not global Hausdorff certification. The selected-section checks retain their separate, predeclared 0.1 mm boundary / 2% area / unchanged hole-count gates.

| Synthetic surface | Source → working triangles | Largest sampled section boundary difference | Axial displacement difference from CAD |
|---|---:|---:|---:|
| Tube | 248,320 → 7,844 | 0.000328 mm | 0.226% |
| 2 mm open channel | 267,904 → 34 | < 1e-12 mm | < 1e-10% |
| Two-bore plate | 267,008 → 14,440 | 0.00000224 mm | 0.295% |

The corresponding quadratic systems have 84,324, 53,172 and 157,239 DOFs. All residual, force and moment gates pass. Measured import preprocessing took 11–27 seconds on this host; complete import/mesh/CPU checks took 24–153 seconds. The largest conservative sample-distance upper bound was 0.005987 mm; the maximum relative volume change was 0.00000559%. These bounds can exceed the true nearest-surface distance because any sufficiently close target triangle can establish the sample budget.

Retained evidence: [final corpus](../evidence/dense-stl-validation.json), [frozen inputs](../tests/fixtures/dense-stl/README.md), and [distance-search review](../evidence/dense-stl-search-review.json). `python -m scripts.validate_dense_stl` reproduces the corpus in isolated storage. The `dense-stl-initial`, `dense-stl-first-pass`, `dense-stl-meshing-initial` and `dense-stl-quadric-initial` JSON files retain failed welding, incomplete reduction, the interrupted Gmsh parametrization attempt and intersecting reduced facets. Final cleanup merges near-coincident output vertices on a grid 100 times finer than the sample budget; validation runs after cleanup and binary precision conversion.

The complete 98-test backend suite passed during integration; all 19 affected checks passed again after final meshing/cleanup changes. Five frontend regressions and the TypeScript/Vite build pass. The [browser record](../evidence/dense-stl-browser.json) covers real dense upload, rejection before preprocessing consent, scale-dependent limits with renewed consent, the accepted channel build and saved study; screenshots retain the model and review controls. The prior GPU study was restored afterward. The new dense-channel report archive validates all 27 manifest entries, preserves the exact original STL and fidelity module, and its extracted reproduction executes with identical full displacement values: [archive check](../evidence/dense-stl-archive.json).

Historical welded uploads require re-upload before new meshing; existing models/results remain available. This corpus uses redundant tessellation of existing piecewise-planar CAD surfaces, not newly resolved curvature or representative industrial/freeform inputs. Stress convergence, self-intersection certification, other GPU/device acceptance and printed-material calibration remain separate work.

## STL source topology repair — 2026-09-22

Two reproduced import defects are fixed. A dense two-shell input could lose its small component during welding and then pass inspection. A cube with one flipped triangle could mesh successfully while reporting 666,666.7 mm³ instead of its actual 1,000,000 mm³, corrupting volume-based mass. Small and dense inputs now share shell, degeneracy, edge and winding checks; source bytes are validated before simplification and again before meshing, including historical uploads. Globally inverted winding remains supported. Multiple boundary shells (including enclosed cavities) and self-intersection certification remain outside the supported scope.

All 14 affected STL/print tests passed; five dedicated topology regressions cover the original failures, historical source loss and uniform inversion. An independent recheck also verified a translated, inverted cube at scale 2: 8,000,000 mm³. Retained results: [STL topology recheck](../evidence/stl-topology-recheck.json).

## Print contour correction and flexure acceptance — 2026-09-22

The print equivalent now measures nominal perimeter/skin/core volumes on actual layer contours. A 2 mm channel exposes the previous box approximation: its upright walls have no nominal infill space, yet the former model assigned the same fractions as a solid box. Independent geometric controls cover a box, channel, hollow tube, arbitrary frame rotation and open-contour rejection. Preview and solve agree, readiness rejects failed contour estimates, and actual archive subprocesses reproduce both the new contour method and historical box results with matching full displacement vectors. An independent review also exercised 25 rotated boxes; midpoint volume error remained below 0.011% in that probe. This is geometric accounting, not spatial wall/infill mechanics or calibrated printed stiffness.

An exploratory OrcaSlicer 2.4.2 comparison found new mass estimates +2.23% (box), +1.29% (channel) and +7.01% (tube) above deposited filament. The old box model underestimated channel/tube deposition by 58.7%/53.9%. No post-hoc accuracy gate or physical-mass claim is attached. The measured inputs, effective profiles, measurement-only toolpaths and hashes are retained with [the comparison](../evidence/slicer-usage-comparison.json); procedure and limitations are in [PRINT-STL.md](PRINT-STL.md).

Production-browser verification on the saved synthetic coupon (rotation [30,45,20]°, 35% gyroid, three 0.4 mm walls, 0.2 mm layers, four top/bottom layers, illustrative PLA, face 9 fixed and 4 N downward on face 7) completed actual Apple `metal-3` WebGPU run `12f9942450724ed1876b14254905a847`: 4,455 DOFs, 0.0995654 mm displacement, 2.51677 g estimated filament and 4.44e-10 verified residual. Full displacement differs from CPU by 8.08e-13 relatively. The exported ZIP verifies all 27 manifest entries and its bundled reproduction actually runs, preserving 12 conversation messages, the reference and annotation. Historical GPU parity still passes using its recorded box method. Save/reload retains the new run and old pin; their comparison visibly discloses the changed volume method. Evidence: `print-contour-gpu-comparison.json`, `print-legacy-gpu-comparison.json`, `print-contour-archive.json`, and `print-contour-comparison.png` under `evidence/`.

`python -m scripts.validate_flexure` completed eight synthetic isotropic CPU/P2 cases: three CAD levels and a frozen medium-CAD STL per fixture. All **38 gates** pass: 5% analytic response, 2% successive response change, 3% STL/fine-CAD difference, and 1e-7 residual/relative force/relative moment equilibrium. The 160 × 24 × 16 mm channel has 2 mm walls/floor and a total 10 N end load; P2 end-face quadrature measures mean deflection against the slender Euler–Bernoulli reference. The tube (120 mm long, OD12/ID8) uses a loading bar and two opposing 10 N forces to apply 200 N·mm with zero resultant force; a rotation/translation fit on X=24–84 mm measures twist away from the ends. The fit uses mesh vertices without area weighting, with fit residual reported but ungated. MIT reference links and complete inputs are recorded in the evidence.

| Fixture | CAD response error, coarse / medium / fine | STL response error | Largest successive change | STL / fine CAD |
|---|---:|---:|---:|---:|
| Channel bending | 1.427 / 1.522 / 1.577% | 1.607% | 0.0941% | 0.0295% |
| Tube torsion | 1.941 / 1.080 / 0.576% | 1.614% | 0.852% | 1.033% |

The initial run is retained in `evidence/flexure-validation-initial.json`: 6/4 mm tube meshes exceeded 5% error and the STL import failed with zero tetrahedra. Requested tube sizes were refined to 2/1.5/1.1 mm without relaxing the limits. The STL defect was a partial Gmsh surface parameterization contaminating its topology fallback; a clean reload repairs it and a frozen failing STL protects the path. Final results are in `evidence/flexure-validation.json` (13,842–286,008 DOFs, approximately 729 seconds total solve time). Review corrected the channel's equilibrium denominator from 20 N to its actual 10 N; `--recheck` recomputed gates from unchanged raw solve metrics and records the evaluator hash. All passes remain. These response checks do not establish asymptotic or stress convergence, dense-STL simplification fidelity, print calibration or another GPU's behavior.

The report's added assumptions exposed a nearly empty overflow page. Its reproducibility section now stays together and shares space with the attached reference when it fits. All four revised pages were rendered and inspected; the method is explicit in the definition table, while setup notes retain their original wording. `evidence/print-contour-report.pdf` preserves the reviewed output. Archive hashes were refreshed and bundled reproduction source remained byte-identical to the independently executed package.

Current checks: **88 backend tests**, **five frontend regressions**, and TypeScript/Vite production build pass. After the report layout adjustment, all 51 affected geometry/engineering/proposal/archive tests passed again. Independent contour/migration and benchmark reviews found no remaining blocking defect. Known dependency deprecation and bundle-size advisories remain. Remote CI, device/camera coverage and physical coupons remain pending.

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

The production browser reopened the completed print study and its pinned comparison after the recovery changes. Historical print-warning boilerplate is clarified in the workspace as it is in exported reports: the directional print equivalent exists, while additional raster-scale anisotropy, local voids, bonding defects and moisture are not modeled. Immutable run JSON is unchanged.

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
