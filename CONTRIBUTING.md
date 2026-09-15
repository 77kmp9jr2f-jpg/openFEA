# Contributing to OpenFEA

This is a local engineering workspace. Changes should keep the solver honest: no silent fallbacks, no model-generated CAD execution, and no claim of physical certification.

## Run

```sh
./scripts/start.sh
```

Development: backend on `127.0.0.1:8000`, frontend on `127.0.0.1:5173`.

## Checks

```sh
.venv/bin/python -m pytest -q tests
npm run build
```

Add tests for numerical or import behavior. A new analysis assumption belongs in the result warnings and in `docs/VALIDATION.md` if you record evidence.

## Scope

- One connected solid, small-strain linear elasticity.
- STL import must stay watertight and single-shell.
- Print settings use the documented homogenized model in `backend/print_model.py` and [docs/PRINT-STL.md](docs/PRINT-STL.md). Do not present that as sliced-toolpath or coupon-calibrated strength unless you add that evidence.
- Astra is optional. Modelling, meshing, solving and exports must work without it.

## Pull requests

Keep each PR focused. Include what you verified and what you did not (GPU, camera, live Astra). Do not add hosted authentication or public binding unless that work is explicitly requested.
