# OpenFEA

A local engineering workspace for designing a 3D part from image references, reviewing its dimensions and loading, running real finite-element analysis, and exporting a traceable report. The product name is **OpenFEA**. Environment variables still use the `FEAR_*` prefix so existing local setups keep working.

OpenFEA uses open-source geometry, meshing, simulation, and UI components. **Astra is GPT-6 Astra, a separately authenticated proprietary AI service**, accessed through the installed Codex CLI. The modeller, solver, study storage, and exports work without AI.

## Run locally

Prerequisites: Python 3.12+, Node.js 20.19+ or 22.12+, and a WebGPU-capable browser with a hardware GPU (or explicitly choose the CPU reference solver). The prepared workspace already includes dependencies.

```sh
./scripts/start.sh
```

Open **http://127.0.0.1:8000**. The script creates a virtual environment and installs dependencies on first use, builds the frontend, then starts a server bound to loopback. Use `FEAR_PYTHON=/path/to/python3.12 ./scripts/start.sh` if your default Python is older. A compiler or OpenGL runtime may be needed for Gmsh on some platforms; macOS arm64 is the verified environment.

For development, run the backend and frontend in separate terminals:

```sh
.venv/bin/python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000 --reload --reload-dir backend
npm run dev
```

The development UI is at http://127.0.0.1:5173. API documentation is at http://127.0.0.1:8000/docs. Agents start at [docs/AGENT.md](docs/AGENT.md) and `GET /api/agent`.

## Use the workspace

1. **Reference.** Upload PNG/JPEG/WebP, use the synthetic example, or capture a camera image. Draw arrows, rectangles, dimensions, and notes. Use Select to move an annotation; undo/redo and reload preserve the saved marks. Dimensions in a note are explicit specifications, not automatic metrology.
2. **Astra.** Ask the assistant to inspect the image. It sees the reference, normalized annotation coordinates and notes, current geometry, face definitions, material, loads, fixtures, and current result summary. Supply missing dimensions, then review and apply its structured CAD proposal. No model-generated Python or shell code is executed to build CAD.
3. **Model.** Build a bracket, plate/beam, shaft/tube, a custom constructive-solid-geometry recipe, import a single-solid STEP, or import a watertight STL. Geometry and meshing are performed by Gmsh. Download STEP, STL, and the original mesh. Rebuilding clears old face selections and results. STL import checks scale, watertightness, shells and mesh defects, then clusters triangles into selectable surfaces.
4. **Print.** Optional. Set orientation, infill, walls, line width, layer height and skins. Those settings change a documented homogenized stiffness and estimated filament mass. They are not a sliced toolpath and not a calibration against printed coupons. Pin one result and run another configuration to compare displacement, stress and mass.
5. **Simulation.** Readiness lists missing fixtures, loads, material and confirm. Use recommended faces or click them. Each force is a total in N, uniformly distributed over its face in global model axes. Confirm before solving. Local CPU is the default; GPU is an explicit WebGPU choice.
6. **Results.** Inspect stress, displacement, exaggerated deformation, force equilibrium, and interpretation notes. Export PDF, self-contained HTML, JSON, or the complete ZIP package. The ZIP includes original CAD/mesh, inputs/results, the last 24 interview messages, the applied Astra setup proposal when used, all recorded solution DOFs, quadrature stresses, nodal CSV, solver source, dependency versions, hashes, and a reproduction script.
7. **Save study.** The browser automatically preserves the current workspace. Save study creates a server-side snapshot that can be reopened from Studies. Geometry revisions and analysis runs are immutable.

## Astra connection

Install the official Codex CLI and sign in with `codex login`; ensure your account has access to `gpt-6-astra`. Set `FEAR_CODEX_BIN` if `codex` is not on the server's PATH. Each request uses `codex exec` with structured output, a read-only sandbox, shell tools disabled, ephemeral sessions, and a bounded timeout. User configuration/MCP integrations are not loaded. The CLI performs normal account authentication; OpenFEA does not read or expose your authentication tokens.

Sending a chat message transmits its image, annotations and design context to Astra. The UI labels real replies **ASTRA · LIVE**. Static onboarding text is labelled **WORKFLOW GUIDE**. Failures are surfaced explicitly; there is no simulated AI fallback. A health indicator confirms the CLI exists, not account entitlement or a completed model call.

## Engineering scope

- One connected 3D solid with small strains and static linear elasticity; isotropic material by default, or the documented print equivalent below.
- Quadratic tetrahedral displacement interpolation (`ElementTetP2`), assembled with scikit-fem. The optional browser WebGPU solver uses sparse conjugate gradient with symmetric Jacobi scaling and float64 residual refinement. SciPy sparse direct factorization is an explicit CPU reference option. CAD generation, assembly, stress recovery and independent verification remain on the local CPU. GPU computing is not claimed to be faster on these small meshes.
- Internal units: **mm, N, MPa**. Density is kg/m³; displayed mass is grams. STEP coordinates are converted to mm and must be checked against displayed bounds.
- Fixed faces restrain all translations. Multiple fixed/loaded faces are supported. No gravity is included automatically.
- Total face force is integrated as uniform traction over the triangulated surface; mesh refinement does not multiply the applied force.
- Reported peak stress is the maximum unaveraged quadrature-point von Mises stress. Viewport colors are volume-weighted nodal averages. Displayed deformation is explicitly exaggerated and sampled at vertices; maximum displacement includes the quadratic edge nodes.
- Optional print model: transversely isotropic equivalent solid from walls, skins, infill density/pattern and a print-axis rotation. Assumptions are written into the result. Not sliced geometry, not coupon-calibrated, not certified printed-part strength.
- No assemblies/contact, friction, bolt preload, plasticity, large deformations, buckling, fatigue, dynamics, thermal loading, or explicit infill geometry.
- Material presets are illustrative values. An imported or photograph-inspired geometry, a converged algebraic solve, and a physical strength validation are different kinds of evidence. Sharp fixture edges and unfilleted corners may have non-convergent peak stress.
- The prototype bounds job time and mesh size (200,000 tetrahedra / 500,000 DOFs) and rejects disconnected solids. Dense CAD STL exports are accepted up to 80 MB and coarsened when needed. Readiness counts the actual quadratic DOFs before solving. Oversized meshes require coarsening; new analyses never silently switch to linear tetrahedra. Historical P1 archives retain their recorded interpolation when reproduced.

## Verify

```sh
.venv/bin/python -m pytest -q tests
node --experimental-strip-types --test tests/frontend-jobs.test.ts
npm run build
# Longer known-CAD import/refinement benchmark (isolated temporary data):
.venv/bin/python -m scripts.validate_imports
```

The numerical suite includes the exact uniform 3D tension field (`nu=0`), a Timoshenko cantilever displacement comparison at two mesh sizes, force/moment equilibrium, energy, load/stiffness scaling, STEP round trips, custom boolean geometry, STL watertightness and print-stiffness comparison, invalid inputs and report hashes. See [CONTRIBUTING.md](CONTRIBUTING.md), [docs/PRINT-STL.md](docs/PRINT-STL.md), and [examples/print-coupon.stl](examples/print-coupon.stl). Test output is isolated from user studies. See [docs/VALIDATION.md](docs/VALIDATION.md) for the recorded prototype checks and their limits.

## ChatGPT Sites

Publishing is planned in [docs/SITES-PUBLISHING-PLAN.md](docs/SITES-PUBLISHING-PLAN.md). The browser GPU solver is implemented. Hosted CAD/assembly, Astra authentication, persistence and reports still require a service boundary; a static upload alone cannot provide the working application. Nothing has been pushed or deployed.

## Storage and portability

All runtime artifacts live in `data/` (ignored by Git), or `FEAR_DATA_DIR` when set. Back up this directory to keep studies and all original references and models. The active browser workspace is stored in localStorage; use Save study before switching browsers. The ZIP's `reproduce.py` re-solves the original mesh without a running server.

This server is intended for the local machine. It rejects foreign browser origins and non-local hostnames. It has no multi-user login or public-service hardening; do not expose it to the internet.

## Open-source components

| Component | Role | Upstream license |
|---|---|---|
| [Gmsh](https://gmsh.info/doc/texinfo/) / OpenCASCADE | CAD booleans, STEP, meshing | GPL-2.0-or-later with Gmsh exception; OpenCASCADE LGPL-2.1 with exception |
| [scikit-fem](https://github.com/kinnala/scikit-fem) | Finite-element assembly | BSD-3-Clause |
| NumPy / SciPy | Numerical arrays and sparse solver | BSD-3-Clause |
| FastAPI / Uvicorn / Pydantic | Local API and validation | MIT / BSD-3-Clause / MIT |
| React / Three.js / Vite / Lucide | Interface and 3D review | MIT / MIT / MIT / ISC |
| Pillow / ReportLab | Reference processing and reports | HPND / BSD |
| Codex CLI | Optional authenticated Astra transport | Apache-2.0; hosted model access separate |

OpenFEA source is GPL-3.0-or-later; see [LICENSE](LICENSE). Dependency versions are pinned by `requirements.txt` and `package-lock.json`. No Gmsh or other dependency binaries are vendored. See upstream [Gmsh licensing](https://gmsh.info/doc/texinfo/#License) and [Codex non-interactive documentation](https://learn.chatgpt.com/docs/non-interactive-mode) for their own terms and behavior.

## Verified example

A completed synthetic reference study is included as [PDF report](evidence/demo/FEA-R-demo-report.pdf) and [reproducibility package](evidence/demo/FEA-R-demo-package.zip). Those files keep the older FEA-R label because they are a hashed handoff snapshot. Its real local-GPU run was independently reproduced on the CPU. The example's dimensions and material are supplied demonstration inputs, not measurements or certified design data.
