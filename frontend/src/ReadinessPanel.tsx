import type { Readiness } from "./types";

export default function ReadinessPanel({
  readiness,
  onApplyRecommended,
}: {
  readiness: Readiness;
  onApplyRecommended?: () => void;
}) {
  const showApply =
    !!onApplyRecommended &&
    (readiness.missing.includes("fixture") || readiness.missing.includes("load"));
  const tone =
    readiness.status === "ready"
      ? "ready"
      : readiness.status === "blocked"
        ? "blocked"
        : "incomplete";
  return (
    <section className={`readiness readiness-${tone}`} aria-live="polite">
      <div className="readiness-head">
        <h3>
          {readiness.status === "ready"
            ? "Ready to solve"
            : readiness.status === "blocked"
              ? "This solid is not ready"
              : "Finish the setup"}
        </h3>
        <p>{readiness.next}</p>
      </div>
      <ul className="readiness-checks">
        {readiness.checks.map((item) => (
          <li key={item.id} data-ok={item.ok}>
            <b>{labelFor(item.id)}</b>
            <span>{item.detail}</span>
          </li>
        ))}
      </ul>
      {showApply && (
        <button className="outline-button" type="button" onClick={onApplyRecommended}>
          Use recommended fixture and load
        </button>
      )}
    </section>
  );
}

function labelFor(id: Readiness["checks"][number]["id"]): string {
  switch (id) {
    case "mesh_usable":
      return "Mesh";
    case "faces_selectable":
      return "Faces";
    case "print_geometry":
      return "Print contours";
    case "fixture":
      return "Fixture";
    case "load":
      return "Load";
    case "material":
      return "Material";
    case "confirm":
      return "Confirm";
    case "scope":
      return "Scope";
    default: {
      const never: never = id;
      return never;
    }
  }
}
