# STL import and print analysis

OpenFEA can take a watertight triangle mesh, turn its surfaces into selectable patches, and optionally replace the isotropic solid with a documented homogenized print model. The integration repairs and conversational print workflow were verified on 2026-09-20; see [VALIDATION.md](VALIDATION.md).

The print model is an equivalent solid. It is not a slicer, not an explicit infill mesh, and not a calibration against printed coupons.

## Import an STL

`POST /api/stls` reads binary or ASCII STL (`backend/stl_io.py`). Inspection records:

- triangle count and axis-aligned bounds
- suggested unit scale when the extents look like metres or inches
- signed volume, surface area
- watertightness, shell count, boundary edges, non-manifold edges, degenerate triangles

Open or multi-shell meshes can be inspected. They cannot be meshed. `scaled_stl_path` refuses a non-watertight file.

Gmsh then runs `classifySurfaces` so clustered triangles become selectable faces. Those patches are not CAD faces. After a rebuild, fixtures and loads must be chosen again.

A first visit with an empty workspace opens the example coupon on the local CPU, checks confirmation, and leaves **Run simulation** available. GPU remains an explicit choice.

In the workspace:

1. **Import STL** or **Use example print coupon**, or accept the first-visit coupon.
2. Check the scale, watertightness line, and listed warnings.
3. Build the reviewed STL, then specify material, fixtures and forces manually or interview with Astra. Own-part imports leave supports and loads empty and confirmation unchecked. Only the labelled first-visit demonstration adopts illustrative PLA, an X=0 fixed face and total [0,0,-40] N on the X=40 face.

STLs over 80,000 working triangles may be vertex-welded. Inspection retains original and working hashes/counts, a vertex-distance bound and relative volume change. Confirm the unit scale and explicitly accept preprocessing with `accept_stl_preprocessing=true` before meshing a simplified STL. This bound does not establish preservation of small holes, walls or fillets. Original bytes, scaled working geometry and transformation metadata accompany new model exports; no empty STEP is offered for a discrete STL. Older uploads receive computed preprocessing metadata on reload.

`examples/print-coupon.stl` is a 40 × 10 × 8 mm closed box (3,200 mm³). Dimensions are demonstration inputs.

## Print settings

The Print tab writes `PrintSettings` onto the analysis:

| Setting | Role |
|---|---|
| Enabled | Off keeps the original isotropic solid. |
| Rotation (deg, XYZ Euler) | Orients print Z (layer normal) in global axes. The mesh is not rebuilt. |
| Infill pattern / density | Core stiffness factors and filament fraction. 100% infill is treated as isotropic filament. |
| Wall count × line width | Solid shell estimated from the oriented bounding box. |
| Top / bottom layers × layer height | Solid skins estimated from the same box. |

`POST /api/print-preview` returns effective moduli, volume fraction, and filament mass without solving. Changing print settings clears the result, confirmation and applied-proposal provenance while keeping fixture/load drafts. Review and confirm each changed configuration. Print axes and build direction are displayed beside the settings and in Astra proposal previews. Astra requires explicit adoption of all print inputs and binds them to the model/reference/setup revision. The first print solve is pinned automatically. Results lead with displacement, residual and mass, plus stored `guidance` that says what not to treat as printed strength.

## Homogenized stiffness

`backend/print_model.py` estimates walls and skins from the axis-aligned box of the rotated part, then treats the remaining core as `infill_density × pattern factor`.

Illustrative core factors (not coupon-calibrated):

| Pattern | In-plane | Layer |
|---|---:|---:|
| Rectilinear | 0.95 | 0.32 |
| Grid | 1.00 | 0.40 |
| Triangles | 1.05 | 0.45 |
| Gyroid | 0.82 | 0.72 |

The solver uses a transversely isotropic stiffness about print Z, rotated into global axes. Reported mass is `solid volume × volume fraction × density`. Assumptions are copied onto the result and into PDF/HTML/ZIP reports.

Published gyroid homogenization (RVE + periodic boundaries, compared to compression tests) finds near-isotropic effective elasticity as a function of relative density. OpenFEA does not use an RVE. The AABB + table-of-factors model is for directional trends on one mesh, not printed-part strength.

## Compare two print configs

Pin a completed run. Change orientation, walls, or infill. Confirm and solve again. Results show a side-by-side table (displacement, peak von Mises, filament mass, solid fraction, effective E, print settings). `GET /api/runs/{a}/compare/{b}` is the same payload. The API returns `same_analysis_context` and `context_differences` across model, mesh, interpolation, material, supports and loads. Changed conditions are disclosed; their effects cannot be attributed to print settings alone. Pins survive browser and saved-study reload.

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
