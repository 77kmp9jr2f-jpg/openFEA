export type Vec3 = [number, number, number];
export type Feature = {
  operation: "add" | "cut";
  primitive: "box" | "cylinder";
  origin: Vec3;
  size: Vec3;
  axis: Vec3;
  radius: number;
};
export type PrintSettings = {
  enabled: boolean;
  rotation_deg: Vec3;
  infill_pattern: "rectilinear" | "grid" | "triangles" | "gyroid";
  infill_density: number;
  wall_count: number;
  line_width_mm: number;
  layer_height_mm: number;
  top_layers: number;
  bottom_layers: number;
};
export const defaultPrint: PrintSettings = {
  enabled: false,
  rotation_deg: [0, 0, 0],
  infill_pattern: "gyroid",
  infill_density: 0.2,
  wall_count: 3,
  line_width_mm: 0.4,
  layer_height_mm: 0.2,
  top_layers: 4,
  bottom_layers: 4,
};
export type PrintPreview = {
  enabled: boolean;
  volume_fraction: number;
  young_xy_mpa: number;
  young_z_mpa: number;
  filament_volume_mm3: number;
  filament_mass_g: number;
  assumptions: string[];
  settings: PrintSettings;
};
export type StlInspect = {
  id: string;
  name: string;
  triangles: number;
  bounds: [Vec3, Vec3];
  extent_mm: Vec3;
  surface_area_mm2: number;
  signed_volume_mm3: number;
  watertight: boolean;
  shells: number;
  boundary_edges: number;
  nonmanifold_edges: number;
  degenerate_triangles: number;
  suggested_scale: number;
  warnings: string[];
};
export type Geometry = {
  name: string;
  kind: "bracket" | "plate" | "shaft" | "custom" | "step" | "stl";
  length: number;
  width: number;
  height: number;
  thickness: number;
  hole_diameter: number;
  mesh_size: number;
  features: Feature[];
  step_id: string | null;
  stl_id: string | null;
  unit_scale: number;
  feature_angle_deg: number;
  provenance: string;
  assumptions: string[];
};
export type Face = {
  id: number;
  label: string;
  kind: string;
  center: Vec3;
  area_mm2: number;
  triangles: number[][];
};
export type Model = {
  id: string;
  spec: Geometry;
  nodes: Vec3[];
  tetrahedra: number;
  faces: Face[];
  volume_mm3: number;
  bounds: [Vec3, Vec3];
  min_quality: number;
  recommended: { fixed_face: number; load_face: number };
  sha256: string;
  seconds: number;
};
export type Material = {
  name: string;
  young_mpa: number;
  poisson: number;
  yield_mpa: number;
  density_kg_m3: number;
};
export type Load = { face_id: number; vector: Vec3 };
export type Result = {
  execution?: {
    backend: "cpu" | "webgpu";
    device: string;
    precision: string;
    iterations: number;
    refinements: number;
  };
  id: string;
  model_id: string;
  nodes: number;
  elements: number;
  dofs: number;
  peak_von_mises_mpa: number;
  max_displacement_mm: number;
  max_display_stress_mpa: number;
  yield_ratio: number;
  force_balance_error_n: number;
  moment_balance_error_nmm: number;
  relative_residual: number;
  reaction_n: Vec3;
  applied_n: Vec3;
  seconds: number;
  mass_g: number;
  warnings: string[];
  displacement: Vec3[];
  nodal_stress_mpa: number[];
  setup: { material: Material; print?: PrintSettings };
  print?: PrintPreview & { mass_g?: number };
};
export type CompareSide = {
  id: string;
  model_id: string;
  max_displacement_mm: number;
  peak_von_mises_mpa: number;
  mass_g: number;
  filament_mass_g: number;
  volume_fraction: number | null;
  young_xy_mpa: number | null;
  young_z_mpa: number | null;
  print?: PrintSettings | null;
};
export type RunCompare = {
  same_model: boolean;
  a: CompareSide;
  b: CompareSide;
  delta: {
    max_displacement_mm: number;
    peak_von_mises_mpa: number;
    mass_g: number;
    filament_mass_g: number;
  };
};
export type Mark = {
  id: string;
  tool: "arrow" | "rectangle" | "note" | "dimension";
  start: [number, number];
  end: [number, number];
  text: string;
};
export type ReferenceImage = {
  id: string;
  name: string;
  width: number;
  height: number;
  url: string;
};
export type SimulationContext = {
  model_id: string;
  geometry: Geometry;
  material: Material;
  fixed_faces: number[];
  loads: Load[];
  notes: string;
  reference_id: string | null;
  annotations: Mark[];
};
export type SimulationProposal = {
  id: string;
  model_id: string;
  source_context: SimulationContext;
  source_hash: string;
  material: Material;
  fixed_faces: number[];
  loads: Load[];
  notes: string;
  assumptions: string[];
};
export type AppliedSetup = {
  model_id: string;
  material: Material;
  fixed_faces: number[];
  loads: Load[];
  notes: string;
  setup_proposal_id: string;
  confirmed: false;
};
export function contextKey(value: unknown): string {
  return JSON.stringify(value, (_key, item) =>
    item && typeof item === "object" && !Array.isArray(item)
      ? Object.fromEntries(
          Object.keys(item)
            .sort()
            .map((key) => [key, item[key]]),
        )
      : item,
  );
}
export type Message = {
  role: "assistant" | "user";
  text: string;
  questions?: string[];
  proposal?: Geometry;
  simulation_proposal?: SimulationProposal;
  interviewFor?: string;
  live?: boolean;
};
export const demoGeometry: Geometry = {
  name: "Mounting bracket",
  kind: "bracket",
  length: 80,
  width: 40,
  height: 60,
  thickness: 8,
  hole_diameter: 8,
  mesh_size: 7,
  features: [],
  step_id: null,
  stl_id: null,
  unit_scale: 1,
  feature_angle_deg: 40,
  provenance: "demo",
  assumptions: [
    "Demonstration dimensions; not derived from a photograph.",
    "Unfilleted bracket; stress at the sharp internal corner is mesh-dependent.",
  ],
};
export const materials: Material[] = [
  {
    name: "Aluminum · illustrative",
    young_mpa: 69000,
    poisson: 0.33,
    yield_mpa: 240,
    density_kg_m3: 2700,
  },
  {
    name: "Steel · illustrative",
    young_mpa: 200000,
    poisson: 0.3,
    yield_mpa: 250,
    density_kg_m3: 7850,
  },
  {
    name: "Polymer · isotropic estimate",
    young_mpa: 2500,
    poisson: 0.35,
    yield_mpa: 40,
    density_kg_m3: 1250,
  },
  {
    name: "PLA · illustrative filament",
    young_mpa: 3500,
    poisson: 0.35,
    yield_mpa: 40,
    density_kg_m3: 1240,
  },
  {
    name: "PETG · illustrative filament",
    young_mpa: 2100,
    poisson: 0.38,
    yield_mpa: 50,
    density_kg_m3: 1270,
  },
];
export async function api<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(
    "/api" + path,
    body === undefined
      ? {}
      : {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        },
  );
  if (!res.ok) {
    const e = await res
      .json()
      .catch(() => ({ detail: "The local server did not respond." }));
    throw new Error(
      typeof e.detail === "string"
        ? e.detail
        : Array.isArray(e.detail)
          ? e.detail.map((v: { msg: string }) => v.msg).join(" ")
          : "Request failed.",
    );
  }
  return res.json();
}
let activeJob: string | null = null;
export async function job<T>(
  path: string,
  body: unknown,
  onStatus?: (status: string) => void,
): Promise<T> {
  const { id } = await api<{ id: string }>(path, body);
  activeJob = id;
  try {
    for (let i = 0; i < 300; i++) {
      await new Promise((r) => setTimeout(r, 900));
      const j = await api<{
        status: string;
        error?: string;
        result: T;
      }>("/jobs/" + id);
      onStatus?.(j.status);
      if (j.status === "cancelled")
        throw new Error(j.error || "The job was cancelled.");
      if (j.status === "failed") throw new Error(j.error);
      if (j.status === "complete") return j.result;
    }
    throw new Error(
      "The job is taking longer than expected. Reload to reconnect.",
    );
  } finally {
    if (activeJob === id) activeJob = null;
  }
}
export async function cancelJob() {
  if (!activeJob) return;
  await api("/jobs/" + activeJob + "/cancel", {});
}
export const format = (value: number, digits = 3) =>
  Number.isFinite(value)
    ? value.toLocaleString("en-US", { maximumSignificantDigits: digits })
    : "—";
