import { ArrowRight, Check } from "lucide-react";
import { Link } from "react-router-dom";

import type { RouteStep } from "@/api/types";

/** The planner's route: the topic the learner is in, then up to three topics ahead, each linking to its lesson. */
export function RouteLine({ route }: { route?: RouteStep[] }) {
  if (!route || route.length < 2) return null;
  return (
    <nav aria-label="Your route" data-testid="route">
      <p className="field-label" style={{ marginBottom: 4 }}>Your route</p>
      <ol className="route-line">
        {route.map((step, index) => (
          <li key={step.unit_id} data-status={step.status}>
            {index > 0 && <ArrowRight size={13} className="route-arrow" aria-hidden />}
            <Link to={`/path/${step.unit_id}?tab=lesson`} className="route-step">
              {step.status === "secure" && <Check size={13} aria-hidden />}
              <span>{step.title}</span>
              <span className="subtle">
                {step.status === "secure" ? " secure" : step.status === "now" ? ` ${step.solved}/${step.total}` : ""}
              </span>
            </Link>
          </li>
        ))}
      </ol>
    </nav>
  );
}
