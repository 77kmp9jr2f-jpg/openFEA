import { CheckCircle2, Eye, Settings2 } from "lucide-react";
import { format, type Model, type SimulationProposal } from "./types";

export default function SetupProposalCard({
  proposal,
  model,
  current,
  applied,
  busy,
  preview,
  apply,
}: {
  proposal: SimulationProposal;
  model: Model | null;
  current: boolean;
  applied: boolean;
  busy: boolean;
  preview: () => void;
  apply: () => void;
}) {
  const faceLabel = (id: number) =>
    model?.id === proposal.model_id
      ? `Face ${id} · ${model.faces.find((face) => face.id === id)?.label || "unknown"}`
      : `Face ${id} · earlier revision`;
  const material = proposal.material;
  return (
    <div className="proposal-card simulation-proposal">
      <div>
        <Settings2 size={16} />
        <b>Simulation proposal</b>
      </div>
      <span className="proposal-revision">
        Model revision {proposal.model_id.slice(0, 8)}
      </span>
      <strong>{material.name}</strong>
      <p>
        E {format(material.young_mpa)} MPa · ν {material.poisson}
        <br />
        Yield {format(material.yield_mpa)} MPa · ρ{" "}
        {format(material.density_kg_m3)} kg/m³
      </p>
      <div className="proposal-condition">
        <b>Fully fixed · XYZ</b>
        {proposal.fixed_faces.map((id) => (
          <p key={id}>{faceLabel(id)}</p>
        ))}
      </div>
      <div className="proposal-condition">
        <b>Total face forces · global axes</b>
        {proposal.loads.map((load, i) => (
          <p key={i}>
            {faceLabel(load.face_id)}
            <br />
            <strong>
              [{load.vector.map((v) => format(v, 6)).join(", ")}] N
            </strong>
            <br />
            {format(Math.hypot(...load.vector))} N uniformly distributed
          </p>
        ))}
      </div>
      <details>
        <summary>Application & assumptions</summary>
        <p>{proposal.notes}</p>
        <ul>
          {proposal.assumptions.map((assumption, i) => (
            <li key={i}>{assumption}</li>
          ))}
        </ul>
      </details>
      {applied ? (
        <p className="proposal-applied">
          <CheckCircle2 size={14} /> Applied · review before solving
        </p>
      ) : !current ? (
        <p className="proposal-stale">
          Inputs changed. Ask Astra to refresh this proposal.
        </p>
      ) : (
        <p>Replaces the complete material, fixture and force setup.</p>
      )}
      <div className="proposal-actions">
        <button
          className="outline-button"
          disabled={busy || !current || applied}
          onClick={preview}
        >
          <Eye size={14} /> Preview on model
        </button>
        <button
          className="primary small"
          disabled={busy || !current || applied}
          onClick={apply}
        >
          Apply to simulation
        </button>
      </div>
    </div>
  );
}
