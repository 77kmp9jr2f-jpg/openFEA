# Making FEA more common and easier

Research notes for the next OpenFEA goal. The question is not “how do we add more physics.” It is why people who already have a part still do not run a useful, honest analysis.

## What actually blocks people

**Geometry and mesh prep come before theory.** CAD-to-FEA still fails on slivers, unused holes, and interdependent features. Design Science interviews on industrial variation simulation name *lack of robust CAD* and *complexity of automated processes* as the main barriers, ahead of missing equations ([Wahlström et al., 2021](https://doi.org/10.1017/dsj.2021.21); also [Digital Engineering on CAD–FEA integration](https://www.digitalengineering247.com/article/integrate-fea-and-cad)). OpenFEA already inspects STL watertightness and scale. It does not yet walk a new user through “this mesh is usable / this face is the support / this number is a singularity.”

**Interpretation does not automate.** Altair and COMSOL commentary on simulation apps is consistent: designers can compare a displacement or a yield ratio, but they miss failure modes and valid ranges. Apps without stated limits produce confident wrong answers ([Limits of FEA automation](https://www.digitalengineering247.com/article/limits-of-fea-automation)). OpenFEA already writes assumptions onto every result. Those assumptions are still a specialist dump, not a next action.

**Democratization is practice, not a download.** Poclain’s 2025 account of upfront simulation is workshops on real cases plus support, not “push the tool” ([Upfront Simulations and (Their) Democratization](https://doi.org/10.18690/um.fs.7.2025.16)). Commercial products that feel easier (Onshape built-in checks, SimScale in the browser, Fusion simulation, PrePoMax + CalculiX) all start from a *template*: pick a part, reuse a setup, stay inside a stated scope.

**Print-specific FEA is a second cliff.** FDM stiffness is anisotropic and process-dependent. The literature homogenizes an RVE (voids, bead interfaces, periodic boundaries) and then compares to coupons ([e.g. gyroid effective elasticity](https://www.mdpi.com/2076-3417/12/4/2180); [FFF mesostructure homogenization](https://doi.org/10.1007/s40964-025-00970-4)). OpenFEA’s print path is an AABB + illustrative pattern table. That is the right honesty for a first version. It is the wrong thing to present as “how strong will this print be.”

Vendor surveys (wait times, license queues, forced simplification) matter less here: OpenFEA is already local, open-source, and small-mesh. The remaining product problem is *getting through the first real study without an analyst in the room*.

## What OpenFEA already does well

- Confirm-before-solve. No silent GPU→CPU fallback.
- Total face force is traction, not “refine the mesh and double the load.”
- Print and STL warnings stay on the result and in the report.
- Pin-and-compare makes print settings a design question instead of a materials lecture.
- Example coupon is one click away.

## What still makes it specialist-only

- First launch builds a mounting bracket, not the coupon people can finish.
- Local GPU is the default; on machines without WebGPU, **Run** stays disabled until the user finds the CPU option.
- Face IDs, confirmation, and “dirty mesh” are correct and still opaque.
- Results lead with peak von Mises, which is the least trustworthy number on a sharp fixture edge.
- Print settings change stiffness, then ask the user to re-confirm as if the whole setup were new.
- Astra interview cards accumulate even when Astra is offline.

## Implication for the next goal

Make the **first successful local analysis** the product, not another solver feature.

A new user should be able to open OpenFEA, run the example coupon on CPU without hunting for settings, see displacement and mass respond to infill, and read three sentences that say what to trust (trend, residual, mass) and what not to trust (peak stress, printed strength). Astra, hosted Sites, and sketch-to-mesh stay deferred until that path is boringly reliable.

Shipped on `print-stl-workspace` (`56f0faa`). The follow-on problem is the same for a person’s own STL/STEP and for an agent: a machine-readable readiness verdict, recommended faces, and a schema-constrained job API that cannot skip confirm or residual `< 1e-7`. See [AGENT.md](AGENT.md).
