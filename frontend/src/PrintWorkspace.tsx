import type { Material, Model, PrintPreview, PrintSettings } from "./types";
import { format } from "./types";

export default function PrintWorkspace({
  print,
  onChange,
  model,
  material,
  preview,
}: {
  print: PrintSettings;
  onChange: (next: PrintSettings) => void;
  model: Model | null;
  material: Material;
  preview: PrintPreview | null;
}) {
  function patch(partial: Partial<PrintSettings>) {
    onChange({ ...print, ...partial });
  }
  return (
    <div className="print-workspace">
      <div className="print-intro">
        <label className="inline-check">
          <input
            type="checkbox"
            checked={print.enabled}
            onChange={(e) => patch({ enabled: e.target.checked })}
          />{" "}
          Use homogenized print stiffness
        </label>
        <p>
          Orientation, walls, skins and infill change the equivalent solid used
          for this solve. This is not a sliced toolpath and not a printed-coupon
          calibration. Filament properties stay the selected material.
        </p>
      </div>
      <fieldset disabled={!print.enabled} className="print-grid">
        <label>
          Infill pattern
          <select
            aria-label="Infill pattern"
            value={print.infill_pattern}
            onChange={(e) =>
              patch({
                infill_pattern: e.target
                  .value as PrintSettings["infill_pattern"],
              })
            }
          >
            <option value="gyroid">Gyroid</option>
            <option value="grid">Grid</option>
            <option value="triangles">Triangles</option>
            <option value="rectilinear">Rectilinear</option>
          </select>
        </label>
        <Field
          label="Infill density"
          unit="×"
          value={print.infill_density}
          step={0.05}
          onChange={(v) => patch({ infill_density: v })}
        />
        <Field
          label="Wall count"
          unit=""
          value={print.wall_count}
          onChange={(v) => patch({ wall_count: Math.max(1, Math.round(v)) })}
        />
        <Field
          label="Line width"
          unit="mm"
          value={print.line_width_mm}
          step={0.05}
          onChange={(v) => patch({ line_width_mm: v })}
        />
        <Field
          label="Layer height"
          unit="mm"
          value={print.layer_height_mm}
          step={0.05}
          onChange={(v) => patch({ layer_height_mm: v })}
        />
        <Field
          label="Top layers"
          unit=""
          value={print.top_layers}
          onChange={(v) => patch({ top_layers: Math.max(0, Math.round(v)) })}
        />
        <Field
          label="Bottom layers"
          unit=""
          value={print.bottom_layers}
          onChange={(v) => patch({ bottom_layers: Math.max(0, Math.round(v)) })}
        />
        <Field
          label="Rotate X"
          unit="deg"
          value={print.rotation_deg[0]}
          onChange={(v) =>
            patch({ rotation_deg: [v, print.rotation_deg[1], print.rotation_deg[2]] })
          }
        />
        <Field
          label="Rotate Y"
          unit="deg"
          value={print.rotation_deg[1]}
          onChange={(v) =>
            patch({ rotation_deg: [print.rotation_deg[0], v, print.rotation_deg[2]] })
          }
        />
        <Field
          label="Rotate Z"
          unit="deg"
          value={print.rotation_deg[2]}
          onChange={(v) =>
            patch({ rotation_deg: [print.rotation_deg[0], print.rotation_deg[1], v] })
          }
        />
      </fieldset>
      <p className="print-note">
        Rotation orients print Z (layer normal) in global XYZ. The mesh is not
        rebuilt. {material.name} supplies filament E, ν, yield and density.
        {model
          ? ` Solid volume ${format(model.volume_mm3)} mm³.`
          : " Build a model to estimate filament usage."}
      </p>
      {print.enabled && preview && (
        <div className="print-metrics">
          <div>
            <span>Effective E in-plane</span>
            <b>{format(preview.young_xy_mpa)} MPa</b>
          </div>
          <div>
            <span>Effective E layer</span>
            <b>{format(preview.young_z_mpa)} MPa</b>
          </div>
          <div>
            <span>Filament fraction</span>
            <b>{format(preview.volume_fraction)}</b>
          </div>
          <div>
            <span>Estimated filament</span>
            <b>{format(preview.filament_mass_g)} g</b>
          </div>
        </div>
      )}
      {print.enabled && preview && (
        <ul className="print-assumptions">
          {preview.assumptions.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

function Field({
  label,
  unit,
  value,
  onChange,
  step = 1,
}: {
  label: string;
  unit: string;
  value: number;
  onChange: (v: number) => void;
  step?: number;
}) {
  return (
    <label className="number-field">
      <span>{label}</span>
      <div>
        <input
          aria-label={label}
          type="number"
          value={value}
          step={step}
          onChange={(e) => onChange(+e.target.value)}
        />
        {unit ? <small>{unit}</small> : null}
      </div>
    </label>
  );
}
