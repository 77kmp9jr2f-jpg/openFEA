# OpenFEA integration acceptance — September 20, 2026

Source: `1a6e8d7` (subsequent research and evidence commits change documentation only).

- `print-proposal.png`: actual browser preview of the live Astra proposal before application, including print axes, fixed end and total force.
- `restored-comparison.png`: actual saved-study reload comparing 20% and 35% gyroid with equal geometry, material, loads, supports and rotation.
- `gpu-verification.json`: actual Apple WebGPU execution, CPU parity and independently executed archive reproduction. This known synthetic coupon does not establish physical print accuracy.
- `gpu-print-report.pdf`, `.html`, `.zip`: freshly exported immutable GPU run. All four PDF pages were rendered and visually inspected. Archive hashes were checked after final report formatting. No STEP is invented for STL input.
- `report-page-*.png`: the inspected PDF raster pages. Screenshot JPEG bytes were transcoded to PNG without editing their page contents.

Saved visual review: [514b555beb024e83b7955783e44a31dc](http://127.0.0.1:8850/reviews/?id=514b555beb024e83b7955783e44a31dc). [All reviews](http://127.0.0.1:8850/reviews/). All three frames were inspected on the exact saved review page. Human review remains open.

Automated evidence: 76 backend tests, five frontend regression tests and TypeScript/Vite build passed. Report/STL/proposal checks were rerun after the final report wording and layout corrections. Two dependency deprecations and the existing bundle-size advisory remain; remote Linux CI is pending a new authorized push.
