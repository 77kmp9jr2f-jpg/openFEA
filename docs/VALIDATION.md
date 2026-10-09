# Validation record — updated 2026-10-09

This records software and numerical evidence, not physical acceptance or a generally validated CAD reconstruction service.

## Repository maintenance verification — 2026-10-09

The checkout was clean at application commit `6082c0e`, with 31 commits ahead of
the freshly fetched `origin/main`. Before the requested documentation update and
push, the following checks ran against that application source on macOS arm64,
Python **3.12.14**, and Node.js **26.10.0**:

| Check | Result |
|---|---|
| `.venv/bin/python -m pytest -q tests` | **116 passed** in 47.52 seconds; two dependency deprecation warnings |
| `node --experimental-strip-types --test tests/frontend-*.test.ts` | **17 passed**, no failures or skips |
| `npm run build` | TypeScript and Vite production build passed; existing chunk-size advisory |
| `.venv/bin/python -m pip check` | No broken requirements |

The dependency warnings concern Starlette's HTTPX test client and AnyIO's
`BlockingPortal` alias. The build emits a 794.33 kB JavaScript chunk before gzip,
above Vite's 500 kB advisory threshold. Neither warning failed its check.

Only documentation changed in this maintenance pass. Hardware GPU, live Astra,
browser interaction, the longer import/refinement benchmarks and physical print
checks were not rerun; the dated evidence below retains its original scope.
The [CI workflow](../.github/workflows/ci.yml) uses Ubuntu, Python 3.12 and Node 22;
its [per-commit results](https://github.com/77kmp9jr2f-jpg/openFEA/actions/workflows/ci.yml)
must be checked independently of these local results. The workflow has no
deployment step, and Sites remains a planned, separately approved release.

Upgrade continuity: refresh pinned Python and npm dependencies as described in
the README, preserve ignored `data/` (or `FEAR_DATA_DIR`) and browser storage,
and retain immutable completed runs and historical print methods. Earlier welded
STL uploads require a fresh upload and current fidelity checks before new meshing;
their saved models/results remain available. The original dense STL rejection and
remaining acceptance items in [PLAN.md](PLAN.md) are unchanged.

## Astra interpretation of recorded print runs — 2026-09-22

Astra's result context previously omitted the run's print data, while its system
guidance still described the older bounding-box approximation. It now receives
the immutable run's method, settings, usage and assumptions separately from
current draft controls. Guidance explains contour accounting and globally
homogenized mechanics, preserves historical methods, and requires missing data
to be acknowledged. Archived conversations are not added to the bounded context.

All **27 affected tests pass** with the two known dependency warnings. Three new
transport cases first reproduced the missing-context failure, then passed for
contour, bounding-box and absent print records. An independent review reran those
three cases and found no actionable defect. Mocked transport tests establish
context fidelity, not general language-model obedience.

Two live production Astra calls used preserved synthetic runs while draft
controls deliberately specified 90% infill and a different orientation. Astra
correctly explained the contour run's recorded **35%** gyroid infill and actual
layer regions. It described the historical run's recorded **20%** gyroid infill
and bounding-box assumptions, acknowledging that its method field was absent.
Both replies excluded supports, adhesion and purge from part usage, and proposed
no change. Run and original-study hashes remain unchanged. The [retained requests,
replies and checks](../evidence/astra-print-context.json) support this pair of
prompts only; no new GPU, browser or physical-validation claim is made.

Two fixed PyMeshLab reductions also reached 80,000 triangles on the original
1.44-million-triangle STL, preserving topology and the volume budget, but both
failed the unchanged surface gate. Neither is adopted. See the [measurements and
scope](ORIGINAL-STL-VALIDATION.md#independent-pymeshlab-probes--2026-09-22).

## Chrome GPU and full large-archive reproduction — 2026-09-22

Google Chrome **154.0.8037.17** completed the retained perforated-plate benchmark on this computer's Apple `metal-3` GPU: **31,333 P2 tetrahedra / 157,239 DOFs**. The setup was restored through Studies, inspected in Simulation, explicitly confirmed, and run using the GPU selection. The server independently verifies residual **1.3898e-9**. The full displacement field is identical to the earlier in-app-browser result and differs from the retained float64 CPU solution by **1.0885e-9** relatively; peak stress differs by **1.1286e-9**. Setup, mesh, geometry, interpolation and every DOF coordinate match. Independent review recalculated these comparisons and verified result, solution and source hashes.

The run is `3dedaa808aba4a4d876aea8847846535`; study `a1a98b62beab42619fa57f3b043a5dba` preserves it. Reloading Chrome and opening Results restores the exact report identity. The original completed conversational study remains unchanged. Both the rendered plate and the numerical interpretation panel were visually inspected. The new run records 7,200 dispatched iterations, three refinements, 16.145 seconds of GPU orchestration and 25.553 seconds including verification/postprocessing. Assembly and transfer are excluded; this is not a controlled end-to-end timing comparison.

The exported package passes all **27 manifest hash checks**. Its own `reproduce.py` then executed successfully in isolated temporary storage using the archived source and original mesh. The reproduced CPU run has residual **1.0046e-12**, identical setup/mesh/DOF coordinates, and the same GPU-versus-CPU displacement and stress differences above. This closes the previously unexecuted archive-reproduction check for the large plate case. No product code changed in this verification pass.

Evidence: [Chrome/CPU/in-app-browser comparison](../evidence/chrome-gpu-comparison.json), [executed archive reproduction](../evidence/chrome-gpu-archive.json), [rendered plate](../evidence/chrome-gpu-plate-result.png), and [numerical checks](../evidence/chrome-gpu-plate-checks.png). This verifies a second browser on the **same hardware**, not another GPU or physical driver loss. General stress convergence and material/print calibration remain unproven.

The original large STL was also tested with two Blender 5.1.1 configurations. Collapse to 79,998 triangles fails the unchanged surface gate despite retaining topology/volume; planar-only dissolution at 0.1° still leaves 1,419,732 triangles. Both are rejected, with source bytes unchanged. [Measurements and scope](ORIGINAL-STL-VALIDATION.md#independent-blender-probes--2026-09-22) preserve these configurations without adopting them or claiming other settings cannot work.

## First-layer guidance and supported slicer comparison — 2026-09-22

The three unsupported oblique slicer failures reproduce with detailed logs. Source inspection and controlled probes narrow the cause to an empty first printable layer: removing box elephant-foot compensation alone still fails, while enabling automatic tree supports with otherwise identical profiles/input STLs lets all three complete. Part and support deposition are measured separately; model-only estimate differences are −8.31% (box), +4.64% (channel), and −0.44% (tube). The combined extrusion totals reconcile within 0.00469 mm, and all 27 final artifacts pass compressed/uncompressed hash checks. The initial supported probe's macOS graphics-initialization abort is retained; only complete desktop-enabled exports are accepted. See the [full method and evidence](SLICER-MATRIX.md#oblique-diagnosis-and-separate-support-comparison).

Preview and new reports now advise slicer review when the first model-layer midsection has no positive-area region after a half-line-width inward offset. This is a nominal footprint diagnostic, not proof of first-layer toolpaths, adhesion or printability, and not an FEA readiness gate. Independent current-versus-prior checks on six frozen cases retain identical preexisting region values, full stiffness matrices and usage results. All **23 affected tests pass** with the two known dependency warnings, including an oblique CPU/P2 solve whose warning appears in preview, archived JSON, HTML and the executed reproduction. Historical print-method reproduction also passes.

The production browser displays the warning for the preserved coupon's [30,45,20]° print frame; the [inspected screenshot](../evidence/print-first-layer-warning.png) shows it with unchanged 2.52 g usage. The completed GPU result and comparison are restored afterward, and the original saved-study hash is unchanged. No new GPU execution or physical-print claim is made for this guidance change.

## Original large STL rejection — 2026-09-22

The preserved 1,441,642-triangle `biscuit-blockerv4.stl` was reprocessed in isolated temporary storage. Its original boundary passes shell, edge, winding and degeneracy checks, but the production reducer stops at 317,596 triangles after conservative count-targeted cleanup, above the 80,000 limit. Three experimental 80,000-target candidates retain topology and volume but fail the unchanged 0.0345-source-unit surface budget. Stronger aggression and coordinate normalization were **not adopted**. No mesh or solve was accepted, and the source hash is unchanged. The [assessment](ORIGINAL-STL-VALIDATION.md) and linked measurements retain the failures and their scope.

Import errors now expose the source/working limits, each achieved triangle count and rejection reason, and suggest original STEP or a controlled CAD export. Surface errors include the measured bound and limit in source units. Production reduction order, cleanup and acceptance thresholds are unchanged. All **25 affected backend tests pass** with the two known dependency warnings, including two new diagnostic regressions identified by independent review: output hard links must not overwrite the source, and malformed inputs must replace stale success evidence. The retained runner also exercises the accepted small-coupon path; no new browser, GPU or physical validation is claimed for this diagnostic change.

## Study and reference ownership — 2026-09-22

The production browser reproduced annotation history crossing studies: delete a mark in study A, open study B with the same reference image, then Undo replaced B's dimension with A's. Restoring a study now resets the reference editor even when the image ID is unchanged. Replacing an image already reset it and remains supported. A failed restore does not increment the editor revision. Reference inputs, undo/redo, deletion and image replacement now respect the active-job lock; SVG pointer and drop handlers also refuse edits while locked.

Two other reproduced races started loading without owning the workspace: initial autosave restoration and the example-coupon asset fetch. A user could open a newer study while either waited, then lose that selection when the old response arrived. Both now lock workspace-changing controls before awaiting their inputs, release on completion/failure, and prevent new Astra requests during the transition. Existing Astra work can still finish independently of a solver cancellation. Old comparison responses, including errors, are ignored after the pinned/current run pair changes.

Six controlled probes exercise the actual `App.tsx` callbacks/effects with deferred HTTP responses: startup, example loading, late comparison success/error, automatic first launch and recovery after startup failure. All observations match the expected behavior. The retained [probe](../evidence/workspace-race-probe.cjs) uses an explicitly stepped hook harness with mocked HTTP, visual components and GPU; it is diagnostic evidence, **not real React scheduling or browser execution**. The [before/after record](../evidence/workspace-races.json) records the final source hash.

Separate real-browser checks verify ordinary within-study delete/undo/redo, fresh history after switching to a study sharing the image, and disabled note/delete/redo/replace/library controls during an actual mesh build while Cancel remains available. After meshing, editing is available and study B's dimension is intact. The [browser record](../evidence/workspace-reference-editing.json) and [inspected screenshot](../evidence/workspace-reference-restored.png) preserve these observations. The original study's file hash is unchanged and its completed GPU result and pinned comparison are restored in the browser. All **17 existing frontend tests and the production build pass**; the bundle-size advisory remains. Backend/numerical source is unchanged, so the preceding 104-test and hardware GPU evidence remains scoped to that source; no new GPU solve or camera-hardware claim is made here.

## Complete interview retention — 2026-09-22

New analyses preserve the complete conversation at submission, including separately displayed questions, geometry/setup review cards and their revision markers. Previously, the browser retained only the last 24 message texts in a run. The remote Astra context remains the ten most recent messages plus the current study, but now includes each message's questions and cards. Earlier unapplied instructions may still need restating. Cards in the archive are inert JSON; the existing applied-setup validation remains separate. The 80 MB HTTP request limit and 20,000-character message-text limit reject oversize submissions without silently trimming them. Historical run records are not rewritten.

The regression tests reproduced both truncation and missing structured context before the fix. All **104 backend tests and 17 frontend tests pass**, and the TypeScript/Vite build passes. Both legacy P1/P2 packages and the new long-interview package execute their bundled reproduction scripts. Independent read-only review found no concrete regression; the two existing dependency deprecation warnings and bundle-size advisory remain.

Browser verification used a disposable copy of the saved synthetic print coupon: 12 prior messages plus 24 explicitly labelled synthetic markers (`live=false`). A real Astra request to repeat the previous separately displayed question returned that exact question, bringing the conversation to **38 messages**. Actual Apple `metal-3` GPU run `72e5b30c71144a789ac1c0ec33bbfdeb` preserves all 38, one geometry card, two simulation cards and six messages with questions. The 4,455-DOF result has maximum displacement **0.0995654 mm** and independently verified residual **4.4417e-10**.

The exported ZIP verifies all **28 manifest entries** and retains the exact transcript in both `interview.json` and `result.json`. Its extracted reproduction actually executes and preserves that transcript, with full displacement relative difference **8.0757e-13** from the GPU. Saving, reloading the browser and reopening the saved server snapshot restores the same result link, all 24 markers and both occurrences of the test question. The original study's hash is unchanged; its completed result is restored in the browser afterward. No captured browser console errors were reported.

Evidence: [verification record](../evidence/interview-retention.json), [complete synthetic transcript](../evidence/interview-retention-transcript.json), and [restored result screenshot](../evidence/interview-retention-browser.png). This establishes software traceability on the known coupon, not arbitrary long-context reasoning or new engineering/physical acceptance.

## Print-usage matrix and scope guidance — 2026-09-22

The [30-case slicer matrix](SLICER-MATRIX.md) exercises three frozen geometries across orientation, wall count, infill and two X1 Carbon nozzle/layer profiles. **27 cases produced verified model-only deposition measurements**; their OpenFEA/slicer mass differences range from **-14.37% to +7.09%**. Three oblique cases failed in OrcaSlicer with exit 156 and generic `Errors`; their source/log evidence is preserved, with no fabricated comparison or bypass. The recorded range is exploratory, not an acceptance threshold. Orientation rankings can differ, and printed stiffness is not established by deposition agreement.

All 171 retained compressed/uncompressed artifact hashes, effective settings, saved placement transforms and extrusion-role sums were independently rechecked. Automatic arrangement had rotated an initial probe; the final runner prepositions geometry, disables arrangement/orientation and rejects non-translation transforms. Independent review also prompted separate artifact directories and persistent placement XML. Existing default profile outputs are byte-identical. Full method, table and limitations are in the linked report; evidence is `slicer-matrix.json`, `slicer-matrix-review.json` and `slicer-matrix-artifacts/`.

Print preview and new result assumptions now explicitly exclude support, adhesion and purge from usage estimates and distinguish material-frame orientation from bed-contact/overhang/printability checks. All **16 affected print tests pass**, including current and historical archive subprocess reproduction. Fresh CPU run `5759744043d24a55ae054cdb510f02be` on the preserved coupon gives 0.0995654 mm displacement, 2.51677 g nominal filament and residual 1.897e-11; all four exported PDF pages were rendered and visually inspected with the added guidance present and no overflow. The production browser displays the same new preview guidance. Numerical model behavior and historical results are unchanged.

## Short-edge reduction and tube GPU recovery — 2026-09-22

Count-targeted STL reduction now merges vertices connected by short mesh edges, rather than relying on spatial-grid placement. Its radius is one tenth of the existing surface-sample budget; a connected component stays intact if any vertex would move farther. Nearby vertices on unrelated edges are not welded by this path. Lossless reduction retains the established finer grid at one hundredth of the budget. Both paths reject a candidate when cleanup reverses a retained surface triangle, then apply the unchanged independent topology, volume and sampled-distance checks. This guard prevents newly introduced local folds; it does not certify absence of all self-intersections.

Five new regressions cover a short edge across a grid boundary, an overlong connected chain, nearby unrelated edges and retained-triangle reversal in both cleanup paths. An independent review supplied the closed-prism fold counterexample: edge incidence, Euler characteristic, volume and sampled distance alone had accepted it. All **103 backend tests** now pass, with the two existing dependency deprecation warnings. No frontend behavior changed in this repair; the preceding 15-test frontend and production-build evidence remains scoped to that unchanged source.

The final dense-STL corpus passes all **69 original gates**, including the tube, open channel and two-bore plate. The tube's 248,320 source triangles reduce to 7,442 working triangles and mesh into 14,724 quadratic tetrahedra / 82,491 DOFs. Minimum quality improves from 1.407e-6 to 1.650e-4 (117-fold), while axial displacement differs from the existing CAD reference by 0.217%. The channel and plate retain their lossless route; the plate's 156,927-DOF CPU solve differs from CAD displacement by 0.293%. Mesh counts can vary between Gmsh runs. Surface/volume tolerances were not relaxed.

Actual production-browser GPU run `9e62c71c8ec847d4aec9c2c1efe2cda5` on Apple `metal-3` uses the same original tube bytes as the earlier nonconvergent case. The final reducer and orientation guard reproduce its working STL and tetrahedral mesh byte for byte. The GPU dispatched 12,000 iterations over five refinements; independently recomputed residual is **7.0824e-9**, full quadratic displacement differs from CPU by **3.7811e-9** relatively, and peak stress differs by 1.4910e-9. All existing acceptance gates pass. GPU orchestration took 13.411 seconds and solve plus verification/postprocessing 18.368 seconds; the retained CPU solve took 24.798 seconds. Preparation and transfer are excluded, so this is not an end-to-end speedup measurement.

Save/reload restores the exact GPU result and report link. The exported package verifies all 27 manifest entries and preserves source/working STL, mesh and current reduction source. Its reproduction subprocess was not rerun for this case; prior independently executed archive evidence remains below. Existing immutable models/results are unchanged; the improved cleanup applies to newly uploaded sources.

Two rejected attempts are retained: extending short-edge cleanup to lossless plate output produced near-flat tetrahedra and a rejected CPU residual; tightening that alternative triggered native Gmsh exit 139. A separate retained-facet plate prototype passed algebra but missed the existing 5% CAD displacement gate (6.18% difference), so it was not adopted. Restoring the established lossless grid preserves the passing plate workflow. No meshing algorithm or solver tolerance changed.

Evidence: [final dense corpus](../evidence/dense-stl-short-edge-validation.json), [GPU/CPU comparison and browser reload](../evidence/short-edge-gpu-comparison.json), [archive integrity](../evidence/short-edge-gpu-archive.json), [diagnosis and rejected prototype](../evidence/short-edge-diagnosis.json), [initial plate rejection](../evidence/dense-stl-short-edge-initial.json), [native failure](../evidence/dense-stl-short-edge-tight-initial.json), and [GPU result screenshot](../evidence/short-edge-gpu-result.png). The corpus records a verified comment-only source-hash reconciliation. These synthetic surfaces do not establish industrial/freeform geometry preservation, general stress convergence, other-GPU acceptance or printed-material calibration.

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
