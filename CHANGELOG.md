# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this
project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Public marketing website (`app/(marketing)`): landing page with animated product
  preview, plus Solutions, Platform, Integrations, Security, Pricing, Documentation,
  About, and a Get Started workspace chooser.
- Root architecture, security, contributing, roadmap, code of conduct, and changelog
  documentation.

### Changed
- Standardized product naming to **ATLASOPS** across the application, backend, database
  configuration, documentation, and demo accounts.
- Default UI theme set to light; dark mode remains available in the application.

## [0.1.0]

### Added
- **Mission Control** with composite health score, executive KPIs, AI situation report,
  ranked recommended actions, and a critical alert feed.
- Operational modules: Shipments, Inventory, Warehouses, Suppliers, Alerts, Analytics,
  and an interactive Network View.
- **Risk engine** with explainable 0–100 scoring across supplier, shipment, inventory, and
  geographic categories.
- **Simulation Center** for supplier shutdown, port closure, warehouse outage, demand
  spike, and weather disruption scenarios.
- **Operations Copilot** with an optional OpenAI integration and a deterministic local
  fallback engine.
- **Executive Briefs** with Markdown and PDF export.
- **Data integration**: CSV/Excel ingestion with validation and mapping, a connector
  template framework (SAP, Oracle, Salesforce, Dynamics, WMS, TMS, REST), and a Pipeline
  Monitor. Demo and Connected operating modes.
- JWT authentication with role-based access control (Admin, Operations Manager, Analyst,
  Executive).
- Deterministic synthetic seed engine and an operational CLI (`init-db`, `seed`, `reset`,
  `create-user`).
- Docker Compose deployment, Alembic migrations, and an integration test suite.

[Unreleased]: https://github.com/your-org/atlasops/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/your-org/atlasops/releases/tag/v0.1.0
