"""AI Operations Advisor.

Builds a structured context snapshot from live application data and answers
operational questions. Uses the OpenAI API when an API key is configured;
otherwise falls back to a deterministic, rule-based "local engine" so the
feature works fully offline for demos and CI.
"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Alert, RiskAssessment, Supplier, Warehouse
from app.models.enums import AlertStatus, RiskLevel
from app.services import ingestion, metrics, risk_engine


def build_context(db: Session) -> dict:
    kpis = metrics.compute_kpis(db)
    risk = risk_engine.summarize(db)

    worst_suppliers = db.scalars(
        select(Supplier).order_by(Supplier.supplier_score.asc()).limit(5)
    ).all()
    busiest_warehouses = db.scalars(
        select(Warehouse).order_by((Warehouse.current_inventory * 1.0 / Warehouse.capacity).desc()).limit(5)
    ).all()
    open_alerts = db.scalars(
        select(Alert).where(Alert.status != AlertStatus.RESOLVED).order_by(Alert.created_at.desc()).limit(8)
    ).all()

    return {
        "kpis": kpis,
        "risk": {
            "overall_score": risk["overall_score"],
            "overall_level": risk["overall_level"].value if isinstance(risk["overall_level"], RiskLevel) else risk["overall_level"],
            "by_category": risk["by_category"],
            "counts": risk["counts"],
        },
        "worst_suppliers": [
            {
                "name": s.name,
                "score": round(s.supplier_score, 1),
                "reliability": round(s.delivery_reliability, 1),
                "avg_delay_days": round(s.average_delay_days, 1),
            }
            for s in worst_suppliers
        ],
        "high_utilization_warehouses": [
            {"name": w.name, "utilization": w.utilization, "risk_level": w.risk_level.value}
            for w in busiest_warehouses
        ],
        "open_alerts": [
            {"title": a.title, "priority": a.priority.value, "type": a.alert_type.value}
            for a in open_alerts
        ],
        "top_risks": [
            {"title": r.title, "score": r.score, "level": r.level.value, "recommendation": r.recommendation}
            for r in risk["top_risks"][:5]
        ],
        "data_sources": _safe_data_context(db),
    }


def _safe_data_context(db: Session) -> dict:
    try:
        return ingestion.ai_context(db)
    except Exception:
        return {"mode": "demo", "connected_systems": 0, "sources": [], "failures": []}


def answer(db: Session, prompt: str) -> tuple[str, str, dict]:
    """Return (response_text, model_name, context_snapshot)."""
    context = build_context(db)
    if settings.ai_enabled:
        try:
            text = _answer_with_openai(prompt, context)
            return text, settings.OPENAI_MODEL, context
        except Exception as exc:  # graceful degradation
            text = _answer_locally(prompt, context)
            return (
                f"{text}\n\n_(AI provider unavailable: {type(exc).__name__}; used local engine.)_",
                "local-engine",
                context,
            )
    return _answer_locally(prompt, context), "local-engine", context


def _answer_with_openai(prompt: str, context: dict) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    system = (
        "You are the Operations Copilot for ATLASOPS, an enterprise supply chain operational intelligence platform. "
        "Answer concisely and decisively for an operations leadership audience. "
        "Always ground answers in the provided JSON context. Use short paragraphs and bullet "
        "points. When recommending actions, be specific and prioritized."
    )
    completion = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        temperature=0.3,
        messages=[
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": f"Operational context (JSON):\n{context}\n\nQuestion: {prompt}",
            },
        ],
    )
    return completion.choices[0].message.content or ""


# --------------------------------------------------------------------------- #
# Deterministic local engine
# --------------------------------------------------------------------------- #
def _answer_locally(prompt: str, context: dict) -> str:
    p = prompt.lower()
    kpis = context["kpis"]
    risk = context["risk"]

    if any(
        k in p
        for k in (
            "data source", "data sources", "connector", "connected", "integration",
            "sync", "synced", "ingest", "imported", "import", "sap", "oracle",
            "salesforce", "dynamics", "wms", "tms", "pipeline", "etl",
        )
    ):
        return _data_sources_answer(context)
    if any(k in p for k in ("delay", "late", "increasing this week")):
        return _delay_answer(context)
    if any(k in p for k in ("warehouse", "stockout", "inventory")):
        return _inventory_answer(context)
    if any(k in p for k in ("supplier", "vendor")):
        return _supplier_answer(context)
    if any(k in p for k in ("risk", "exposure", "vulnerab")):
        return _risk_answer(context)
    if any(k in p for k in ("action", "leadership", "do", "recommend", "priorit")):
        return _action_answer(context)
    if any(k in p for k in ("report", "summary", "status", "overview", "executive")):
        return _executive_summary(context)

    # default: executive summary
    return _executive_summary(context)


def _executive_summary(context: dict) -> str:
    k = context["kpis"]
    r = context["risk"]
    lines = [
        "## Operational Status Summary",
        "",
        f"- **Shipments:** {k['total_shipments']:,} total, {k['active_shipments']:,} active, "
        f"{k['delayed_shipments']:,} delayed.",
        f"- **On-time delivery:** {k['on_time_delivery_rate']}%.",
        f"- **Inventory health:** {k['inventory_health_score']}% of lines healthy.",
        f"- **Supplier reliability:** {k['supplier_reliability_score']}/100.",
        f"- **Overall risk:** {r['overall_score']}/100 ({r['overall_level']}). "
        f"Critical risks: {r['counts'].get('critical', 0)}.",
        f"- **Open alerts:** {k['open_alerts']:,}.",
        "",
        "### Top risks",
    ]
    for risk in context["top_risks"]:
        lines.append(f"- **{risk['title']}** ({risk['level']}, {risk['score']}): {risk['recommendation']}")
    return "\n".join(lines)


def _data_sources_answer(context: dict) -> str:
    ds = context.get("data_sources", {})
    sources = ds.get("sources", [])
    failures = ds.get("failures", [])
    lines = [
        "## Data sources & ingestion",
        "",
        f"Operating mode: **{ds.get('mode', 'demo').title()}**. "
        f"**{ds.get('connected_systems', 0)} connected systems**, "
        f"{ds.get('available_integrations', 0)} integrations available.",
        f"Records imported today: **{ds.get('records_imported_today', 0):,}** "
        f"(lifetime {ds.get('records_imported_total', 0):,}).",
    ]
    if sources:
        lines += ["", "**Connected systems:**"]
        for s in sources:
            last = s.get("last_sync_at")
            last_str = last.replace("T", " ")[:16] if last else "never"
            lines.append(
                f"- **{s['name']}** ({s['type']}) — {s['status']}, health {s['health']}, "
                f"last sync {last_str}, {s['record_count']:,} records."
            )
    if failures:
        lines += ["", "**⚠ Systems with ingestion failures:**"]
        for f in failures:
            lines.append(f"- {f['source']} — status {f['status']}, health {f['health']}.")
    else:
        lines += ["", "_No ingestion failures detected._"]
    return "\n".join(lines)


def _delay_answer(context: dict) -> str:
    k = context["kpis"]
    worst = context["worst_suppliers"]
    lines = [
        "## Why delays are trending",
        "",
        f"There are currently **{k['delayed_shipments']:,} delayed shipments** against an on-time "
        f"rate of **{k['on_time_delivery_rate']}%**. The primary contributors are supplier reliability "
        "gaps and concentration risk:",
        "",
    ]
    for s in worst[:3]:
        lines.append(
            f"- **{s['name']}** — reliability {s['reliability']}%, average delay {s['avg_delay_days']} days."
        )
    lines += [
        "",
        "**Recommended actions:**",
        "1. Expedite high-value delayed shipments via priority carriers.",
        "2. Place the lowest-reliability suppliers on recovery plans and qualify backups.",
        "3. Pre-position safety stock at destinations exposed to repeated slippage.",
    ]
    return "\n".join(lines)


def _inventory_answer(context: dict) -> str:
    whs = context["high_utilization_warehouses"]
    lines = ["## Inventory & warehouse risk", ""]
    if whs:
        top = whs[0]
        lines.append(
            f"The most at-risk warehouse is **{top['name']}** at **{top['utilization']}% utilization** "
            f"(risk level: {top['risk_level']})."
        )
    lines += ["", "**Watchlist:**"]
    for w in whs[:5]:
        lines.append(f"- {w['name']}: {w['utilization']}% utilization ({w['risk_level']}).")
    lines += [
        "",
        "**Recommended actions:**",
        "1. Trigger reorders for SKUs below reorder point.",
        "2. Rebalance inbound flow away from near-capacity sites.",
        "3. Raise safety stock for high-velocity SKUs ahead of demand.",
    ]
    return "\n".join(lines)


def _supplier_answer(context: dict) -> str:
    worst = context["worst_suppliers"]
    lines = ["## Supplier performance", "", f"Average supplier reliability score is "
             f"**{context['kpis']['supplier_reliability_score']}/100**.", "", "**Lowest performers:**"]
    for s in worst:
        lines.append(
            f"- **{s['name']}** — score {s['score']}, reliability {s['reliability']}%, "
            f"avg delay {s['avg_delay_days']}d."
        )
    lines += [
        "",
        "**Recommended actions:**",
        "1. Dual-source the most critical SKUs from the bottom suppliers.",
        "2. Institute weekly performance reviews with recovery milestones.",
        "3. Tighten delivery SLAs and defect thresholds at next contract renewal.",
    ]
    return "\n".join(lines)


def _risk_answer(context: dict) -> str:
    r = context["risk"]
    lines = [
        "## Risk exposure",
        "",
        f"Overall risk is **{r['overall_score']}/100 ({r['overall_level']})**.",
        "",
        "**By category:**",
    ]
    for cat, score in r["by_category"].items():
        lines.append(f"- {cat.title()}: {score}/100")
    lines += ["", "**Highest individual risks:**"]
    for risk in context["top_risks"]:
        lines.append(f"- {risk['title']} ({risk['level']}, {risk['score']})")
    return "\n".join(lines)


def _action_answer(context: dict) -> str:
    lines = [
        "## Recommended leadership actions",
        "",
        "Prioritized by operational and financial impact:",
        "",
    ]
    for i, risk in enumerate(context["top_risks"][:5], start=1):
        lines.append(f"{i}. **{risk['title']}** — {risk['recommendation']}")
    if not context["top_risks"]:
        lines.append("1. Maintain current operating posture; no critical risks detected.")
    return "\n".join(lines)
