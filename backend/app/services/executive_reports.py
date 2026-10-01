"""Executive report generation — graph + analytics + AI."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.services import ai_orchestration, graph, insights, metrics, risk_engine, timeline


REPORT_KINDS = {
    "morning_brief": "Morning Brief",
    "operations": "Operations Report",
    "risk": "Risk Report",
    "supplier": "Supplier Report",
    "executive": "Executive Summary",
    "weekly": "Weekly Overview",
    "monthly": "Monthly KPIs",
}


def generate_report(db: Session, org_id: UUID, kind: str) -> dict[str, Any]:
    kind = kind if kind in REPORT_KINDS else "executive"
    kpis = metrics.compute_kpis(db, org_id)
    risk = risk_engine.summarize(db)
    health = insights.health_score(kpis, risk["overall_score"])
    tl = timeline.global_timeline(db, org_id, limit=20)
    gstats = graph.graph_stats(db, org_id)

    prompt = (
        f"Generate a {REPORT_KINDS[kind]} for ATLASOPS leadership. "
        f"Health grade {health.get('grade')} score {health.get('score')}. "
        f"Use only provided operational context. Keep it actionable."
    )
    orch = ai_orchestration.orchestrate(db, prompt)

    return {
        "kind": kind,
        "title": REPORT_KINDS[kind],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "health": health,
        "kpis": kpis,
        "risk": {
            "overall_score": risk["overall_score"],
            "counts": risk["counts"],
            "top_risks": [
                {
                    "title": r.title,
                    "score": r.score,
                    "level": r.level.value if hasattr(r.level, "value") else str(r.level),
                }
                for r in risk["top_risks"][:5]
            ],
        },
        "graph": gstats,
        "timeline": tl[:10],
        "narrative": orch["response"],
        "model": orch["model"],
        "confidence": orch["confidence"],
        "citations": orch["citations"],
    }
