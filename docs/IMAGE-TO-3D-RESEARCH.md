# Image generation at OpenFEA's sketch-to-mesh step

Research decision · 2026-09-20 (America/Denver)

**Recommendation: adopt optional concept visualization as a workflow; defer production image-to-3D integration.** Run a bounded, separately approved benchmark before building a provider adapter. Keep reviewed dimensions → constrained CAD → local meshing/FEA as the engineering path. A generated surface may eventually enter as an explicitly reviewed experimental STL, never as measured CAD by default.

This session inspected code and current primary sources. It did not generate assets, spend credits, run the proposed benchmark, or establish dimensional accuracy for any provider. No implementation, merge, push, deployment, or hosting change is included.

## Repository fit

Inspected the research checkout at `ebd5fbcb674d75f9d26de148d152b971dee2dc4e` and the local `print-stl-workspace` ref at `22a47b61770146d338f0d0664ef0fc79e57637b5`, without checking out or changing that branch. These are local revision observations, not a remote freshness claim.

- [Current assistant](../backend/assistant.py) asks for missing scale and hidden geometry, returns schema-constrained bracket/plate/shaft/CSG parameters, and does not execute generated CAD code. [Geometry](../backend/geometry.py) constructs an OpenCASCADE solid and tetrahedral mesh; [setup proposals](../backend/simulation_proposals.py) bind material, loads, reference and annotations to the model context. Retain these boundaries.
- On the inspected print branch, `backend/stl_io.py` preserves original/working hashes and preprocessing measurements; `backend/geometry.py` builds selectable surface patches; `backend/report.py` archives source/working STL, provenance and reproduction code. `docs/AGENT.md` explicitly defers sketch-to-mesh. Inspect these exact versions with `git show 22a47b6:<path>`.
- That importer limits working meshes to 80,000 triangles and may weld denser inputs. Its vertex-distance bound is explicitly **not** a surface-deviation or feature-preservation certificate. Edge incidence, shell count and degeneracy checks do not constitute a complete self-intersection, vertex-manifoldness or wall-thickness check. Generated meshes need independent checks before this importer.
- Surface patches are not semantic CAD faces. Rebuilding requires renewed face selection. A plausible-looking mesh can move a fixture, fill a bore or alter a load area while still passing a local solve.
- `backend/print_model.py` on that branch uses an oriented bounding-box shell/skin estimate and illustrative infill factors in a rotated transversely isotropic equivalent solid. It is not sliced infill or calibrated printed strength. Geometry error and this approximation must be assessed separately.
- [Validation](VALIDATION.md) records earlier synthetic-reference and solver evidence, not arbitrary-photo reconstruction. [Sites](SITES-PUBLISHING-PLAN.md) remains planning only. Existing source tests were inspected, not rerun for this documentation change.

## Where generation helps—and where it breaks traceability

| Use | Decision and reason |
|---|---|
| Explore the silhouette, styling or arrangement of a new part | **Adopt as optional concept work.** It can help a person express intent before dimensions exist. Label the image synthetic; selected styling still needs a new dimensional specification. Benefit is a hypothesis, not measured time savings. |
| Clarify an existing photograph or hand sketch | Preserve the original. Use non-generative crop/contrast and editable annotations for evidence. Generative cleanup can erase a seam, enlarge a hole or invent depth. Keep any generated interpretation beside the source. |
| Explain a reviewed design | Prefer deterministic CAD renders, dimension overlays and actual solver plots. Generation can illustrate context, but must not redraw dimensions, boundary conditions or stress contours as engineering evidence. |
| Create unseen views | Useful for ideation; **not additional observations**. Feeding invented views to another model compounds one hypothesis rather than resolving occlusion. |
| Reconstruct dimensions or internal geometry | **Defer automatic acceptance.** A single uncalibrated view leaves scale and hidden features ambiguous. One supplied length only fixes uniform scale; it does not validate every diameter, thickness or position. |
| Produce an organic/decorative surface | Worth an isolated STL experiment. Retain the generated original, record repairs, measure interfaces and remesh locally. Rebuild load-bearing interfaces in constrained CAD when needed. |
| Supply materials or print settings | Reject visual inference of modulus, yield, infill, wall count, layer bonding or loads. PBR “materials” describe appearance, not constitutive properties. |

The harmful chain is **original sketch → attractive invented image → plausible invented mesh → real FEA treated as evidence about the original object**. A correct solve only describes the accepted mesh and inputs. Hashing that chain proves which invention was analyzed; it does not prove reconstruction accuracy.

## Current candidates

Documentation was checked on the research date; model availability, prices and terms need rechecking before a funded trial. No provider below has demonstrated OpenFEA's dimensional/FEA gates in this research.

| Candidate | Documented capability | OpenFEA disposition |
|---|---|---|
| OpenAI GPT Image 2.5 (`gpt-image-2.5-sunburst`, `gpt-image-2.5-flare`) | Current guide supports image generation/editing; it still identifies precise placement, text and consistency limitations. [Official guide](https://developers.openai.com/api/docs/guides/image-generation) | First concept-workflow candidate; compare one pinned model, not both initially. It outputs raster imagery, not a dimensioned solid. The installed image tool's schema does not expose a backend version, so it cannot be assumed to be a pinned API benchmark. |
| Gemini 3.1 Flash Image / Gemini 3 Pro Image | Image creation/editing, multiple reference inputs and high-resolution outputs; generated images carry SynthID. [Official guide](https://ai.google.dev/gemini-api/docs/image-generation) | Alternate concept candidate. More views or sharper labels are not dimensional constraints. No need to add a second production dependency now. |
| Meshy 7.1; Meshy T2 as a later topology comparison | Image/multi-image generation, mesh-format exports, remeshing; `auto_size` estimates real-world height and `image_enhancement` changes input processing. Multi-image accepts 1–4 views; `latest` currently resolves to 7.1. [Image API](https://docs.meshy.ai/en/api/image-to-3d), [multi-image API](https://docs.meshy.ai/en/api/multi-image-to-3d) | Primary cloud benchmark candidate on non-confidential synthetic fixtures. Pin `meshy-7.1`; disable estimated sizing and image enhancement where supported. Save raw and remeshed outputs separately. Triangle/quad topology is not a tetrahedral FEA quality guarantee. |
| Tripo P2 (`P2-20260801`) | Image and multiview generation, geometry seed, triangle/quad output and face limits. PBR can force texturing back on. [Image API](https://developers.tripo3d.ai/en/docs/generation-image-to-model/p), [multiview API](https://developers.tripo3d.ai/en/docs/generation-multiview-to-model/p) | Second cloud benchmark candidate: pin model/seed; set both `texture=false` and `pbr=false`. The seed reproducibility statement is a provider claim to test, not a substitute for archived output bytes. |
| Microsoft TRELLIS.2 | Image-to-3D with open surfaces, non-manifold geometry and PBR; code/model MIT, some dependencies separately licensed. Official setup is Linux + NVIDIA GPU with ≥24 GB; published timing is on H100. [Repository](https://github.com/microsoft/TRELLIS.2) | Preferred local-control benchmark candidate if suitable hardware is already available. It is not a documented drop-in for this macOS workflow. No service credits, but compute/setup costs remain. Its representational flexibility does not ensure a closed engineering solid. |
| Tencent Hunyuan3D-2.1 | Released shape/PBR pipeline; documented shape-only VRAM is 10 GB. [Repository](https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1) | Defer initial comparison to bound scope. Its [community license](https://github.com/Tencent-Hunyuan/Hunyuan3D-2.1/blob/main/LICENSE) has territorial restrictions, including EU/UK/South Korea exclusion; do not classify it as equivalent to an unrestricted MIT dependency. This is a released-weight alternative, not a claim that 2.1 is Tencent's latest hosted offering. |

None of the inspected generator contracts supplies OpenFEA's reviewed mechanical feature specification or a tolerance-certified B-rep. STL/GLB conversion, automatic repair and “print-ready” appearance cannot supply those missing guarantees. This is an engineering assessment of these interfaces, not a universal ranking of model quality.

## Cost, licensing and privacy

| Option | Published cost basis and rights/data implications |
|---|---|
| GPT Image 2.5 API | Guide lists $8/M image-input tokens, $30/M image-output tokens and $5/M text-input tokens; total depends on request usage, with additional main-model cost through Responses. API content is not trained on by default; standard abuse logs may retain content up to 30 days, with exceptions. Output ownership is allocated to the customer subject to applicable law and input rights. [Costs](https://developers.openai.com/api/docs/guides/image-generation), [data controls](https://developers.openai.com/api/docs/guides/your-data), [service agreement §4](https://openai.com/policies/services-agreement/) |
| Gemini | Flash Image standard output is $0.067 at 1K, $0.101 at 2K, $0.151 at 4K, plus inputs/other tokens. Paid-service prompts/responses are not used to improve products; limited safety logging remains. Unpaid-service handling differs, including human review, with regional exceptions. Google does not claim generated-content ownership. [Pricing](https://ai.google.dev/gemini-api/docs/pricing), [terms](https://ai.google.dev/gemini-api/terms) |
| Meshy | 7.1 image or multi-image: 20 credits without texture; selected higher geometry resolution adds 5. Remesh: 5 credits. Use API pricing, not Studio task pricing; the inspected API table does not establish a universal dollar/credit conversion. Paid customers own output as between the parties; free output is CC BY 4.0. **Non-enterprise inputs/outputs may be used for training unless otherwise agreed.** Private visibility is not a no-training promise. Preserve AI identifiers and avoid community publication. [API prices](https://docs.meshy.ai/en/api/pricing), [terms §§2.9, 3.2–3.3](https://www.meshy.ai/terms-of-use), [security clarification](https://help.meshy.ai/en/articles/9991999-is-my-asset-safe) |
| Tripo | P2 geometry without texture: 100 credits; developer page says $0.01/credit, hence **$1 per base P2 generation**, excluding conversion/other processing. Paid-user terms prohibit training on inputs/outputs; free-user rights differ substantially. Terms §3.2 also require prior written authorization to make the foundation-model service available to end users: resolve applicable API/supplemental terms before shipping an adapter. Retention/DPA details remain a procurement check. [Changelog](https://developers.tripo3d.ai/en/docs/changelog), [credit basis](https://developers.tripo3d.ai/), [terms §§3.2, 5.2](https://www.tripo3d.ai/terms), [privacy explanation](https://www.tripo3d.ai/help/privacy-policy/how-to-understand-data-privacy-and-ai-training-at-tripo) |

Use our own synthetic CAD fixtures first. A paid account, output license or private asset library does not itself authorize uploading a client's confidential drawing. Before sensitive use, establish input rights, applicable contract, training restriction, retention/deletion, subprocessors and storage region. Self-hosting can avoid a generation-service upload, provided the actual runtime/dependencies are configured accordingly. OpenFEA's GPL source license does not grant rights to third-party inputs or hosted models.

## Benchmark plan—proposed, not executed

### Known parts and controls

Freeze parametric sources, STEP, reference STL, units, drawing and render-camera metadata before generating anything. Dimensions below are exact synthetic inputs in mm, not physical measurements. B1 comes from [numerical tests](../tests/test_engineering.py); B2 from the [recorded demo proposal](../evidence/astra-dimensioned-proposal.json). B3–B6 are specified fixtures to build for the benchmark. Hold evaluation CAD out of generator inputs; expose only the designated images and scale datum.

| Fixture | Definition and purpose |
|---|---|
| B1 beam | Existing numerical-test solid: 100 × 10 × 10. Uniform tension and bending provide analytical controls. |
| B2 bracket | Existing demo: 80 × 40 × 60 overall, 8-thick legs, Ø8 bores at base (X=57.6,Y=20) and upright (Y=20,Z=43.2). Tests two bores, orthogonality and occlusion. |
| B3 tube | New known-CAD fixture: length 60, OD20, axial through-bore Ø12. Tests hollow topology and concentricity. |
| B4 asymmetric plate | New: 60 × 40 × 6, through-bores Ø6 at (15,12) and Ø10 at (43,27), along Z. Tests count, position and unwanted symmetry. |
| B5 U-channel | New: outer 60 × 24 × 16, 2-thick floor and side walls; channel open along X and at top. Tests thin sections and false closure. |
| B6 blind recess | New: 40 × 30 × 20 block, centered Ø10 blind bore 12 deep from top. Include a view hiding the bore and a solid-block image twin; the system must request hidden detail before engineering acceptance. |

Controls: (1) known CAD directly meshed; (2) its controlled STL imported through the print branch; (3) original image plus supplied dimension sheet through the existing constrained-proposal workflow. Control 2 isolates STL conversion/patching error. Control 3 tests whether generation actually saves reviewed-model preparation time; label its richer dimensional inputs explicitly rather than claiming equal-input reconstruction accuracy.

Test three arms with fixed images/prompts and all outputs retained:

- **A:** one unaltered CAD render or line drawing → image-to-3D.
- **B:** three genuine views rendered from the same CAD → multi-image-to-3D.
- **C:** the same single input as A → one generative “clean concept” image → the same 3D provider. This measures whether the additional image stage improves or damages reconstruction. Generated views must never be counted as B.

Start with B1–B3, A/B, Meshy 7.1 and Tripo P2, three independent generations per cell: **36 meshes, 18/provider**. Meshy base budget is 360 credits (450 if the chosen resolution adds 5/job); Tripo base budget is $18. These exclude subscriptions, processing, taxes and retries. Price the actual configuration before approval; no spending is authorized by this document. Reserve no automatic retry allowance.

Only if this screen merits continuation, run C on the winning provider: **9 image generations + 9 meshes**. Measure the image API usage separately; for example, nine Gemini 1K outputs cost $0.603 for image output alone. Separately budget one Tripo fixed-seed replay (+1 mesh, $1 base) to test its reproducibility claim; it does not count as an independent sample. Then test B4–B6 as held-out fixtures using the same arms, repetitions and thresholds, with a new bounded budget. A later real-photo phase uses measured physical versions, lens/scale documentation and concealed-feature inspection; synthetic success does not establish camera reconstruction performance.

### Measurement and acceptance gates

These are proposed screening thresholds, not standards or manufacturing acceptance. Freeze them before output inspection and tighten them to actual design tolerances when evaluating a real part.

| Area | Required evidence / initial gate |
|---|---|
| Scale and dimensions | Record raw units/bounds first. Permit only a logged rigid alignment and one uniform scale from the designated length; no anisotropic fitting. Check every feature, not just bounds. Overall lengths within 1%; bore diameter/center errors ≤0.20 mm; wall and blind-depth errors ≤0.10 mm. Missing/extra holes or closed channels fail regardless of global distance score. |
| Surface fidelity | Bidirectional area-sampled surface distance to reference CAD: median, 95th percentile and sampled maximum; report sampling density. Initial 95th-percentile gate ≤0.20 mm. Separately inspect minimum thickness and local interfaces; sampled distance is not a certified Hausdorff bound. |
| Topology and meshing | Exactly the intended connected solid, consistent outward winding, nonzero volume; no boundary/non-manifold edges or vertices, degenerate faces or triangle self-intersections. Run an independent intersection/thickness checker. Record Euler characteristics and bore connectivity against CAD. Then local tetrahedral meshing must succeed with no inverted/zero-volume elements and within app limits. Report full element-quality distribution and refinement behavior, not surface polygon count alone. |
| Processing damage | Score raw, converted, repaired and OpenFEA-working meshes separately. Log commands/versions, changed features, volume and surface deviation at each stage. A successful weld cannot erase the raw failure or its correction time. |
| Boundary conditions | Reviewer matches fixture/load regions by intended geometry, areas and normals; never reuse face IDs between revisions. Missing/unresolvable regions fail. Apply the same reviewed total force, constitutive values and support idealization as the CAD control. |
| Local FEA | First use isotropic solid settings to isolate geometry. Require free-DOF residual <1e-7, force/moment balance, <2% change in displacement/energy on refinement, and ≤5% difference in displacement/compliance/energy from a converged CAD control. Compare stress in predefined regions away from sharp fixtures/corners (initial ≤10% difference); singular peak stress is not an acceptance metric. If limits prevent refinement, mark inconclusive. |
| Provenance and export | Every artifact/transform has a hash and parent; dimension sources and reviewer acceptance are recorded. Export must reproduce the accepted local solve from archived mesh/source without calling the generator. Repeat a supported fixed-seed request to measure provider reproducibility separately. |
| Workflow benefit | Blind shape review with textures off; log queue/runtime, active correction/review minutes, failures, credits and final accepted part cost. An eligible mode (A or B, scored separately) needs ≥8/9 outputs passing all geometry/FEA gates, every fixture ≥2/3 passes, zero silent critical-feature errors, and median reviewed-part preparation time ≥25% below constrained-CAD control. Report all cells and paired per-part spread; nine outputs are screening, not reliability proof. |

For B1, reuse the existing 1000 N tension case with E=210,000 MPa, ν=0, and the 100 N bending case with ν=0.3. For B2, use the recorded illustrative E=69,000 MPa, ν=0.33, X=0 restraint and total [0,0,−100] N on X=80. Define and review the remaining fixtures' load areas/materials **before** evaluating outputs; benchmark agreement does not certify these materials.

After geometry acceptance, compare reference and reconstructed versions at identical **XYZ Euler orientations (0,0,0) versus (0,90,0) degrees, 20% versus 60% gyroid, 2 versus 4 walls, and 3 versus 6 layers on each of top and bottom**, using fixed 0.4 mm line width and 0.2 mm layer height: 16 configurations/part plus a 100% infill control. Record orientation matrices, effective stiffness, displacement, mass and settings. This checks whether geometry error changes the experimental model's trends. It does not validate its bounding-box approximation.

Physical follow-on is separate: slice frozen exports using a recorded printer/material/profile, inspect actual walls/skins/infill and load-bearing regions, then print measured coupons/parts and measure mass, dimensions and load–deflection in documented fixtures. Record filament batch/conditioning and print direction. Do not claim printed strength or an infill optimum from software agreement.

### Minimum evidence record and stop rule

Each trial retains: fixture/drawing hashes; original and generated image hashes; synthetic/captured status; provider/model/version/seed; request options and response/task ID (no credentials); terms/pricing date; raw mesh; all transforms/repairs and hashes; dimensional/topology results; operator time and actual charges; immutable OpenFEA revision, reviewed material/BCs/print settings, local solver evidence and reproduction archive. Cloud generation may not be reproducible indefinitely: preserve its returned bytes, while keeping downstream analysis reproducible.

Stop a provider after the screen if it cannot preserve critical features, needs more repair time than constrained CAD, cannot meet privacy/rights requirements, or cannot fit the meshing limits without unacceptable deviation. A visually strong failure can remain a concept tool. Only a successful held-out benchmark justifies designing a quarantined import adapter; every resulting part still requires review. Generated geometry must create a new revision, clear prior face/setup acceptance, and never trigger an automatic solve.
