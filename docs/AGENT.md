# Agent contract

Agents set up and run OpenFEA through the HTTP API. They do not scrape the workspace.

`GET /api/agent` returns this contract as JSON. `POST /api/readiness` returns the same verdict the UI shows.

## Gates

- `confirmed` must be `true` on `POST /api/solve`. The schema rejects anything else.
- The solver rejects a free-DOF relative residual ≥ `1e-7`.
- Readiness derives the actual quadratic DOF count from the immutable mesh and blocks systems above 500,000 DOFs. Request a coarser mesh; new solves never silently downgrade interpolation. Historical linear-element reports remain reproducible.
- Scope is one connected solid, small-strain static linear elasticity, optional homogenized print equivalent.
- Model-generated CAD or solver code is never executed. Agents send schema-constrained JSON.
- `POST /api/solve` is the local CPU reference solver. GPU is an explicit browser WebGPU path (`/api/gpu/prepare` then `/api/gpu/finish`) and is not headless.

Deferred: contact, plasticity, printed-part strength, hosted Sites, sketch-to-mesh.

## Workflow

1. `POST /api/stls` (raw bytes, `X-Filename`) or `POST /api/steps`. Review units and preprocessing first; explicitly set `accept_stl_preprocessing=true` only after reviewing a simplified STL. Mesh only a watertight STL.
2. `POST /api/models` with a `Geometry` body. Poll `GET /api/jobs/{id}` until `status` is `complete`.
3. `POST /api/readiness` with the model id and the intended material, `fixed_faces`, `loads`, `print`, and `confirmed`.
4. If `status` is not `ready`, ask for missing physical inputs or follow the `fix` on each failed check. `recommended` contains demonstration suggestions, not user evidence or permission to invent loading. Review and explicitly adopt appropriate conditions.
5. Review the verdict. Then `POST /api/solve` with the same setup and `confirmed: true`.
6. Poll the job. Read `guidance`, `relative_residual`, `max_displacement_mm`, mass, `model_sha256`, `mesh_sha256`, and `warnings`.
7. `GET /api/runs/{id}/report/json` (or html/pdf/zip) is the same snapshot a human exports.

## What to trust

`guidance.trust` names displacement, residual, and mass. `guidance.caution` names peak stress, yield ratio, and homogenized print stiffness. Those sentences are stored on the result so the workspace and the report cannot drift.

## Print-aware Astra setup

`POST /api/assistant` accepts the complete `print` object alongside geometry, material, supports and loads. Astra asks for missing or unapproved manufacturing inputs. A complete simulation proposal supplies every print setting explicitly. `/api/setup-proposals/{id}/apply` binds that object to the source context and returns `confirmed:false`. The solver rejects a submitted setup whose print settings differ from its applied proposal. Manual edits must clear `setup_proposal_id` and require fresh review. Model and proposal comparison normalizes older optional geometry defaults without rewriting immutable stored records.
