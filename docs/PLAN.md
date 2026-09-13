# FEA-R working prototype

Build a local, open-source engineering workspace for general 3D mechanical parts. Astra is the named AI assistant and a separately authenticated proprietary service; modelling, meshing, solving and exports also work without it.

Completion gates:
- Image upload/camera capture, persistent arrows, boxes, notes and dimensions.
- A live Astra image/specification conversation with explicit missing questions and a reviewable CAD proposal.
- Parametric brackets, plates and shafts, additive/subtractive box/cylinder recipes, and single-solid STEP import; no promise of arbitrary photo reconstruction.
- Real OpenCASCADE solids and Gmsh tetrahedral meshes, exportable STEP/STL/MSH.
- Select model faces, apply global XYZ forces and fixed supports, choose material, run quadratic 3D linear-elastic FEA.
- Run the actual sparse system on the user’s hardware GPU via WebGPU, independently verify it and provide an explicit CPU reference option.
- Document a concrete ChatGPT Sites publishing path without assuming native Python runs in a Worker.
- Display stress, displacement and exaggerated deformation, plus reaction/residual checks and assumptions.
- Export a reproducible report and documentation bundle; preserve immutable geometry and simulation IDs.
- Verify numerical results against analytic tension and bending cases, test failure gates and browser interaction, inspect current evidence in a saved visual review, commit locally.

Currently implemented analysis scope: one connected homogeneous isotropic solid; small-strain static elasticity. No assemblies/contact, plasticity, buckling, fatigue, transient loads or certified material data. Photographic proposals are unmeasured until the user supplies/accepts specifications.

## Outstanding requested scope at the September 13 checkpoint

- Finish browser verification of the conversational proposal through apply, confirmation, GPU solve, saved-study reload and a fresh report/review. Automated proposal and archive-reproduction checks pass; see `VALIDATION.md` for the exact evidence boundary.
- Add a dedicated 3D-printing section accepting STL input and addressing infill, print orientation, walls and related print settings. STL import and print-specific mechanical modelling are not implemented in this checkpoint. Their effect on results must be supported by an explicit model and verification, rather than presented as certified printed-part strength.
- Evaluate current image-generation/image-to-3D tools for the sketch-to-mesh step in the separately requested research task. Creation of that task was rejected by automatic approval review because of an account usage limit; it was not created and this research remains pending.
- Keep ChatGPT Sites publishing at the planning stage. Push and deployment require explicit user authorization.
