"""Plan catalog — seat limits, AI credits, and feature gates."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final

from app.models.enums import BillingPlan


@dataclass(frozen=True, slots=True)
class PlanDefinition:
    slug: BillingPlan
    name: str
    description: str
    seat_limit: int  # -1 = unlimited
    connector_limit: int  # -1 = unlimited
    ai_credits_monthly: int
    features: frozenset[str] = field(default_factory=frozenset)
    stripe_price_env_monthly: str | None = None
    stripe_price_env_annual: str | None = None
    trial_days: int = 0
    is_public: bool = True


PLAN_CATALOG: Final[dict[BillingPlan, PlanDefinition]] = {
    BillingPlan.TRIAL: PlanDefinition(
        slug=BillingPlan.TRIAL,
        name="Trial",
        description="14-day evaluation with limited seats and AI credits.",
        seat_limit=5,
        connector_limit=2,
        ai_credits_monthly=1_000,
        features=frozenset(
            {
                "mission",
                "shipments",
                "inventory",
                "suppliers",
                "risk",
                "simulations",
                "ai_chat",
                "csv_import",
                "excel_import",
            }
        ),
        trial_days=14,
        is_public=False,
    ),
    BillingPlan.STARTER: PlanDefinition(
        slug=BillingPlan.STARTER,
        name="Starter",
        description="For small ops teams connecting their first data sources.",
        seat_limit=10,
        connector_limit=3,
        ai_credits_monthly=5_000,
        features=frozenset(
            {
                "mission",
                "shipments",
                "inventory",
                "suppliers",
                "risk",
                "simulations",
                "ai_chat",
                "ai_reports",
                "csv_import",
                "excel_import",
                "json_import",
                "connectors",
            }
        ),
        stripe_price_env_monthly="STRIPE_PRICE_STARTER_MONTHLY",
        stripe_price_env_annual="STRIPE_PRICE_STARTER_ANNUAL",
    ),
    BillingPlan.PROFESSIONAL: PlanDefinition(
        slug=BillingPlan.PROFESSIONAL,
        name="Professional",
        description="For teams running real operations on connected data.",
        seat_limit=50,
        connector_limit=15,
        ai_credits_monthly=25_000,
        features=frozenset(
            {
                "mission",
                "shipments",
                "inventory",
                "suppliers",
                "risk",
                "simulations",
                "ai_chat",
                "ai_reports",
                "csv_import",
                "excel_import",
                "json_import",
                "connectors",
                "audit_log",
                "api_tokens",
                "webhooks",
                "sso",
            }
        ),
        stripe_price_env_monthly="STRIPE_PRICE_PROFESSIONAL_MONTHLY",
        stripe_price_env_annual="STRIPE_PRICE_PROFESSIONAL_ANNUAL",
    ),
    BillingPlan.ENTERPRISE: PlanDefinition(
        slug=BillingPlan.ENTERPRISE,
        name="Enterprise",
        description="Organization-wide deployment with unlimited seats and custom limits.",
        seat_limit=-1,
        connector_limit=-1,
        ai_credits_monthly=100_000,
        features=frozenset(
            {
                "mission",
                "shipments",
                "inventory",
                "suppliers",
                "risk",
                "simulations",
                "ai_chat",
                "ai_reports",
                "csv_import",
                "excel_import",
                "json_import",
                "connectors",
                "audit_log",
                "api_tokens",
                "webhooks",
                "sso",
                "custom_roles",
                "priority_support",
                "dedicated_onboarding",
            }
        ),
        stripe_price_env_monthly="STRIPE_PRICE_ENTERPRISE_MONTHLY",
        stripe_price_env_annual=None,
    ),
}


def get_plan(plan: BillingPlan | str) -> PlanDefinition:
    if isinstance(plan, str):
        plan = BillingPlan(plan)
    try:
        return PLAN_CATALOG[plan]
    except KeyError as exc:
        raise ValueError(f"Unknown plan: {plan}") from exc


def list_public_plans() -> list[PlanDefinition]:
    return [p for p in PLAN_CATALOG.values() if p.is_public]


def plan_has_feature(plan: BillingPlan | str, feature: str) -> bool:
    return feature in get_plan(plan).features
