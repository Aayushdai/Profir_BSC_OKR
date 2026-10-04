# -*- coding: utf-8 -*-

{
    'name': 'Executive CEO Dashboard',
    'version': '19.0.1.0.0',
    'category': 'Productivity/Dashboards',

    'summary': (
        'Executive dashboard for visualizing financial, sales, '
        'CRM, inventory and operational performance data.'
    ),

    'description': """
Executive CEO Dashboard
=======================

A centralized executive dashboard for visualizing operational
business performance from Odoo.

The dashboard acts as a visualization layer over existing Odoo
operational modules. Strategic objectives, OKRs, KPIs, targets,
progress calculations and performance-gap analysis are handled
separately by the Strategic Performance Management module.

Finance & Accounting
--------------------
* Total Revenue
* Total Expenses
* Net Profit
* Net Margin
* Cash Position
* Accounts Receivable
* Accounts Payable
* Overdue Invoices
* Days Sales Outstanding (DSO)
* Top Overdue Customers

Sales & CRM
-----------
* Confirmed Sales Orders
* Sales Order Activity
* Sales Revenue
* Sales Pipeline
* Win Rate
* Average Deal Size
* New Leads
* Top Customers
* Closing Opportunities

Inventory & Purchasing
----------------------
* Total Inventory Value
* Low Stock Items
* Pending Deliveries
* Pending Receipts
* Overdue Purchase Orders
* Reorder Information

Projects & Operations
---------------------
* Overdue Tasks
* Tasks Due Today
* Active Projects

Dashboard Features
------------------
* Centralized executive dashboard
* Date From / Date To filtering
* Operational data visualization
* Financial and operational summaries
* Dynamic support for available Odoo modules

Strategic Performance Separation
--------------------------------
The dashboard does not own strategic business logic.

BSC perspectives, strategic objectives, OKRs, Key Results,
KPI definitions, KPI targets, progress calculations and
performance-gap analysis belong to the Strategic Performance
Management module.

The CEO Dashboard consumes and visualizes relevant operational
and strategic performance data.
    """,

    'author': 'Solomon Yeshiwas',
    'website': '',
    'license': 'LGPL-3',

    'depends': [
        'base',
        'web',
    ],

    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/dashboard_views.xml',
    ],

    'assets': {
        'web.assets_backend': [
            'ceo_dashboard/static/src/scss/dashboard.scss',
            'ceo_dashboard/static/src/js/dashboard.js',
            'ceo_dashboard/static/src/xml/dashboard.xml',
        ],
    },

    'images': [
        'static/description/banner.png',
        'static/description/dashboard_main.png',
        'static/description/finance_tab.png',
        'static/description/sales_tab.png',
    ],

    'application': True,
    'installable': True,
    'auto_install': False,
}