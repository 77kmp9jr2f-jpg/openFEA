// Retained diagnostic probe, not a React/browser test runner. See workspace-races.json.
// Run from an installed checkout: node evidence/workspace-race-probe.cjs
const fs = require("fs");
const path = require("path");
const os = require("os");
const crypto = require("crypto");
const esbuild = require("esbuild");
const root = path.resolve(__dirname, "..");
const out = fs.mkdtempSync(
  path.join(os.tmpdir(), "openfea-workspace-races-fixed-"),
);
(async () => {
  const app = path.join(root, "frontend/src/App.tsx");
  const source = fs.readFileSync(app, "utf8");
  const icons = source
    .match(/import \{([\s\S]*?)\} from "lucide-react"/)[1]
    .replace(/^[\s\S]*?\nimport \{/, "")
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean)
    .map((s) => s.split(/\s+as\s+/)[0]);
  await esbuild.build({
    entryPoints: [app],
    bundle: true,
    platform: "node",
    format: "cjs",
    jsx: "automatic",
    outfile: path.join(out, "app.cjs"),
    plugins: [
      {
        name: "harness",
        setup(b) {
          b.onResolve(
            {
              filter:
                /^(react|react\/jsx-runtime|lucide-react|\.\/(Viewport|ImageReview|SetupProposalCard|PrintWorkspace|CompareTable|ResultGuidance|ReadinessPanel|gpu))$/,
            },
            (a) => ({ path: a.path, namespace: "stub" }),
          );
          b.onLoad({ filter: /.*/, namespace: "stub" }, (a) => ({
            contents:
              a.path === "react"
                ? `export const useState=(...a)=>globalThis.hooks.useState(...a); export const useRef=(...a)=>globalThis.hooks.useRef(...a); export const useEffect=(...a)=>globalThis.hooks.useEffect(...a);`
                : a.path === "react/jsx-runtime"
                  ? `export const Fragment='fragment'; export function jsx(type,props){return {type,props}} export const jsxs=jsx;`
                  : a.path === "lucide-react"
                    ? icons.map((n) => `export const ${n}='${n}';`).join("\n")
                    : a.path === "./gpu"
                      ? `export const gpuCapability=async()=>({available:true,device:'test'});export const solveGPU=async()=>{throw Error('unused')};`
                      : `export default function Stub(){return null}`,
            loader: "js",
          }));
          b.onLoad({ filter: /App\.tsx$/ }, () => ({
            contents: source.replace(
              '  return (\n    <div className="app-shell">',
              '  globalThis.review={restore,openLibrary,ask,solve,snapshot,state:{busy,aiBusy,compare,ready,workspaceRevision,confirmed,compute,error,status},setTab};\n  return (\n    <div className="app-shell">',
            ),
            loader: "tsx",
            resolveDir: path.dirname(app),
          }));
        },
      },
    ],
  });
  const App = require(path.join(out, "app.cjs")).default;
  const deferred = () => {
    let resolve, reject;
    const promise = new Promise((r, j) => {
      resolve = r;
      reject = j;
    });
    return { promise, resolve, reject };
  };
  const spec = {
    name: "Base",
    kind: "plate",
    length: 40,
    width: 20,
    height: 10,
    thickness: 10,
    hole_diameter: 0,
    mesh_size: 8,
    features: [],
    assumptions: [],
    provenance: "user_dimensions",
    step_id: null,
    stl_id: null,
    unit_scale: 1,
    feature_angle_deg: 40,
    accept_stl_preprocessing: false,
  };
  const material = {
    name: "M",
    young_mpa: 1000,
    poisson: 0.3,
    yield_mpa: 40,
    density_kg_m3: 1000,
  };
  const print = {
    enabled: false,
    rotation_deg: [0, 0, 0],
    infill_density: 0.2,
    infill_pattern: "grid",
    wall_count: 2,
    line_width_mm: 0.4,
    layer_height_mm: 0.2,
    top_layers: 3,
    bottom_layers: 3,
  };
  const model = (id, name) => ({
    id,
    spec: { ...spec, name },
    nodes: [],
    faces: [],
    tetrahedra: 10,
    recommended: { fixed_face: 1, load_face: 2 },
    bounds: [
      [0, 0, 0],
      [40, 20, 10],
    ],
  });
  const saved = (id, name, extra = {}) => ({
    spec: { ...spec, name },
    modelId: id,
    material,
    fixed: [],
    loads: [],
    image: null,
    marks: [],
    messages: [{ role: "user", text: name }],
    notes: name,
    print,
    ...extra,
  });
  function harness(savedSnapshot, route) {
    let cursor = 0,
      cells = [],
      effects = [],
      pendingEffects = [],
      tree;
    global.hooks = {
      useState(initial) {
        const i = cursor++;
        if (!(i in cells))
          cells[i] = typeof initial === "function" ? initial() : initial;
        return [
          cells[i],
          (value) =>
            (cells[i] = typeof value === "function" ? value(cells[i]) : value),
        ];
      },
      useRef(value) {
        const i = cursor++;
        if (!(i in cells)) cells[i] = { current: value };
        return cells[i];
      },
      useEffect(fn, deps) {
        const i = cursor++;
        const old = effects[i];
        if (!old || deps.some((x, j) => !Object.is(x, old.deps[j]))) {
          pendingEffects.push(() => {
            old?.cleanup?.();
            effects[i] = { deps, cleanup: fn() };
          });
        }
      },
    };
    global.localStorage = {
      getItem: (k) =>
        k === "openfea-current" && savedSnapshot
          ? JSON.stringify(savedSnapshot)
          : null,
      setItem() {},
      removeItem() {},
    };
    global.fetch = async (url, options) => {
      const value = await route(String(url), options);
      return value instanceof Response ? value : Response.json(value);
    };
    const render = () => {
      cursor = 0;
      tree = App();
      const fx = pendingEffects;
      pendingEffects = [];
      for (const f of fx) f();
      return tree;
    };
    const tick = async () => {
      await new Promise((r) => setImmediate(r));
      render();
      await new Promise((r) => setImmediate(r));
      render();
    };
    const walk = (node, predicate) => {
      if (!node) return;
      if (Array.isArray(node)) {
        for (const n of node) {
          const r = walk(n, predicate);
          if (r) return r;
        }
      } else if (typeof node === "object") {
        if (predicate(node)) return node;
        return walk(node.props?.children, predicate);
      }
    };
    const text = (n) =>
      n == null
        ? ""
        : Array.isArray(n)
          ? n.map(text).join("")
          : typeof n === "object"
            ? text(n.props?.children)
            : String(n);
    return {
      render,
      tick,
      find: (p) => walk(tree, p),
      button: (label) =>
        walk(tree, (n) => n.type === "button" && text(n).includes(label)),
      close() {
        for (const e of effects) e?.cleanup?.();
      },
    };
  }
  const common = (url) =>
    url === "/api/health"
      ? { assistant: { available: true } }
      : url === "/api/studies"
        ? [{ id: "studyB", name: "Study B", updated_at: 0 }]
        : url === "/api/print-preview"
          ? {}
          : url.startsWith("/api/readiness")
            ? {
                model: { id: "FIRST" },
                can_solve: false,
                recommended: { fixed_faces: [], loads: [] },
              }
            : undefined;

  let results = {
    source_sha256: crypto.createHash("sha256").update(source).digest("hex"),
    before_evidence: path.join(root, "evidence/workspace-races.json"),
  };
  async function clickStudy(h) {
    const open = h.find(
      (n) => n.type === "button" && n.props["aria-label"] === "Saved studies",
    );
    if (open.props.disabled) return false;
    await open.props.onClick();
    h.render();
    const row = h.find((n) => n.props?.className === "library-row");
    if (!row || row.props.disabled) return false;
    await row.props.onClick();
    await h.tick();
    return true;
  }
  {
    const old = deferred();
    const h = harness(saved("A", "Autosave A"), (url) =>
      url === "/api/models/A"
        ? old.promise
        : url === "/api/models/B"
          ? model("B", "Study B")
          : url === "/api/studies/studyB"
            ? { state: saved("B", "Study B") }
            : common(url),
    );
    h.render();
    await h.tick();
    const pendingBusy = review.state.busy;
    const blocked = !(await clickStudy(h));
    const unchanged = review.snapshot().spec.name;
    old.resolve(model("A", "Autosave A"));
    await h.tick();
    const afterStartup = review.snapshot().spec.name;
    const busyAfterStartup = review.state.busy;
    const laterRestore = await clickStudy(h);
    results.startup = {
      pendingBusy,
      libraryBlocked: blocked,
      pendingSpec: unchanged,
      afterStartup,
      busyAfterStartup,
      laterRestore,
      afterLaterRestore: review.snapshot().spec.name,
      workspaceRevision: review.state.workspaceRevision,
    };
    h.close();
  }
  {
    const coupon = deferred();
    const h = harness(saved("A", "Study A"), (url) =>
      url === "/api/models/A"
        ? model("A", "Study A")
        : url === "/api/models/B"
          ? model("B", "Study B")
          : url === "/api/studies/studyB"
            ? { state: saved("B", "Study B") }
            : url === "/print-coupon.stl"
              ? coupon.promise
              : url === "/api/stls"
                ? {
                    id: "newstl",
                    watertight: true,
                    triangles: 12,
                    shells: 1,
                    extent_mm: [40, 20, 10],
                    warnings: [],
                  }
                : common(url),
    );
    h.render();
    await h.tick();
    const couponPending = h.button("Use example print coupon").props.onClick();
    h.render();
    const pendingBusy = review.state.busy;
    const blocked = !(await clickStudy(h));
    coupon.resolve(new Response("mock stl"));
    await couponPending;
    await h.tick();
    const afterCoupon = review.snapshot().spec.name;
    const busyAfterCoupon = review.state.busy;
    const laterRestore = await clickStudy(h);
    results.coupon = {
      pendingBusy,
      libraryBlocked: blocked,
      afterCoupon,
      busyAfterCoupon,
      laterRestore,
      afterLaterRestore: review.snapshot().spec.name,
    };
    h.close();
  }
  for (const oldOutcome of ["success", "error"]) {
    const old = deferred();
    const run = (id, mid) => ({ id, model_id: mid, print: { enabled: false } });
    const a = saved("A", "Study A", { resultId: "A2", pinnedId: "A1" });
    const b = saved("B", "Study B", { resultId: "B2", pinnedId: "B1" });
    const h = harness(a, (url) =>
      url === "/api/models/A"
        ? model("A", "Study A")
        : url === "/api/models/B"
          ? model("B", "Study B")
          : url === "/api/runs/A1/compare/A2"
            ? old.promise
            : url === "/api/runs/B1/compare/B2"
              ? { a: { id: "B1" }, b: { id: "B2" } }
              : url.startsWith("/api/runs/")
                ? run(url.split("/").at(-1), url.includes("/A") ? "A" : "B")
                : url === "/api/studies/studyB"
                  ? { state: b }
                  : common(url),
    );
    h.render();
    await h.tick();
    await clickStudy(h);
    const correct = review.state.compare;
    if (oldOutcome === "success")
      old.resolve({ a: { id: "A1" }, b: { id: "A2" } });
    else old.reject(new Error("old compare failed"));
    await h.tick();
    results["comparison_" + oldOutcome] = {
      currentStudy: review.snapshot().spec.name,
      currentResult: review.snapshot().resultId,
      correctPair: correct,
      afterOldResponse: review.state.compare,
    };
    h.close();
  }
  {
    const h = harness(null, (url, options) =>
      url === "/print-coupon.stl"
        ? new Response("mock stl")
        : url === "/api/stls"
          ? {
              id: "firststl",
              watertight: true,
              triangles: 12,
              shells: 1,
              extent_mm: [40, 20, 10],
              warnings: [],
            }
          : url === "/api/models"
            ? { id: "firstjob" }
            : url === "/api/jobs/firstjob"
              ? { status: "complete", result: model("FIRST", "First coupon") }
              : common(url),
    );
    h.render();
    await h.tick();
    const pending = review.state.busy;
    await new Promise((r) => setTimeout(r, 1000));
    await h.tick();
    results.first_launch = {
      pending,
      busy: review.state.busy,
      ready: review.state.ready,
      model: review.snapshot().modelId,
      confirmed: review.state.confirmed,
      compute: review.state.compute,
      messages: review.snapshot().messages.map((m) => m.text),
    };
    h.close();
  }
  {
    const h = harness(saved("A", "Autosave A"), (url) =>
      url === "/api/health"
        ? Promise.reject(new Error("offline"))
        : url === "/api/models/B"
          ? model("B", "Study B")
          : url === "/api/studies/studyB"
            ? { state: saved("B", "Study B") }
            : common(url),
    );
    h.render();
    await h.tick();
    const failed = {
      busy: review.state.busy,
      ready: review.state.ready,
      error: review.state.error,
    };
    const laterRestore = await clickStudy(h);
    results.startup_failure = {
      failed,
      laterRestore,
      afterRecovery: review.snapshot().spec.name,
      ready: review.state.ready,
    };
    h.close();
  }
  fs.writeFileSync(
    path.join(out, "results.json"),
    JSON.stringify(results, null, 2),
  );
  fs.writeFileSync(path.join(out, "App.tsx"), source);
  console.log(JSON.stringify(results, null, 2));
  console.log("PROBE_DIR", out);
})().catch((e) => {
  console.error(e);
  process.exitCode = 1;
});
