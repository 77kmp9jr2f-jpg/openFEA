# Architecture and data flow

The React workspace holds a reviewable design draft. Edits invalidate the current result; geometry edits require a rebuild before the simulation can run. The server owns immutable model and run artifacts. A study snapshot references those artifacts and preserves the image, annotations, chat and simulation draft together.

```mermaid
flowchart LR
  I[Image / camera + annotations] --> A[Astra structured proposal]
  A --> R[User reviews dimensions]
  STEP[Single-solid STEP] --> G[Gmsh / OpenCASCADE]
  R --> G
  G --> M[CAD revision + tetrahedral mesh]
  M --> L[Astra loading interview / actual face context]
  L --> R2[Preview proposal / apply / confirm]
  R2 --> U[Material / supports / global XYZ forces]
  M --> U
  U --> P[Quadratic scikit-fem matrix assembly]
  P --> GPU[Browser WebGPU sparse CG]
  P --> CPU[Explicit SciPy CPU reference]
  GPU --> S[Independent residual check / stress recovery]
  CPU --> S
  S --> V[Stress / displacement / equilibrium]
  V --> D[PDF + HTML + reproducibility ZIP]
```

`backend/schemas.py` is the input boundary. All mechanical numeric values reject NaN/Infinity, and geometry/load/material ranges are bounded. Astra output is JSON schema constrained, then revalidated through the same geometry schema. It produces parameters and ordered boolean primitives; the application executes fixed, checked modelling code.

`geometry.py` creates one OpenCASCADE solid or reads STEP, creates a linear tetrahedral geometry mesh and records the triangle membership of every CAD face. The solver upgrades displacement interpolation to P2 through scikit-fem. Face loads and constraints are selected by CAD face ID bound to the model revision. Faces are reselected after every rebuild, even if the mesher happens to reuse a numeric ID.

`simulation_proposals.py` stores a validated, complete setup with its CAD revision and a SHA-256 binding to the geometry, material, supports, forces, application notes, reference and annotations seen by Astra. Applying requires that context to remain unchanged. The browser shows a separate preview, applies only after an explicit click, and never checks confirmation automatically. Manual edits clear proposal provenance. The solver verifies that a claimed applied proposal matches the submitted material/conditions/notes/reference before assembly. The exported interview is a bounded transcript snapshot; it is not independently authenticated evidence of the user's statements.

`solver.py` maps CAD triangles to mesh facets. For each force it computes the discrete face area and integrates a constant traction, ensuring the requested total force is preserved. Dirichlet constraints include vertex and quadratic edge DOFs. The solution checks free-DOF residuals and computes all fixed-DOF reactions and moment balance. It writes full solution arrays and separately produces vertex samples for the viewer.

`jobs.py` keeps a bounded worker queue and runs meshing, solving, and Astra in child processes. The server remains responsive; job timeout terminates its process group. Completed job/result JSON is written atomically. The frontend polls one job ID. Interrupted server restarts do not yet reconnect an in-flight browser request; completed immutable artifacts remain on disk.

`report.py` reads only the stored result and its corresponding model, never the current UI draft. It produces an independent vector stress view, records force definition, constraints, material, dimensions, solver versions and hashes, and builds a self-contained archive. The snapshot can be re-solved with `reproduce.py` using the same mesh.

STL imports are inspected for watertightness, shells, open/non-manifold edges and implausible scale, then meshed after `classifySurfaces` so triangle clusters become selectable load/support patches. Optional print settings (`backend/print_model.py`) replace isotropic Lamé constants with a transversely isotropic stiffness about the print-Z axis and scale reported mass by the estimated filament fraction. That model is an AABB-based homogenization, not an explicit infill mesh.

Current limits include one connected body, predefined or box/cylinder CSG proposals, STEP or watertight STL, one active reference per study, fixed supports only, no CAD fillet UI, no general photogrammetry, and no physical-material or printed-coupon calibration. Camera access depends on the browser and hardware. The optional Astra service is not open source. Gmsh is serialized with a process file lock plus the in-process thread lock.

The default GPU route prepares an immutable analysis snapshot, transfers a CSR sparse matrix and load vector, and solves on the browser's hardware WebGPU adapter. Symmetric Jacobi scaling and float64 browser residual refinement correct float32 GPU drift. No result is accepted until the backend reconstructs the system from the stored mesh/setup and verifies a relative residual below 1e-7. Reported adapter information is browser-provided; the numerical check is independent. Unavailable hardware and device/precision failures produce errors, never a silent CPU substitution. `frontend/src/gpu.ts` contains the WGSL compute kernels and orchestration. See `SITES-PUBLISHING-PLAN.md` for the hosted execution boundary.
