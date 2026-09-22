# Original dense STL assessment — 2026-09-22

The preserved `biscuit-blockerv4.stl` upload was reprocessed with the current
importer in isolated temporary storage. **It remains unsupported at the current
working triangle limit and surface tolerance.** No alternative reduction was
adopted, and no new mesh or analysis was accepted for it.

This is the original supplied tessellation, without the artificial subdivision
used in the earlier three-fixture corpus. Its source has 1,441,642 triangles,
72,082,184 bytes and SHA-256
`8ec3d22525675ffb8780628497bdbc68ddad2356a4ab2c2d2afb0c14e8b13d80`.
It passes the current single-shell, edge-incidence, winding and degeneracy
checks, with Euler characteristic −132. These checks do not certify absence of
self-intersections. No source CAD, intended feature dimensions or physical
ground truth was supplied for this assessment.

The original coordinate extents are approximately 200 × 345 × 228.6. The
unchanged sample-distance limit is 0.0345 **source units** (0.0345 mm if the
confirmed import scale is 1 mm per source unit). The working limit is 80,000
triangles; relative volume change must remain at most 1%.

| Attempt | Triangles after cleanup | Outcome |
|---|---:|---|
| Production lossless | 1,441,614 | Exceeds working limit |
| Production target 8,000, aggression 3 | 317,596 | Exceeds working limit |
| Production target 40,000, aggression 3 | 317,596 | Exceeds working limit |
| Experimental target 80,000, aggression 5 | 79,998 | Surface bound 0.0401368 exceeds 0.0345 |
| Experimental target 80,000, aggression 7 | 79,998 | Surface bound 0.0530447 exceeds 0.0345 |
| Experimental normalized target 80,000, aggression 3 | 79,996 | Surface bound 0.0659049 exceeds 0.0345 |

All three 80,000-target candidates remain watertight, retain the source Euler
characteristic and stay within the volume budget. That is insufficient: each
fails a sampled surface-distance check. Measurements stop after the first
failing sample in each direction, so the table does **not** report a global
maximum or claim coverage of every face for these rejected candidates.

The native reducer uses absolute quadric-error thresholds. Centering coordinates
and scaling the longest extent to 1 allowed the conservative aggression setting
to reach the count target. Restoring the original coordinates before cleanup
and validation still failed the unchanged surface gate. This rejects that
normalization fallback for this part; it does not prove that every possible
reduction method would fail. Earlier 40,000-target aggression 5/7 probes also
failed the surface gate and are retained in the initial diagnostic record.

The importer now reports source/working limits and each attempt's achieved count
and rejection reason. Surface failures include the measured bound and limit in
source units. It suggests the original STEP model when available, or a CAD STL
export with controlled tolerances that retain intended small features. It does
not recommend blindly discarding detail to meet a triangle count. The production
reduction sequence, cleanup, acceptance limits and meshing behavior are unchanged.

## Reproduce

From the repository root, with its Python environment installed:

```sh
python -m scripts.validate_original_stl \
  data/stls/6aece2e705cd44bba3d302755c211625/source.stl \
  --probe-alternatives
```

The original file is local user data, not a committed/public fixture. Supply its
path on another machine. The runner always uses temporary storage, saves the
JSON report, verifies the input hash afterward and removes generated import
artifacts. Exit **1 is expected for this rejected input**; exit 0 means the
production importer accepted it. Experimental results never change that verdict
and are never installed in the production workflow. No section, meshing, solver
or GPU validation follows a rejected production import.

Evidence: [final production and experimental measurements](../evidence/original-stl-validation.json),
[initial production rejection](../evidence/original-stl-initial.json),
[initial native-reducer probes](../evidence/original-stl-reduction-initial.json).
All 25 affected STL/topology/cleanup/print and diagnostic tests pass. Two new
regressions reproduce and prevent output hard links overwriting the input and
malformed inputs leaving stale success evidence. A separate small-coupon
invocation verifies the diagnostic runner's accepted path. Independent review
confirmed both repairs; [verification record](../evidence/original-stl-verification.json).

The preserved historical upload/model/result remains available under its original
identity. Its earlier coarse-welded geometry does not satisfy the current
re-upload acceptance path. Supported ingestion of this original part, independent
tiny-feature ground truth, broader original/freeform inputs and stress
convergence remain open work.
