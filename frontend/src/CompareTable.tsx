import type { RunCompare } from "./types";
import { format } from "./types";

export default function CompareTable({ compare }: { compare: RunCompare }) {
  const { a, b, delta } = compare;
  const rows: [string, string, string, string][] = [
    [
      "Max displacement",
      `${format(a.max_displacement_mm)} mm`,
      `${format(b.max_displacement_mm)} mm`,
      `${signed(delta.max_displacement_mm)} mm`,
    ],
    [
      "Peak von Mises",
      `${format(a.peak_von_mises_mpa)} MPa`,
      `${format(b.peak_von_mises_mpa)} MPa`,
      `${signed(delta.peak_von_mises_mpa)} MPa`,
    ],
    [
      "Filament mass",
      `${format(a.filament_mass_g)} g`,
      `${format(b.filament_mass_g)} g`,
      `${signed(delta.filament_mass_g)} g`,
    ],
    ["Solid fraction", ratio(a.volume_fraction), ratio(b.volume_fraction), "—"],
    ["E in-plane / layer", stiffness(a), stiffness(b), "—"],
    ["Infill", infill(a), infill(b), "—"],
    ["Walls / skins", walls(a), walls(b), "—"],
    ["Print rotation", rotation(a), rotation(b), "—"],
  ];
  return (
    <div className="compare-table-wrap">
      <h3>Print configuration comparison</h3>
      {!compare.same_analysis_context && (
        <p role="alert">
          Other inputs changed: {compare.context_differences.join(", ")}. These
          differences cannot be attributed to print settings alone.
        </p>
      )}
      {compare.same_analysis_context && (
        <p>Same geometry, mesh, material, supports, loads and interpolation.</p>
      )}
      <details>
        <summary>Analysis conditions for both runs</summary>
        {[a, b].map((side) => (
          <div key={side.id}>
            <b>{side.id.slice(0, 8)}</b>
            <p>
              {side.setup?.material.name} · E{" "}
              {format(side.setup?.material.young_mpa ?? NaN)} MPa · fixed faces{" "}
              {side.setup?.fixed_faces.join(", ")}
            </p>
            {side.setup?.loads.map((load, i) => (
              <p key={i}>
                Face {load.face_id}: [{load.vector.join(", ")}] N
              </p>
            ))}
          </div>
        ))}
      </details>
      <table className="compare-table">
        <thead>
          <tr>
            <th>Metric</th>
            <th>Pinned {a.id.slice(0, 8)}</th>
            <th>Current {b.id.slice(0, 8)}</th>
            <th>Δ current − pinned</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(([label, left, right, change]) => (
            <tr key={label}>
              <td>{label}</td>
              <td>{left}</td>
              <td>{right}</td>
              <td>{change}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function signed(value: number) {
  const text = format(Math.abs(value));
  return value > 0 ? `+${text}` : value < 0 ? `−${text}` : text;
}
function ratio(value: number | null) {
  return value == null ? "—" : format(100 * value) + "%";
}
function stiffness(side: RunCompare["a"]) {
  if (side.young_xy_mpa == null || side.young_z_mpa == null) return "Isotropic";
  return `${format(side.young_xy_mpa)} / ${format(side.young_z_mpa)} MPa`;
}
function infill(side: RunCompare["a"]) {
  const print = side.print;
  if (!print?.enabled) return "Print model off";
  return `${print.infill_pattern} · ${format(100 * print.infill_density)}%`;
}
function walls(side: RunCompare["a"]) {
  const print = side.print;
  if (!print?.enabled) return "—";
  return `${print.wall_count} × ${print.line_width_mm} mm; ${print.top_layers}+${print.bottom_layers} × ${print.layer_height_mm} mm`;
}
function rotation(side: RunCompare["a"]) {
  const print = side.print;
  if (!print?.enabled) return "—";
  return print.rotation_deg.map((v) => `${v}°`).join(", ");
}
