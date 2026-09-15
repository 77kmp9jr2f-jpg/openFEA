import type { Result } from "./types";

export default function ResultGuidance({ result }: { result: Result }) {
  const guidance = result.guidance;
  if (!guidance) return null;
  return (
    <div className="result-guidance">
      <div>
        <h3>Trust these</h3>
        <ul>
          {guidance.trust.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </div>
      <div>
        <h3>Do not treat as printed strength</h3>
        <ul>
          {guidance.caution.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </div>
      <p className="result-guidance-next">{guidance.next}</p>
    </div>
  );
}
