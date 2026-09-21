# ChatGPT Sites publishing plan

Status: planned, not deployed. The current working application runs locally. No Site has been registered, source pushed, secret provisioned or version published.

## Intended hosted experience

A signed-in user opens OpenFEA on ChatGPT Sites, uploads a reference, annotates dimensions, works with Astra on a reviewable solid, defines fixtures and forces, and runs the stiffness solve on their own hardware GPU through WebGPU. Every report identifies the compute device and numerical verification. Geometry processing must have a concrete implementation before this is a standalone hosted product.

## Execution split

| Function | Current implementation | Sites destination |
|---|---|---|
| Reference annotation / 3D viewport | React / Three.js browser UI | Retain browser UI on Sites |
| Sparse structural solve | WebGPU CG with float64 browser residual refinement | Retain on user's GPU; require actual hardware adapter |
| CAD / STEP / tetrahedral meshing | Native Python Gmsh / OpenCASCADE on local computer | First hosted release: authenticated geometry service; evaluate browser WASM as a later alternative |
| Matrix assembly / stress / verification | Native scikit-fem and NumPy on local computer | Same geometry service initially; later evaluate browser assembly and postprocessing |
| Astra | Installed, signed-in Codex CLI, GPT-6 Astra | Server-side authenticated model transport; validate actual hosted access to Astra first |
| Study records | Local JSON + browser localStorage | Owner-scoped D1 records, R2 artifacts if cloud persistence is selected |
| Reports / archives | Local Python ReportLab / ZIP | Geometry service initially; signed downloads through Sites |

The Sites plugin's installed runtime contract uses Cloudflare Workers with 128 MB per isolate and a Workers-compatible JavaScript entrypoint. It does not supply a native Python/Gmsh process environment. Uploading this Vite frontend alone would leave CAD, model inspection, Astra, study persistence and reports broken. The GPU computes the sparse iterative solve; WebGPU rendering alone does not meet the requirement.

## Delivery sequence and acceptance gates

1. **Keep the verified local baseline.** Preserve the CPU analytical benchmarks and actual GPU-versus-CPU comparison. Keep mesh/CAD hashes, runtime metadata and the full solution export. Both solver paths operate on the same immutable mesh and load definition. The GPU path must pass a server-recomputed relative free-DOF residual below 1e-7.
2. **Add a hosted application boundary.** Adapt the existing Vite project to the Sites Worker contract without reinitializing over the application. Use the Sites Vite integration, sign-in helpers and an owner-scoped study model. Split local-only Codex CLI transport from the hosted API. Add server-side request size, per-user job/concurrency limits, idempotent jobs, timeouts and artifact retention. Ensure image and CAD records cannot be read across accounts.
3. **Choose and provision the geometry service.** Run the existing open-source native engine in a bounded container service behind authenticated HTTPS. Send model parameters, STEP and loads there, then return sparse matrices to the user's browser; the user's GPU remains the iterative solver. Disclose that geometry/reference data crosses the service boundary. Do not run a dense or CPU-only cloud solve while labelling it local GPU. A local-companion edition is an alternative, but needs explicit pairing, a narrow origin allowlist and browser local-network permission testing; merely allowing all CORS origins is inadequate.
4. **Resolve hosted Astra access.** The current desktop account and CLI cannot be embedded in a public Worker. Verify whether the chosen hosted model transport exposes GPT-6 Astra for this account. Do not substitute a different model silently. If an OpenAI API key is required, use the installed environment's approved key-provisioning flow and store it as a Sites secret. This is a release dependency, not an already-configured capability.
5. **Port and verify the full journey.** Run the exact tension and bending checks against hosted assembly; compare browser GPU and CPU reference solutions on identical meshes. Verify image upload, annotations, questions for unknown scale, accepted CAD proposal, STEP import, multiple loads, report links, snapshot restore and account isolation. Test WebGPU on representative Apple/Windows GPUs, device loss, denied camera, unsupported GPU and memory limits. Unsupported hardware must show an explicit CPU option or an actionable message. Report generation must reject a submitted displacement vector with an unacceptable residual.
6. **Prepare the specific release.** Register one private Site, configure only the necessary capabilities and runtime secrets, build Worker-compatible output, and inspect migrations. Report the local commits to push, verification results, selected Sites target/access and continuity risks. Obtain the user's explicit push approval before any source push; local preview/build permission does not authorize this. Package the exact validated source/build using the Sites helper, save that version, publish with the appropriate access approval, and verify the deployment status and full hosted journey.

## Optional browser-only engineering path

A future WASM path can move CAD/meshing, assembly and report generation into browser workers. This needs a maintained OpenCASCADE/Gmsh WASM build, licensing/redistribution review, robust STEP import, bounded memory use and parity against the current numerical corpus. Do not commit to browser-only general CAD based on a simple primitive demo. Scope it as a separate feasibility milestone: reproduce the bracket and imported STEP geometry/mesh, solve and report on target devices, then decide whether it can replace the geometry service.

## Release risks and continuity

- Existing local studies contain references to local immutable files. Add explicit import/export migration; never assume browser localStorage moves to the hosted origin.
- GPUs expose different limits and precision/performance. Record device identity as browser-reported and preserve numerical acceptance independently.
- Sparse matrix transfer and assembly size can dominate small-part runtime; GPU acceleration is not a measured speedup claim.
- Gmsh GPL terms and the OpenFEA GPL-3.0-or-later source must remain available with redistributed builds. Model access is separately licensed and authenticated.
- Hosted access control, retention, quotas, secrets, Astra entitlement and the native service are still unimplemented. The current server intentionally rejects foreign origins and is unsuitable for exposure as a public server.

Planning evidence: installed Sites building/hosting skills, their runtime references and live tool descriptions inspected 2026-09-09. Recheck these contracts at release time; platform capabilities may change.
