# FEA-R

A local engineering workspace for designing a 3D part from image references, reviewing its dimensions and loading, running real finite-element analysis, and exporting a traceable report.

FEA-R uses open-source geometry, meshing, simulation, and UI components. **Astra is GPT-6 Astra, a separately authenticated proprietary AI service**, accessed through the installed Codex CLI. The modeller, solver, study storage, and exports work without AI.

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

The development UI is at http://127.0.0.1:5173. API documentation is at http://127.0.0.1:8000/docs.

## Use the workspace

1. **Reference.** Upload PNG/JPEG/WebP, use the synthetic example, or capture a camera image. Draw arrows, rectangles, dimensions, and notes. Use Select to move an annotation; undo/redo and reload preserve the saved marks. Dimensions in a note are explicit specifications, not automatic metrology.
2. **Astra.** Ask the assistant to inspect the image. It sees the reference, normalized annotation coordinates and notes, current geometry, face definitions, material, loads, fixtures, and current result summary. Supply missing dimensions, then review and apply its structured CAD proposal. No model-generated Python or shell code is executed to build CAD.
3. **Model.** Build a bracket, plate/beam, shaft/tube, a custom constructive-solid-geometry recipe, or import a single-solid STEP. Geometry and meshing are performed by Gmsh's OpenCASCADE kernel. Download STEP, STL, and the original mesh. Rebuilding clears old face selections and results.
4. **Simulation.** Use **Discuss loading** to describe the material, attachment and operating loads. Astra asks for missing inputs, then proposes a complete material/support/force setup on the actual CAD faces. **Preview on model** displays those conditions without changing the draft; **Apply to simulation** fills the controls and leaves the review checkbox unchecked. Changes to the model, reference or draft invalidate earlier proposals. You can also select faces and edit material/XYZ forces manually. Each force is a total in N, uniformly distributed over its face in global model axes. Review and confirm before solving. Local GPU is the default; select Local CPU explicitly to run the reference solver.
5. **Results.** Inspect stress, displacement, exaggerated deformation, force equilibrium, and interpretation notes. Export PDF, self-contained HTML, JSON, or the complete ZIP package. The ZIP includes original CAD/mesh, inputs/results, the last 24 interview messages, the applied Astra setup proposal when used, all quadratic solution DOFs, quadrature stresses, nodal CSV, solver source, dependency versions, hashes, and a reproduction script.
6. **Save study.** The browser automatically preserves the current workspace. Save study creates a server-side snapshot that can be reopened from Studies. Geometry revisions and analysis runs are immutable.

## Astra connection

Install the official Codex CLI and sign in with `codex login`; ensure your account has access to `gpt-6-astra`. Set `FEAR_CODEX_BIN` if `codex` is not on the server's PATH. Each request uses `codex exec` with structured output, a read-only sandbox, shell tools disabled, ephemeral sessions, and a bounded timeout. User configuration/MCP integrations are not loaded. The CLI performs normal account authentication; FEA-R does not read or expose your authentication tokens.

Sending a chat message transmits its image, annotations and design context to Astra. The UI labels real replies **ASTRA · LIVE**. Static onboarding text is labelled **WORKFLOW GUIDE**. Failures are surfaced explicitly; there is no simulated AI fallback. A health indicator confirms the CLI exists, not account entitlement or a completed model call.

## Engineering scope

- One connected, homogeneous, isotropic 3D solid, with small strains and static linear elasticity.
- Quadratic tetrahedral displacement interpolation (`ElementTetP2`), assembled with scikit-fem. The default browser WebGPU solver uses sparse conjugate gradient with symmetric Jacobi scaling and float64 residual refinement. SciPy sparse direct factorization is an explicit CPU reference option. CAD generation, assembly, stress recovery and independent verification remain on the local CPU. GPU computing is not claimed to be faster on these small meshes.
- Internal units: **mm, N, MPa**. Density is kg/m³; displayed mass is grams. STEP coordinates are converted to mm and must be checked against displayed bounds.
- Fixed faces restrain all translations. Multiple fixed/loaded faces are supported. No gravity is included automatically.
- Total face force is integrated as uniform traction over the triangulated surface; mesh refinement does not multiply the applied force.
- Reported peak stress is the maximum unaveraged quadrature-point von Mises stress. Viewport colors are volume-weighted nodal averages. Displayed deformation is explicitly exaggerated and sampled at vertices; maximum displacement includes the quadratic edge nodes.
- No assemblies/contact, friction, bolt preload, plasticity, large deformations, buckling, fatigue, dynamics, thermal loading, or 3D-print anisotropy.
- Material presets are illustrative values. An imported or photograph-inspired geometry, a converged algebraic solve, and a physical strength validation are different kinds of evidence. Sharp fixture edges and unfilleted corners may have non-convergent peak stress.
- The prototype bounds job time and mesh size (35,000 tetrahedra / 150,000 DOFs) and rejects disconnected solids. Its limits are for local responsiveness, not engineering adequacy.

## Verify

```sh
.venv/bin/python -m pytest -q tests
npm run build
```

The numerical suite includes the exact uniform 3D tension field (`nu=0`), a Timoshenko cantilever displacement comparison at two mesh sizes, force/moment equilibrium, energy, load/stiffness scaling, STEP round trips, custom boolean geometry, invalid inputs and report hashes. Test output is isolated from user studies. See [docs/VALIDATION.md](docs/VALIDATION.md) for the recorded prototype checks and their limits.

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

FEA-R source is GPL-3.0-or-later; see [LICENSE](LICENSE). Dependency versions are pinned by `requirements.txt` and `package-lock.json`. No Gmsh or other dependency binaries are vendored. See upstream [Gmsh licensing](https://gmsh.info/doc/texinfo/#License) and [Codex non-interactive documentation](https://learn.chatgpt.com/docs/non-interactive-mode) for their own terms and behavior.

## Verified example

A completed synthetic reference study is included as [PDF report](evidence/demo/FEA-R-demo-report.pdf) and [reproducibility package](evidence/demo/FEA-R-demo-package.zip). Its real local-GPU run was independently reproduced on the CPU. The example's dimensions and material are supplied demonstration inputs, not measurements or certified design data.
