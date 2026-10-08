"""AI Operations Advisor.

Builds a structured context snapshot from live application data and answers
operational questions. Uses the OpenAI API when an API key is configured;
otherwise falls back to a deterministic, rule-based "local engine" so the
feature works fully offline for demos and CI.
"""
from __future__ import annotations

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Alert, RiskAssessment, Supplier, Warehouse, Inventory, Product, Shipment
from app.models.enums import AlertStatus, RiskLevel, ShipmentStatus
from app.services import ingestion, metrics, risk_engine


def build_context(db: Session) -> dict:
    """Build AI context scoped to the caller's RBAC permissions.

    ``ai.chat`` alone must not become a privilege-escalation path into
    suppliers/risk/analytics data the role cannot read via dedicated APIs.
    """
    from app.tenancy.context import get_tenant

    tenant = get_tenant()
    org_id = tenant.organization_id
    perms = tenant.permissions
    ctx: dict = {"permissions_applied": sorted(perms)}

    if "analytics.read" in perms or "mission.read" in perms:
        ctx["kpis"] = metrics.compute_kpis(db, org_id)

    if "risk.read" in perms:
        risk = risk_engine.summarize(db)
        ctx["risk"] = {
            "overall_score": risk["overall_score"],
            "overall_level": risk["overall_level"].value
            if isinstance(risk["overall_level"], RiskLevel)
            else risk["overall_level"],
            "by_category": risk["by_category"],
            "counts": risk["counts"],
        }
        ctx["top_risks"] = [
            {
                "title": r.title,
                "score": r.score,
                "level": r.level.value,
                "recommendation": r.recommendation,
            }
            for r in risk["top_risks"][:5]
        ]

    if "suppliers.read" in perms:
        worst_suppliers = db.scalars(
            select(Supplier)
            .where(Supplier.organization_id == org_id)
            .order_by(Supplier.supplier_score.asc())
            .limit(5)
        ).all()
        ctx["worst_suppliers"] = [
            {
                "name": s.name,
                "score": round(s.supplier_score, 1),
                "reliability": round(s.delivery_reliability, 1),
                "avg_delay_days": round(s.average_delay_days, 1),
            }
            for s in worst_suppliers
        ]

    if "warehouses.read" in perms:
        busiest_warehouses = db.scalars(
            select(Warehouse)
            .where(Warehouse.organization_id == org_id)
            .order_by((Warehouse.current_inventory * 1.0 / Warehouse.capacity).desc())
            .limit(5)
        ).all()
        ctx["high_utilization_warehouses"] = [
            {"name": w.name, "utilization": w.utilization, "risk_level": w.risk_level.value}
            for w in busiest_warehouses
        ]

    if "alerts.read" in perms:
        open_alerts = db.scalars(
            select(Alert)
            .where(
                Alert.organization_id == org_id,
                Alert.status != AlertStatus.RESOLVED,
            )
            .order_by(Alert.created_at.desc())
            .limit(8)
        ).all()
        ctx["open_alerts"] = [
            {"title": a.title, "priority": a.priority.value, "type": a.alert_type.value}
            for a in open_alerts
        ]

    if "inventory.read" in perms and "warehouses.read" in perms:
        from app.services.inventory_logic import days_of_supply, reorder_recommendation
        positions = db.execute(select(Inventory, Product, Warehouse)
            .join(Product, Product.id == Inventory.product_id)
            .join(Warehouse, Warehouse.id == Inventory.warehouse_id)
            .where(Inventory.organization_id == org_id, Product.organization_id == org_id,
                   Warehouse.organization_id == org_id, Inventory.is_current.is_(True),
                   Inventory.quantity <= Inventory.reorder_point)
            .order_by(case((Inventory.avg_daily_demand > 0, Inventory.quantity * 1.0 / Inventory.avg_daily_demand), else_=1e12), Product.sku).limit(20)).all()
        shipments = []
        if "shipments.read" in perms and positions:
            shipments = db.scalars(select(Shipment).where(Shipment.organization_id == org_id,
                Shipment.product_id.in_([p.id for _, p, _ in positions]),
                Shipment.status.in_([ShipmentStatus.DELAYED, ShipmentStatus.IN_TRANSIT, ShipmentStatus.CUSTOMS_HOLD]))
                .order_by(Shipment.eta).limit(50)).all()
        supplier_names = {}
        if "suppliers.read" in perms and shipments:
            supplier_names = {s.id: s.name for s in db.scalars(select(Supplier).where(
                Supplier.organization_id == org_id, Supplier.id.in_([ship.supplier_id for ship in shipments if ship.supplier_id]))) }
        ctx["inventory_priorities"] = [{
            "sku": product.sku, "product": product.name, "warehouse": warehouse.name,
            "quantity": inv.quantity, "reorder_point": inv.reorder_point,
            "avg_daily_demand": inv.avg_daily_demand, "days_of_supply": days_of_supply(inv.quantity, inv.avg_daily_demand),
            "recommended_replenishment": reorder_recommendation(inv),
            "snapshot_at": inv.snapshot_date.isoformat() if inv.snapshot_date else None,
            "linked_shipments": [{"reference": ship.reference, "status": ship.status.value,
                "supplier": supplier_names.get(ship.supplier_id),
                "units": ship.units, "delay_days": ship.delay_days, "eta": ship.eta.isoformat()}
                for ship in shipments if ship.product_id == product.id and ship.warehouse_id == warehouse.id],
        } for inv, product, warehouse in positions]
        ctx["inventory_method"] = "Current stock versus configured thresholds; reservations and incoming units are not deducted from suggested replenishment. Shipment links show association, not proven causation."

    if "connectors.read" in perms:
        ctx["data_sources"] = _safe_data_context(db)

    if {'inventory.read','warehouses.read','shipments.read','suppliers.read','alerts.read'}.issubset(perms):
        from app.services.priorities import operational_priorities
        priorities = operational_priorities(db,org_id)
        ctx['operational_priorities'] = [{key:item[key] for key in ('title','severity','explanation','recommendation','method')} for item in priorities['items'][:10]]
        ctx['priority_ranking'] = priorities['ranking']

    return ctx


def _safe_data_context(db: Session) -> dict:
    try:
        with db.begin_nested():
            return ingestion.ai_context(db)
    except Exception:
        return {"mode": "unknown", "data_available": False, "sources": [], "failures": ["Data source context unavailable"]}


def answer(db: Session, prompt: str, *, context: dict | None = None) -> tuple[str, str, dict]:
    """Return (response_text, model_name, context_snapshot)."""
    from app.services.ai_providers import get_ai_provider

    context = build_context(db) if context is None else context
    # Simulation intents: never invent outcomes — point at the simulation engine.
    if _wants_simulation(prompt):
        text = _simulation_guidance(prompt, context)
        return text, "local-engine", context

    provider = get_ai_provider()
    from app.core.telemetry import AI_PROVIDER_TOTAL
    provider_label = "openai" if provider.name == "openai" else "local-engine"
    try:
        text = provider.answer(prompt, context)
        if AI_PROVIDER_TOTAL is not None:
            AI_PROVIDER_TOTAL.labels(provider_label, "success").inc()
        model = settings.OPENAI_MODEL if provider.name == "openai" else provider.name
        return text, model, context
    except Exception as exc:  # graceful degradation
        if AI_PROVIDER_TOTAL is not None:
            AI_PROVIDER_TOTAL.labels(provider_label, "fallback").inc()
        from app.services.ai_providers import LocalEngineProvider

        text = LocalEngineProvider().answer(prompt, context)
        return (
            f"{text}\n\n_(AI provider unavailable: {type(exc).__name__}; used local engine.)_",
            "local-engine",
            context,
        )


def _wants_simulation(prompt: str) -> bool:
    p = prompt.lower()
    return any(
        k in p
        for k in (
            "what happens if",
            "what if",
            "simulate",
            "simulation",
            "unavailable for",
            "shutdown for",
            "outage for",
            "closed for",
        )
    )


def _simulation_guidance(prompt: str, context: dict) -> str:
    worst = (context.get("worst_suppliers") or [{}])[0]
    name = worst.get("name") or "the selected supplier"
    return (
        "## Simulation required\n\n"
        f"I will not invent impact numbers for: _{prompt.strip()}_\n\n"
        "Run the **Simulation Center** with a grounded scenario against live tenant data:\n"
        f"1. Open `/simulator` and choose **Supplier delay** or **Supplier shutdown**.\n"
        f"2. Target **{name}** (or another supplier from your scorecards).\n"
        "3. Compare **no action** vs recommended mitigations in the result.\n"
        "4. Record the chosen action in Incidents / Alerts when you decide.\n\n"
        "_Estimates from the simulation engine are labeled modeled estimates, not audited financials._"
    )


# --------------------------------------------------------------------------- #
# Deterministic local engine
# --------------------------------------------------------------------------- #
def _answer_locally(prompt: str, context: dict) -> str:
    p = prompt.lower()
    kpis = context.get("kpis") or {}
    risk = context.get("risk") or {"overall_score": 0, "overall_level": "unknown", "by_category": {}, "counts": {}}
    if not context.get("kpis") and not context.get("risk"):
        return (
            "I can answer within your role permissions, but this account does not have "
            "access to the operational datasets needed for that question. Ask an admin "
            "to grant the relevant read permissions, or narrow the question to areas you can access."
        )

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
    matching = [row for row in context.get("inventory_priorities", []) if row['sku'].lower() in p or row['warehouse'].lower() in p]
    if matching:
        return _inventory_answer({**context, 'inventory_priorities':matching})
    if context.get('operational_priorities') and any(k in p for k in ('urgent','address first','what should','operational issues','priorities','problems right now')):
        lines=['Recorded operational priorities',context['priority_ranking']]
        for item in context['operational_priorities']:
            lines.extend([f"- {item['severity']}: {item['title']}",f"  Evidence: {item['explanation']}",f"  Recommendation: {item['recommendation']}"])
        lines.append('These are recommendations. No supplier has been contacted, no order placed, and no stock changed.')
        return '\n'.join(lines)
    if context.get("inventory_priorities") and any(k in p for k in ("warehouse", "stockout", "inventory", "replenish", "urgent", "what should", "operational issues")):
        return _inventory_answer(context)
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
    k = context.get("kpis") or {}
    r = context.get("risk") or {"overall_score": 0, "overall_level": "unknown", "counts": {}}
    if not k and not r:
        return "Insufficient permissions to build an executive summary for this role."
    lines = [
        "## Operational Status Summary",
        "",
        f"- **Shipments:** {k.get('total_shipments', 0):,} total, {k.get('active_shipments', 0):,} active, "
        f"{k.get('delayed_shipments', 0):,} delayed.",
        f"- **On-time delivery:** {k.get('on_time_delivery_rate', '—')}%.",
        f"- **Inventory health:** {k.get('inventory_health_score', '—')}% of lines healthy.",
        f"- **Supplier reliability:** {k.get('supplier_reliability_score', '—')}/100.",
        f"- **Overall risk:** {r.get('overall_score', '—')}/100 ({r.get('overall_level', '—')}). "
        f"Critical risks: {(r.get('counts') or {}).get('critical', 0)}.",
        f"- **Open alerts:** {k.get('open_alerts', 0):,}.",
        "",
        "### Top risks",
    ]
    for risk in context.get("top_risks") or []:
        lines.append(f"- **{risk['title']}** ({risk['level']}, {risk['score']}): {risk['recommendation']}")
    if not context.get("top_risks"):
        lines.append("- _No risk records in scope for this role._")
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
    k = context.get("kpis") or {}
    worst = context.get("worst_suppliers") or []
    if not k and not worst:
        return "Delay analysis requires analytics and/or supplier read permissions."
    lines = [
        "## Why delays are trending",
        "",
        f"There are currently **{k.get('delayed_shipments', 0):,} delayed shipments** against an on-time "
        f"rate of **{k.get('on_time_delivery_rate', '—')}%**. The primary contributors are supplier reliability "
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
    positions = context.get("inventory_priorities")
    if positions:
        lines = ["Recorded inventory below reorder thresholds (up to 20 positions):"]
        for row in positions:
            coverage = f"{row['days_of_supply']:g} days" if row['days_of_supply'] is not None else "unknown"
            lines.append(f"- {row['product']} ({row['sku']}) at {row['warehouse']}: {row['quantity']} units; reorder threshold {row['reorder_point']}; average daily demand {row['avg_daily_demand']}; stock coverage {coverage}; suggested replenishment {row['recommended_replenishment']} units.")
            for shipment in row['linked_shipments']:
                supplier = f"; supplier {shipment['supplier']}" if shipment.get('supplier') else ""
                lines.append(f"  Linked shipment {shipment['reference']}: {shipment['status']}, {shipment['units']} units, recorded delay {shipment['delay_days']} days; ETA {shipment['eta']}{supplier}.")
        lines.append(context.get('inventory_method', ''))
        lines.append("Next: confirm demand and supplier delivery dates, then track the approved response in an incident. No order has been placed and no inventory has been changed.")
        return "\n".join(lines)
    whs = context.get("high_utilization_warehouses") or []
    if not whs:
        return "Warehouse risk analysis requires warehouses.read permission."
    lines = ["## Inventory & warehouse risk", ""]
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
    worst = context.get("worst_suppliers") or []
    k = context.get("kpis") or {}
    if not worst and "supplier_reliability_score" not in k:
        return "Supplier analysis requires suppliers.read (and preferably analytics.read)."
    lines = [
        "## Supplier performance",
        "",
        f"Average supplier reliability score is **{k.get('supplier_reliability_score', '—')}/100**.",
        "",
        "**Lowest performers:**",
    ]
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
    r = context.get("risk")
    if not r:
        return "Risk analysis requires risk.read permission."
    lines = [
        "## Risk exposure",
        "",
        f"Overall risk is **{r['overall_score']}/100 ({r['overall_level']})**.",
        "",
        "**By category:**",
    ]
    for cat, score in (r.get("by_category") or {}).items():
        lines.append(f"- {cat.title()}: {score}/100")
    lines += ["", "**Highest individual risks:**"]
    for risk in context.get("top_risks") or []:
        lines.append(f"- {risk['title']} ({risk['level']}, {risk['score']})")
    return "\n".join(lines)


def _action_answer(context: dict) -> str:
    top = context.get("top_risks") or []
    lines = [
        "## Recommended leadership actions",
        "",
        "Prioritized by operational and financial impact:",
        "",
    ]
    for i, risk in enumerate(top[:5], start=1):
        lines.append(f"{i}. **{risk['title']}** — {risk['recommendation']}")
    if not top:
        lines.append("1. Maintain current operating posture; no critical risks in your permission scope.")
    return "\n".join(lines)
