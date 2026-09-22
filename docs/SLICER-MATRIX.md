# Slicer orientation, wall and profile comparison

Measured on 2026-09-22 with installed OrcaSlicer 2.4.2. This is a model-only deposition comparison, not printed mass, stiffness calibration, a printability check or a universal error bound.

Thirty cases use the exact frozen box, open-channel and hollow-tube surfaces from the earlier [usage comparison](PRINT-STL.md#slicer-usage-comparison--2026-09-22). Twenty-seven produced comparable toolpaths; all three oblique cases failed during slicer processing with exit 156 and the generic message `Errors`. Their input STLs and diagnostic logs are retained. The log does not establish a specific root cause; no check was bypassed to obtain a number.

Each cell is `(OpenFEA estimated mass / slicer deposited mass - 1) × 100`. Positive means OpenFEA estimates more material. Unchanged settings are three 0.4 mm walls, 0.2 mm layers, four top/bottom layers, 20% gyroid, flow 1 and density 1.24 g/cm³. The last row uses the X1 Carbon 0.6 mm nozzle / 0.30 mm Standard profile with matching nominal widths and heights; it changes multiple profile parameters, so it does not isolate nozzle diameter alone.

| Variation | Box | Channel | Tube |
|---|---:|---:|---:|
| 3 walls / 20% infill | +2.23% | +1.29% | +7.00% |
| 1 wall | -5.66% | -7.98% | -10.11% |
| 5 walls | +2.75% | +2.43% | +7.00% |
| 60% infill | +4.24% | +1.99% | +7.00% |
| X rotation 90 degrees | +0.59% | -0.19% | -4.55% |
| Y rotation 90 degrees | +4.32% | +7.09% | -4.69% |
| XYZ rotation 30/45/20 degrees | Slicer rejected | Slicer rejected | Slicer rejected |
| X90 / 1 wall | -1.14% | -7.49% | -14.37% |
| X90 / 5 walls | +1.15% | +1.23% | +0.68% |
| 0.6 mm nozzle / 0.3 mm layers | -3.67% | +3.87% | +6.78% |

## What to adopt

Keep layer contours as a nominal geometric estimate and compare actual usage with the intended slicer profile. The measured range is **-14.37% to +7.09%** in these cases; it is not an accuracy guarantee. One-wall cases show the largest underestimates. In the thin upright tube, nominal perimeters consume all core space, so changing infill has no effect. The horizontal tube also demonstrates that the estimate and slicer can rank orientations differently. Do not fit a universal correction factor or material stiffness to this small deposition dataset.

The workspace and new reports now explicitly say that mass covers the part only, excluding support, adhesion and purge, and that print-frame rotation does not evaluate bed contact, overhangs or printability. Some measured orientations would require manufacturing review even though a toolpath was generated. Globally homogenized wall/infill stiffness still needs separate spatial-mechanics evidence and measured coupons.

The 0.3 mm channel case has a 1.923% layer-sampled solid-volume discrepancy because its thin floor is sampled at finite layer spacing. Production preview already discloses discrepancies above 1%. This comparison does not silently rescale the estimate to hide the discrepancy.

## Reproduction and checks

Run `.venv/bin/python -m scripts.compare_slicer_matrix` from the repository root. It needs the installed macOS OrcaSlicer app and BBL profiles; alternate paths are command-line options. It never sends to a printer. The expected exit is **1 while any case is rejected**, including the current three oblique failures; inspect the complete JSON rather than interpreting the exit code as an aborted harness. `--only` accepts explicit geometry-scenario IDs for diagnosis; use a separate `--output` to preserve the full record.

The runner reads frozen STL bytes, transforms them into the same print frame as OpenFEA, centers them on the bed and disables automatic arrangement/orientation. The initial probes caught unexpected arrangement rotation; the saved 3MF placement must now contain translations only. OrcaSlicer's [versioned CLI source](https://raw.githubusercontent.com/OrcaSlicer/OrcaSlicer/v2.4.2/src/OrcaSlicer.cpp) initializes arrangement rotations as enabled. Raw placement XML is retained so this check can be repeated without the temporary project.

Every measured case checks effective walls, widths, heights, skins, infill, density, diameter and flow. Positive XY extrusion is summed by model role, excluding retract/prime/custom moves, then converted with the effective filament diameter and density. The sum agrees with the slicer's rounded filament total within 0.0051 mm. Support/adhesion/purge are disabled. Profile-specific bead overlap, bridging, gap fill, compensation and other settings remain in the effective settings file; this is not an exact bead-envelope model.

Evidence: [30-case record](../evidence/slicer-matrix.json), [artifact and report checks](../evidence/slicer-matrix-review.json), and [compressed inputs, toolpaths, settings, placement XML and logs](../evidence/slicer-matrix-artifacts/). All 171 compressed and uncompressed hashes were independently verified. Files use output-specific directories so a diagnostic record cannot overwrite another record's evidence. Failed cases retain available artifacts and never receive a fabricated mass comparison.

Independent review checked transformations, deposition accounting and effective settings; it found and prompted repairs to artifact isolation and placement retention. The existing three-case runner's default profile files remain byte-identical. Sixteen affected print tests pass, including actual current/historical archive reproduction. A fresh CPU coupon report retains the new guidance on four visually checked pages. No numerical print model or immutable historical result was changed.

Remaining work: additional printer families, wall generators, infill patterns and support-aware toolpaths; diagnosis of the oblique slicer failures; physical mass and stiffness coupons across orientations. These remain distinct from software verification.
