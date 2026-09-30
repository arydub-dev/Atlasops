"""AI orchestration — permission-aware, graph-grounded tool pipeline."""
from __future__ import annotations

import re
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import settings
from app.integrations import analytics
from app.services import ai_advisor, graph, metrics, risk_engine, timeline
from app.tenancy.context import get_tenant


TOOLS = {
    "mission_summary": "Mission Summary",
    "executive_report": "Executive Report",
    "root_cause": "Root Cause Analysis",
    "supplier_analysis": "Supplier Analysis",
    "inventory_analysis": "Inventory Analysis",
    "impact_analysis": "Impact Analysis",
    "operational_qa": "Operational Q&A",
    "incident_summary": "Incident Summary",
}


def detect_intent(prompt: str) -> str:
    p = prompt.lower()
    if any(w in p for w in ("root cause", "why did", "rca")):
        return "root_cause"
    if any(w in p for w in ("impact", "downstream", "upstream", "blast radius")):
        return "impact_analysis"
    if any(w in p for w in ("supplier", "vendor")):
        return "supplier_analysis"
    if any(w in p for w in ("inventory", "stock", "warehouse")):
        return "inventory_analysis"
    if any(w in p for w in ("executive", "board", "brief", "morning")):
        return "executive_report"
    if any(w in p for w in ("mission", "situation", "overview")):
        return "mission_summary"
    if any(w in p for w in ("incident",)):
        return "incident_summary"
    return "operational_qa"


def _extract_entity_hint(prompt: str) -> tuple[str | None, str | None]:
    """Best-effort parse of type:uuid or reference-like tokens."""
    m = re.search(
        r"\b(supplier|warehouse|shipment|purchase_order|sales_order|alert|risk):([0-9a-f-]{36})\b",
        prompt,
        re.I,
    )
    if m:
        return m.group(1).lower(), m.group(2)
    return None, None


def build_orchestrated_context(db: Session, prompt: str, intent: str) -> dict[str, Any]:
    """Build retrieval context using the same RBAC gates as dedicated APIs.

    ``ai.chat`` alone must not load mission/network graph or timeline data the
    caller cannot read via ``/mission`` or ``/graph``.
    """
    tenant = get_tenant()
    org_id = tenant.organization_id
    perms = tenant.permissions
    base = ai_advisor.build_context(db)
    base["intent"] = intent
    base["tool"] = TOOLS.get(intent, intent)

    can_mission = "mission.read" in perms
    if can_mission:
        base["timeline"] = timeline.global_timeline(db, org_id, limit=25)
        base["graph_stats"] = graph.graph_stats(db, org_id)

    etype, eid = _extract_entity_hint(prompt)
    if can_mission and etype and eid:
        try:
            uid = UUID(eid)
            base["impact"] = graph.impact_analysis(db, org_id, etype, uid)  # type: ignore[arg-type]
            base["entity_timeline"] = timeline.entity_timeline(
                db, org_id, entity_type=etype, entity_id=uid, limit=30
            )
            base["citations"] = [
                {"type": etype, "id": eid, "source": "graph"},
                *[
                    {"type": "timeline_event", "id": t["id"], "source": t["source"]}
                    for t in base["entity_timeline"][:5]
                ],
            ]
        except ValueError:
            base["citations"] = []
    else:
        # Cite top risks / alerts already filtered by ai_advisor RBAC
        base["citations"] = [
            {"type": "risk", "id": r.get("title"), "source": "risk_engine"}
            for r in (base.get("top_risks") or [])[:3]
        ] + [
            {"type": "alert", "id": a.get("title"), "source": "alerts"}
            for a in (base.get("open_alerts") or [])[:3]
        ]

    base["confidence"] = None  # No calibrated confidence model exists.
    return base


# Cap prompt size to limit prompt-injection / DoS surface into the model.
_MAX_ORCHESTRATE_PROMPT_CHARS = 8_000


def orchestrate(db: Session, prompt: str, *, user_id: str | None = None) -> dict[str, Any]:
    """Full pipeline: intent → retrieval → LLM/local → grounded response."""
    if len(prompt or "") > _MAX_ORCHESTRATE_PROMPT_CHARS:
        prompt = (prompt or "")[:_MAX_ORCHESTRATE_PROMPT_CHARS]
    intent = detect_intent(prompt)
    context = build_orchestrated_context(db, prompt, intent)

    # Specialize prompt for tools
    tool_prompt = prompt
    if intent == "mission_summary":
        tool_prompt = (
            "Produce a concise Mission Control situation summary with top risks, "
            "delayed shipments, inventory pressure, and recommended actions. "
            f"Operator question: {prompt}"
        )
    elif intent == "executive_report":
        tool_prompt = (
            "Write an executive briefing suitable for leadership. Include health, "
            f"KPIs, risks, and asks. Operator request: {prompt}"
        )
    elif intent == "root_cause":
        tool_prompt = (
            "Perform root-cause analysis using timeline and risk signals. "
            f"State only facts present in context. Question: {prompt}"
        )
    elif intent == "impact_analysis":
        tool_prompt = (
            "Explain operational impact using graph neighborhood stats. "
            f"Question: {prompt}"
        )

    text, model, _ = ai_advisor.answer(db, tool_prompt, context=context)

    # Grounding footer
    cites = context.get("citations") or []
    if cites:
        cite_lines = "; ".join(
            f"{c.get('type')}:{c.get('id')}" for c in cites[:8] if c.get("id")
        )
        text = f"{text}\n\n---\n**Grounding:** {cite_lines}\n**Confidence:** Not calibrated; verify recommendations."

    if user_id:
        analytics.capture(
            distinct_id=user_id,
            event="ai_orchestrate",
            properties={"intent": intent, "model": model},
        )

    return {
        "response": text,
        "model": model,
        "intent": intent,
        "tool": TOOLS.get(intent, intent),
        "confidence": context.get("confidence"),
        "citations": cites,
        "context": {
            "kpis": context.get("kpis"),
            "risk": context.get("risk"),
            "graph_stats": context.get("graph_stats"),
            "timeline_count": len(context.get("timeline") or []),
            "impact_summary": (context.get("impact") or {}).get("impact", {}).get("summary"),
        },
    }
