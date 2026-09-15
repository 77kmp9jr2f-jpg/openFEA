# Agent contract

Agents set up and run OpenFEA through the HTTP API. They do not scrape the workspace.

`GET /api/agent` returns this contract as JSON. `POST /api/readiness` returns the same verdict the UI shows.

## Gates

- `confirmed` must be `true` on `POST /api/solve`. The schema rejects anything else.
- The solver rejects a free-DOF relative residual ≥ `1e-7`.
- Scope is one connected solid, small-strain static linear elasticity, optional homogenized print equivalent.
- Model-generated CAD or solver code is never executed. Agents send schema-constrained JSON.
- `POST /api/solve` is the local CPU reference solver. GPU is an explicit browser WebGPU path (`/api/gpu/prepare` then `/api/gpu/finish`) and is not headless.

Deferred: contact, plasticity, printed-part strength, hosted Sites, sketch-to-mesh.

## Workflow

1. `POST /api/stls` (raw bytes, `X-Filename`) or `POST /api/steps`. Mesh only a watertight STL.
2. `POST /api/models` with a `Geometry` body. Poll `GET /api/jobs/{id}` until `status` is `complete`.
3. `POST /api/readiness` with the model id and the intended material, `fixed_faces`, `loads`, and `confirmed`.
4. If `status` is not `ready`, apply `recommended` or the `fix` on each failed check. Do not invent extra physics.
5. Review the verdict. Then `POST /api/solve` with the same setup and `confirmed: true`.
6. Poll the job. Read `guidance`, `relative_residual`, `max_displacement_mm`, mass, `model_sha256`, `mesh_sha256`, and `warnings`.
7. `GET /api/runs/{id}/report/json` (or html/pdf/zip) is the same snapshot a human exports.

## What to trust

`guidance.trust` names displacement, residual, and mass. `guidance.caution` names peak stress, yield ratio, and homogenized print stiffness. Those sentences are stored on the result so the workspace and the report cannot drift.
