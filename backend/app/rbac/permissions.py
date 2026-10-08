"""Enterprise permission catalog and system roles."""
from __future__ import annotations

from typing import Final

# resource.action
PERMISSIONS: Final[tuple[str, ...]] = (
    # org
    "org.read",
    "org.update",
    "org.delete",
    "org.transfer_ownership",
    "org.billing.manage",
    "org.members.invite",
    "org.members.manage",
    "org.roles.manage",
    "org.tokens.manage",
    "org.webhooks.manage",
    "org.audit.read",
    "org.usage.read",
    "org.environments.manage",
    # suppliers
    "suppliers.create",
    "suppliers.read",
    "suppliers.update",
    "suppliers.delete",
    "suppliers.export",
    # warehouses
    "warehouses.create",
    "warehouses.read",
    "warehouses.update",
    "warehouses.delete",
    "warehouses.export",
    # products
    "products.create",
    "products.read",
    "products.update",
    "products.delete",
    "products.export",
    # inventory
    "inventory.create",
    "inventory.read",
    "inventory.update",
    "inventory.delete",
    "inventory.export",
    "inventory.approve",
    "inventory.archive",
    # shipments
    "shipments.create",
    "shipments.read",
    "shipments.update",
    "shipments.delete",
    "shipments.export",
    "shipments.approve",
    # alerts
    "alerts.create",
    "alerts.read",
    "alerts.update",
    "alerts.resolve",
    "alerts.export",
    # risk
    "risk.read",
    "risk.recompute",
    "risk.export",
    # simulations
    "simulations.create",
    "simulations.read",
    "simulations.delete",
    # analytics
    "analytics.read",
    "analytics.export",
    # ai
    "ai.chat",
    "ai.reports",
    # connectors / import
    "connectors.create",
    "connectors.read",
    "connectors.update",
    "connectors.delete",
    "connectors.sync",
    "imports.create",
    "imports.read",
    "imports.rollback",
    # mission / network
    "mission.read",
    "network.read",
    # phase C
    "workflows.read",
    "workflows.manage",
    "workflows.execute",
    "documents.read",
    "documents.manage",
)

ALL_PERMISSIONS: Final[frozenset[str]] = frozenset(PERMISSIONS)

# System role slug → permissions
SYSTEM_ROLES: Final[dict[str, frozenset[str]]] = {
    "demo_operator": frozenset(p for p in PERMISSIONS if p in {
        "org.read", "mission.read", "network.read", "analytics.read", "ai.chat",
        "suppliers.read", "warehouses.read", "products.read", "shipments.read", "inventory.read",
        "suppliers.create", "warehouses.create", "products.create", "shipments.create", "inventory.create",
        "products.update", "shipments.update", "inventory.update", "imports.create", "imports.read",
        "alerts.read", "alerts.create", "alerts.update", "alerts.resolve", "risk.read", "connectors.read"
    }),
    "owner": ALL_PERMISSIONS,
    "admin": frozenset(p for p in PERMISSIONS if p not in {"org.delete", "org.transfer_ownership"}),
    "operations_director": frozenset(
        p
        for p in PERMISSIONS
        if p.startswith(
            (
                "suppliers.",
                "warehouses.",
                "products.",
                "inventory.",
                "shipments.",
                "alerts.",
                "risk.",
                "simulations.",
                "analytics.",
                "ai.",
                "connectors.",
                "imports.",
                "mission.",
                "network.",
                "workflows.",
                "documents.",
                "org.read",
                "org.usage.read",
                "org.members.invite",
            )
        )
    ),
    "operations_manager": frozenset(
        p
        for p in PERMISSIONS
        if p.startswith(
            (
                "suppliers.",
                "warehouses.",
                "products.",
                "inventory.",
                "shipments.",
                "alerts.",
                "risk.",
                "simulations.",
                "analytics.",
                "ai.",
                "imports.",
                "connectors.read",
                "connectors.sync",
                "mission.",
                "network.",
                "workflows.read",
                "workflows.execute",
                "documents.read",
                "org.read",
            )
        )
    ),
    "warehouse_manager": frozenset(
        {
            "warehouses.read",
            "warehouses.update",
            "warehouses.export",
            "inventory.create",
            "inventory.read",
            "inventory.update",
            "inventory.export",
            "inventory.approve",
            "shipments.read",
            "alerts.read",
            "alerts.update",
            "alerts.resolve",
            "mission.read",
            "network.read",
            "org.read",
            "ai.chat",
        }
    ),
    "inventory_manager": frozenset(
        {
            "products.read",
            "products.update",
            "products.export",
            "inventory.create",
            "inventory.read",
            "inventory.update",
            "inventory.delete",
            "inventory.export",
            "inventory.approve",
            "inventory.archive",
            "suppliers.read",
            "warehouses.read",
            "alerts.read",
            "alerts.update",
            "risk.read",
            "analytics.read",
            "imports.create",
            "imports.read",
            "mission.read",
            "org.read",
            "ai.chat",
        }
    ),
    "planner": frozenset(
        {
            "suppliers.read",
            "warehouses.read",
            "products.read",
            "inventory.read",
            "inventory.export",
            "shipments.read",
            "alerts.read",
            "risk.read",
            "simulations.create",
            "simulations.read",
            "analytics.read",
            "analytics.export",
            "mission.read",
            "network.read",
            "org.read",
            "ai.chat",
            "ai.reports",
        }
    ),
    "transportation": frozenset(
        {
            "shipments.create",
            "shipments.read",
            "shipments.update",
            "shipments.export",
            "shipments.approve",
            "warehouses.read",
            "suppliers.read",
            "alerts.read",
            "alerts.update",
            "alerts.resolve",
            "risk.read",
            "connectors.read",
            "connectors.sync",
            "mission.read",
            "network.read",
            "org.read",
            "ai.chat",
        }
    ),
    "procurement": frozenset(
        {
            "suppliers.create",
            "suppliers.read",
            "suppliers.update",
            "suppliers.export",
            "products.read",
            "inventory.read",
            "shipments.read",
            "alerts.read",
            "risk.read",
            "analytics.read",
            "mission.read",
            "org.read",
            "ai.chat",
        }
    ),
    "finance": frozenset(
        {
            "suppliers.read",
            "products.read",
            "inventory.read",
            "shipments.read",
            "shipments.export",
            "analytics.read",
            "analytics.export",
            "mission.read",
            "org.read",
            "org.usage.read",
            "org.billing.manage",
            "ai.reports",
        }
    ),
    "auditor": frozenset(
        {
            "org.read",
            "org.audit.read",
            "org.usage.read",
            "suppliers.read",
            "warehouses.read",
            "products.read",
            "inventory.read",
            "shipments.read",
            "alerts.read",
            "risk.read",
            "simulations.read",
            "analytics.read",
            "connectors.read",
            "imports.read",
            "mission.read",
            "network.read",
        }
    ),
    "viewer": frozenset(
        {
            "org.read",
            "suppliers.read",
            "warehouses.read",
            "products.read",
            "inventory.read",
            "shipments.read",
            "alerts.read",
            "risk.read",
            "simulations.read",
            "analytics.read",
            "mission.read",
            "network.read",
        }
    ),
}


def permissions_for_role(role_slug: str, custom: frozenset[str] | None = None) -> frozenset[str]:
    if custom is not None:
        return frozenset(custom) & ALL_PERMISSIONS
    return SYSTEM_ROLES.get(role_slug, SYSTEM_ROLES["viewer"])


# Lower rank = more privileged. Used to prevent invite-based privilege escalation.
ROLE_RANK: Final[dict[str, int]] = {
    "owner": 0,
    "admin": 1,
    "operations_director": 2,
    "operations_manager": 3,
    "warehouse_manager": 4,
    "inventory_manager": 4,
    "planner": 4,
    "transportation": 4,
    "procurement": 4,
    "finance": 4,
    "auditor": 5,
    # "analyst" is a legacy alias used by some UI labels; treat as planner-rank.
    "analyst": 5,
    "viewer": 6,
}

# Roles that may never be granted via invitation (ownership transfer is separate).
NON_INVITABLE_ROLES: Final[frozenset[str]] = frozenset({"owner"})


def can_invite_role(inviter_role: str, target_role: str) -> bool:
    """True when inviter may assign ``target_role`` (never owner; never above self)."""
    if target_role in NON_INVITABLE_ROLES:
        return False
    if target_role.startswith("custom:"):
        # Custom roles require member-manage; invite path should reject unless admin+.
        return inviter_role in {"owner", "admin"}
    if target_role not in SYSTEM_ROLES:
        return False
    inviter_rank = ROLE_RANK.get(inviter_role)
    target_rank = ROLE_RANK.get(target_role)
    if inviter_rank is None or target_rank is None:
        return False
    # Inviter may only assign equal or weaker roles (higher rank number).
    return target_rank >= inviter_rank and inviter_role in {
        "owner",
        "admin",
        "operations_director",
    }
