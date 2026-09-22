# STL import and print analysis

OpenFEA can take a watertight triangle mesh, turn its surfaces into selectable patches, and optionally replace the isotropic solid with a documented homogenized print model. The integration repairs and conversational print workflow were verified on 2026-09-20; see [VALIDATION.md](VALIDATION.md).

The print model is an equivalent solid. It is not a slicer, not an explicit infill mesh, and not a calibration against printed coupons.

## Import an STL

`POST /api/stls` reads binary or ASCII STL (`backend/stl_io.py`). Inspection records:

- triangle count and axis-aligned bounds
- suggested unit scale when the extents look like metres or inches
- signed volume, surface area
- watertightness, boundary-shell count, boundary edges, non-manifold edges, degenerate triangles and inconsistent triangle winding; dense inputs receive the same checks

Open or multi-shell meshes below the working triangle limit can be inspected, but cannot be meshed. Dense unsupported sources are rejected before simplification can erase defects. This STL importer requires one closed boundary shell with consistent winding; separate components and enclosed cavities with multiple boundary shells are unsupported. These checks do not certify freedom from geometric self-intersections. `scaled_stl_path` rechecks both source and working bytes, including historical uploads. Uniformly inverted winding can be reversed; mixed winding must be repaired before using enclosed volume or mass.

Gmsh then runs `classifySurfaces` so clustered triangles become selectable faces. Those patches are not CAD faces. After a rebuild, fixtures and loads must be chosen again.

A first visit with an empty workspace opens the example coupon on the local CPU, checks confirmation, and leaves **Run simulation** available. GPU remains an explicit choice.

In the workspace:

1. **Import STL** or **Use example print coupon**, or accept the first-visit coupon.
2. Check the scale, watertightness line, and listed warnings.
3. Build the reviewed STL, then specify material, fixtures and forces manually or interview with Astra. Own-part imports leave supports and loads empty and confirmation unchecked. Only the labelled first-visit demonstration adopts illustrative PLA, an X=0 fixed face and total [0,0,-40] N on the X=40 face.

STLs over 80,000 triangles receive guarded quadric reduction using pinned `fast-simplification` 0.2.0. The first attempt removes redundant tessellation using the library's lossless mode; conservative attempts target 8,000 then 40,000 triangles if needed. The algorithm name is not an accuracy guarantee. Each candidate is rounded to actual binary-STL precision, stripped of collapsed output faces, and independently checked before it can be stored:

- One closed, consistently wound boundary; no degenerate faces or non-manifold edges; unchanged Euler characteristic.
- At most 1% enclosed-volume change, with unchanged global orientation.
- A measured surface-distance upper bound at most 0.01% of the longest dimension, at every vertex, edge midpoint and face centroid in both directions. For a 60 mm part, that limit is 0.006 mm.

Distances are to actual target triangles. Triangle-size groups and enclosing-radius searches avoid mistaking sparse target vertices for surface deviation. Count-targeted reductions merge vertices connected by very short mesh edges, with maximum edge length and vertex movement bounded by one tenth of the surface budget. A connected chain is left intact if any vertex would move farther; this cleanup does not weld nearby vertices on unrelated edges. It replaces grid rounding for count-targeted output, where close endpoints could survive on opposite sides of a cell boundary. Lossless output retains its established finer grid, one hundredth of the surface budget. Both paths now reject a candidate if cleanup reverses a retained triangle's normal; inspection metadata records which cleanup was used. All acceptance checks apply **after** cleanup and binary precision conversion. The bound applies only to the declared samples; it does **not** certify global Hausdorff distance, absence of self-intersections, or preservation of every small hole, wall or fillet. Inputs that fail are rejected with a request for a coarser CAD export; no fidelity threshold is relaxed to meet a triangle count. Dense inspection/reduction runs outside the API event loop.

Inspection retains original/working hashes and counts, volume change, both the historical vertex-distance field and the new sampled surface measurements, limits and reduction mode. Confirm scale and explicitly accept preprocessing with `accept_stl_preprocessing=true` before meshing; changing scale clears the UI review checkbox. Count-targeted reductions retain their checked surface facets during volume meshing to avoid expensive surface parametrization cuts. The requested mesh size controls the interior; it does not regenerate finer CAD curvature or guarantee boundary refinement. Original bytes, scaled working geometry and transformation metadata accompany model exports; no empty STEP is offered for a discrete STL. Existing results and reports remain readable and reproducible. **Historical welded uploads must be re-uploaded before building a new mesh**, because their earlier preprocessing has not passed the current surface budget. Their stored geometry is not silently replaced.

Rejected reductions report the source count, local working limit, achieved count for each attempt, and reason for rejection. Sample-distance failures include the measured bound and limit in source units. Prefer the original STEP model when available, or a CAD export with tolerances that preserve the intended small features. The [original 1.44-million-triangle assessment](ORIGINAL-STL-VALIDATION.md) records a valid closed source that the current reducer cannot bring within both the count and fidelity limits; this is a supported rejection, not a successful import.

`examples/print-coupon.stl` is a 40 × 10 × 8 mm closed box (3,200 mm³). Dimensions are demonstration inputs.

## Print settings

The Print tab writes `PrintSettings` onto the analysis:

| Setting | Role |
|---|---|
| Enabled | Off keeps the original isotropic solid. |
| Rotation (deg, XYZ Euler) | Orients print Z (layer normal) in global axes. The mesh is not rebuilt. |
| Infill pattern / density | Core stiffness factors and filament fraction. 100% infill is treated as isotropic filament. |
| Wall count × line width | Nominal perimeter depth measured inward from each actual layer contour, including hole boundaries. |
| Top / bottom layers × layer height | Nominal solid skins at local exposed surfaces, measured using neighboring layers. |

`POST /api/print-preview` returns effective moduli, volume fraction, and filament mass without solving. Changing print settings clears the result, confirmation and applied-proposal provenance while keeping fixture/load drafts. Review and confirm each changed configuration. Print axes and build direction are displayed beside the settings and in Astra proposal previews. Astra requires explicit adoption of all print inputs and binds them to the model/reference/setup revision. The first print solve is pinned automatically. Results lead with displacement, residual and mass, plus stored `guidance` that says what not to treat as printed strength.

## Homogenized stiffness

`backend/print_geometry.py` transforms the model surface into the print frame and intersects it with layer midplanes. Closed contours preserve internal holes and disconnected islands within a layer. Inward offsets measure nominal perimeter depth; intersections with neighboring layers identify local top/bottom skins. A partial final layer uses its actual thickness. These volumes define a global shell/core fraction; `backend/print_model.py` treats the remaining core as `infill_density × pattern factor`.

The method is recorded as `layer-contours-v1`. Open contours are rejected, with the same repair message in preview and readiness. Midpoint sampling and the meshed surface approximate CAD curvature and fine features; a volume discrepancy above 1% is disclosed. The local contour budget is 10,000 layers and 200 million layer/triangle pairs. These limits request adjusted settings or a coarser surface, never a silent bounding-box fallback.

Illustrative core factors (not coupon-calibrated):

| Pattern | In-plane | Layer |
|---|---:|---:|
| Rectilinear | 0.95 | 0.32 |
| Grid | 1.00 | 0.40 |
| Triangles | 1.05 | 0.45 |
| Gyroid | 0.82 | 0.72 |

The solver uses one transversely isotropic stiffness throughout the body, rotated about print Z into global axes. It does **not** place separate stiff walls and soft infill in the FE mesh. Bending behavior from that spatial distribution is therefore unresolved. Reported mass is `layer-sampled solid volume × volume fraction × density`. Assumptions are copied onto the result and into PDF/HTML/ZIP reports.

OpenFEA does not use an RVE or calibrated filament/bonding law. Its table of factors remains illustrative. Nominal perimeter/skin volumes do not model bead overlap, variable extrusion widths, gap fill or actual toolpaths.

## Slicer usage comparison — 2026-09-22

An isolated OrcaSlicer 2.4.2 comparison used the same input surfaces, 0.2 mm layers, nominal 0.4 mm widths, three walls, four top/bottom layers, 20% gyroid and density 1.24 g/cm³. Classic walls, flow 1, no supports/adhesion/purge, and fixed upright orientation were used. The sum of positive XY extrusion by model role agrees with the slicer's rounded filament-length total within 0.01 mm. Effective settings, source surfaces, measurement-only G-code and hashes are retained under `evidence/slicer-usage-artifacts/`; regenerate with `python -m scripts.compare_slicer_usage`.

| Synthetic input | Historical box estimate | Layer contours | Slicer deposition | Contour difference |
|---|---:|---:|---:|---:|
| 40 × 10 × 8 mm box | 2.154 g | 2.154 g | 2.107 g | +2.23% |
| 60 × 24 × 16 mm channel, 2 mm walls/floor | 2.924 g | 7.171 g | 7.079 g | +1.29% |
| 20 mm tall tube, OD20/ID16 | 1.207 g | 2.804 g | 2.620 g | +7.01% |

This exploratory comparison supports removing the box approximation for hollow/thin geometry. It does not establish a universal error bound or physical mass. The tube still differs by 7%; its slicer uses gap fill and bead geometry that the nominal envelope does not resolve. The saved G-code omits machine startup operations and is for measurement only, not printing. Stiffness calibration still requires measured coupons in multiple orientations.

The expanded [orientation/wall/profile matrix](SLICER-MATRIX.md) records 30 cases: 27 measured differences range from -14.37% to +7.09%, while three oblique cases were rejected by the slicer and have no mass comparison. Some orientation rankings disagree. Estimated filament covers the part only, excluding supports, adhesion and purge; check usage and orientation trends with the intended slicer profile. Print-frame rotation does not verify bed contact, overhangs or printability. These limits appear in current preview assumptions and new reports.

The follow-up identifies an empty first printable layer as the supported diagnosis for those oblique rejections. Three separate automatic-tree-support cases complete; their part-only differences are −8.31%, +4.64% and −0.44%, with support deposition recorded separately. OpenFEA now adds a narrow first-layer geometric diagnostic: the first model-layer midsection is offset inward by half the nominal line width. If it leaves no positive-area region, preview and new reports advise checking first-layer extrusion, bed contact and supports in the slicer. Exact-width and variable-width paths can differ; a positive area does not certify a printable first layer. This adds guidance, not a solve gate or a change to stiffness/mass calculations. See the [measurements and method](SLICER-MATRIX.md#oblique-diagnosis-and-separate-support-comparison).

## Compare two print configs

Pin a completed run. Change orientation, walls, or infill. Confirm and solve again. Results show a side-by-side table (displacement, peak von Mises, filament mass, solid fraction, effective E, print settings and volume method). `GET /api/runs/{a}/compare/{b}` is the same payload. The API returns `same_analysis_context` and `context_differences` across model, mesh, interpolation, material, supports, loads and print volume method. Changed conditions are disclosed; their effects cannot be attributed to print settings alone. Pins survive browser and saved-study reload.

Browser check on 2026-09-14, CPU, example coupon, same mesh, −40 N:

| Config | Solid equivalent | Filament mass | Max displacement |
|---|---:|---:|---:|
| Gyroid 20%, 3 walls | 54.3% | 2.15 g | 1.11 mm |
| Gyroid 60%, 3 walls | 77.1% | 3.06 g | 0.821 mm |

Residual on both runs: 1.8e-11. Peak stress stayed near 14.7 MPa (fixture-edge singularity, not a print-strength result).

## Cancel a job

While a mesh or solve is running, **Cancel** on the busy overlay calls `POST /api/jobs/{id}/cancel`. Queued work cannot launch after cancellation; running worker process groups are stopped. Each frontend operation owns its cancellation signal, and cancellation during GPU iteration/readback destroys device buffers instead of cancelling a concurrent Astra request. The UI reports `The job was cancelled.` Completed or failed jobs are left as-is.

## Tests

`tests/test_stl_print.py` and the API cancel checks cover:

- open vs closed STL inspection
- reject non-STL bytes
- refuse to mesh an open shell
- 100% vs sparse infill stiffness and mass
- rotation moving the soft axis
- selectable faces + print solve residual
- compare deltas

`docs/VALIDATION.md` records the suite and browser evidence.

## Solver and migration limits

New analyses use P2 with at most 500,000 total DOFs; GPU return payloads use the same cap and browser buffer limits are checked before dispatch. Oversized meshes request coarsening instead of silently changing to P1. Historical archives reproduce their recorded P1/P2 order. Re-run old off-axis print studies: the former inverse rotation was corrected on 2026-09-20, so old results are not current evidence of the intended orientation. Stored artifacts and IDs remain unchanged.

New print analyses use actual layer contours from September 22. Historical results without `geometry_method` retain `bounding-box-v1` in archive reproduction and GPU/CPU parity checks. Comparisons across methods warn that differences cannot be attributed to changed print settings alone. Re-run a baseline using the new method before interpreting an infill/orientation comparison. The older browser results above are historical box-method evidence.
