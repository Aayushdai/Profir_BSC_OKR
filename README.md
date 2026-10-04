# Executive CEO Dashboard (Odoo 20)

A centralized executive dashboard for visualizing operational performance from Odoo.

The dashboard provides a consolidated view of Finance & Accounting, Sales & CRM,
Inventory & Operations, and Project Operations, with global date filtering and
year-over-year comparison.

The module acts as a visualization layer over existing Odoo operational data.
Strategic objectives, OKRs, KPI definitions, KPI targets, performance calculations,
and strategic analysis are handled separately by the Strategic Performance
Management module.

## Dependencies

`base`, `web`

The dashboard keeps these dependencies minimal and dynamically uses operational
Odoo models when the corresponding applications are installed.

## Install

1. Copy the `ceo_dashboard` folder into your Odoo addons path.
2. Update the Apps List.
3. Install **Executive CEO Dashboard**.
4. Open **Executive Dashboard** from the main menu.

## Main Features

- Executive Summary
- Finance & Accounting metrics
- Sales & CRM metrics
- Inventory & Operations metrics
- Project operational metrics
- Today / Week / Month / Quarter / Year date presets
- Custom date range filtering
- Year-over-year comparison
- Currency-aware financial formatting
- Direct drill-down to relevant Odoo records
- Refresh of operational data from Odoo

## Notes / Assumptions

- Financial figures are retrieved from the available Odoo accounting data.
- Revenue, expenses, profit, cash, receivables, payables, and overdue invoice
  metrics are presented from the corresponding operational records.
- Sales and CRM information is retrieved from available sales orders and CRM
  opportunities.
- Inventory information is retrieved from available stock and purchasing data.
- Project information is retrieved from available project and task data.
- Operational sections are handled independently so that unavailable optional
  Odoo models do not prevent the dashboard from loading the remaining sections.
- Strategic performance logic such as BSC perspectives, strategic objectives,
  OKRs, Key Results, KPI targets, KPI progress, and performance-gap analysis is
  outside the scope of this dashboard module.

## Architecture

```text
Odoo Operational Modules
        |
        v
Operational Data
        |
        v
CEO Dashboard
(Visualization Layer)
        |
        v
Executive Users