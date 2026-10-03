# -*- coding: utf-8 -*-

from datetime import timedelta
import logging

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.tools import date_utils


_logger = logging.getLogger(__name__)


class CeoDashboard(models.AbstractModel):
    """Executive CEO Dashboard Data Engine.

    Provides operational business data for dashboard visualization.

    Strategic objectives, OKRs, KPIs, targets, progress calculations,
    and performance-gap analysis will be handled by the Strategic
    Performance Management module.
    """

    _name = 'ceo.dashboard'
    _description = 'Executive CEO Dashboard Data Engine'

    # ---------------------------------------------------------------------
    # Public Entry Point
    # ---------------------------------------------------------------------

    @api.model
    def get_dashboard_data(self, date_from=None, date_to=None):
        today = fields.Date.context_today(self)

        date_from_dt = (
            fields.Date.from_string(date_from)
            if date_from
            else date_utils.start_of(today, 'month')
        )

        date_to_dt = (
            fields.Date.from_string(date_to)
            if date_to
            else today
        )

        company = self.env.company
        currency = company.currency_id

        # Detect available operational modules.
        installed = {
            'account': 'account.move' in self.env,
            'sale': 'sale.order' in self.env,
            'crm': 'crm.lead' in self.env,
            'stock': 'stock.quant' in self.env,
            'purchase': 'purchase.order' in self.env,
            'project': 'project.task' in self.env,
        }

        data = {
            'company_name': company.name or 'My Company',
            'currency_symbol': currency.symbol or '$',
            'currency_position': currency.position or 'before',
            'currency_name': currency.name or 'USD',
            'date_from': fields.Date.to_string(date_from_dt),
            'date_to': fields.Date.to_string(date_to_dt),
            'installed': installed,
        }

        data['summary'] = self._get_summary_data(
            date_from_dt,
            date_to_dt,
            company,
            installed,
        )

        data['finance'] = self._get_finance_data(
            date_from_dt,
            date_to_dt,
            company,
            installed,
        )

        data['sales'] = self._get_sales_data(
            date_from_dt,
            date_to_dt,
            company,
            installed,
        )

        data['inventory'] = self._get_inventory_data(
            date_from_dt,
            date_to_dt,
            company,
            installed,
        )

        data['project'] = self._get_project_data(
            date_from_dt,
            date_to_dt,
            company,
            installed,
        )

        return data

    # ---------------------------------------------------------------------
    # 1. Executive Summary
    # ---------------------------------------------------------------------

    def _get_summary_data(self, date_from, date_to, company, installed):
        today = fields.Date.context_today(self)

        revenue = 0.0
        expenses = 0.0
        revenue_ly = 0.0

        cash = 0.0
        ar_total = 0.0
        ap_total = 0.0

        overdue_amount = 0.0
        overdue_count = 0
        dso = 0.0

        orders_mtd_count = 0
        orders_today_count = 0

        win_rate = 0.0
        top_overdue = []

        # -------------------------------------------------------------
        # Accounting
        # -------------------------------------------------------------

        if installed['account']:
            try:
                revenue, expenses = self._calc_revenue_expense(
                    date_from,
                    date_to,
                    company,
                )

                ly_from = date_from - relativedelta(years=1)
                ly_to = date_to - relativedelta(years=1)

                revenue_ly, _ = self._calc_revenue_expense(
                    ly_from,
                    ly_to,
                    company,
                )

                cash = self._calc_cash(
                    date_to,
                    company,
                )

                ar_total, ap_total = self._calc_ar_ap(
                    date_to,
                    company,
                )

                overdue_recs = self._get_overdue_moves(company)

                if overdue_recs:
                    overdue_count = len(overdue_recs)

                    overdue_amount = sum(
                        overdue_recs.mapped('amount_residual')
                    )

                    days_in_period = max(
                        1,
                        (date_to - date_from).days + 1,
                    )

                    if revenue > 0:
                        dso = round(
                            (ar_total / revenue) * days_in_period,
                            1,
                        )

                    grouped = {}

                    for move in overdue_recs:
                        if move.partner_id:
                            grouped.setdefault(
                                move.partner_id,
                                [],
                            ).append(move)

                    sorted_customers = sorted(
                        grouped.items(),
                        key=lambda item: sum(
                            m.amount_residual
                            for m in item[1]
                        ),
                        reverse=True,
                    )[:5]

                    for partner, moves in sorted_customers:
                        latest_move = moves[0]

                        delay = (
                            today
                            - (
                                latest_move.invoice_date_due
                                or latest_move.invoice_date
                                or today
                            )
                        ).days

                        top_overdue.append({
                            'name': partner.name or 'Unknown',
                            'inv_ref': latest_move.name or 'INV/---',
                            'contact': (
                                partner.contact_address_inline
                                or partner.phone
                                or partner.email
                                or 'Accounting Contact'
                            ),
                            'amount': sum(
                                m.amount_residual
                                for m in moves
                            ),
                            'days_late': max(delay, 0),
                        })

            except Exception as e:
                _logger.warning(
                    "CEO Dashboard Summary: account calculation error: %s",
                    e,
                )

        # -------------------------------------------------------------
        # Sales
        # -------------------------------------------------------------

        if installed['sale']:
            try:
                Sale = self.env['sale.order']

                month_start = today.replace(day=1)

                orders_mtd_count = Sale.search_count([
                    ('company_id', '=', company.id),
                    ('state', '=', 'sale'),
                    ('date_order', '>=', f"{month_start} 00:00:00"),
                ])

                orders_today_count = Sale.search_count([
                    ('company_id', '=', company.id),
                    ('state', '=', 'sale'),
                    ('date_order', '>=', f"{today} 00:00:00"),
                ])

            except Exception as e:
                _logger.warning(
                    "CEO Dashboard Summary: sale calculation error: %s",
                    e,
                )

        # -------------------------------------------------------------
        # CRM
        # -------------------------------------------------------------

        if installed['crm']:
            try:
                Lead = self.env['crm.lead']

                won = Lead.search_count([
                    ('company_id', 'in', (company.id, False)),
                    ('stage_id.is_won', '=', True),
                ])

                lost = Lead.search_count([
                    ('company_id', 'in', (company.id, False)),
                    ('active', '=', False),
                    ('probability', '=', 0),
                ])

                total_opps = won + lost

                win_rate = (
                    round((won / total_opps) * 100, 1)
                    if total_opps > 0
                    else 0.0
                )

            except Exception as e:
                _logger.warning(
                    "CEO Dashboard Summary: CRM calculation error: %s",
                    e,
                )

        # -------------------------------------------------------------
        # Inventory
        # -------------------------------------------------------------

        inventory_value = 0.0
        low_stock_count = 0
        pending_deliveries = 0
        pending_receipts = 0
        turnover_rate = 0.0

        if installed['stock']:
            try:
                StockQuant = self.env['stock.quant']

                quants = StockQuant.search([
                    ('company_id', '=', company.id),
                    ('location_id.usage', '=', 'internal'),
                ])

                inventory_value = sum(
                    q.quantity * q.product_id.standard_price
                    for q in quants
                )

                StockPicking = self.env['stock.picking']

                pending_deliveries = StockPicking.search_count([
                    ('company_id', '=', company.id),
                    ('picking_type_code', '=', 'outgoing'),
                    ('state', 'not in', ('done', 'cancel')),
                ])

                pending_receipts = StockPicking.search_count([
                    ('company_id', '=', company.id),
                    ('picking_type_code', '=', 'incoming'),
                    ('state', 'not in', ('done', 'cancel')),
                ])

                if inventory_value > 0 and expenses > 0:
                    turnover_rate = round(
                        expenses / inventory_value,
                        1,
                    )

            except Exception as e:
                _logger.warning(
                    "CEO Dashboard Summary: stock calculation error: %s",
                    e,
                )

        # -------------------------------------------------------------
        # Project
        # -------------------------------------------------------------

        projects_over_budget_count = 0

        if installed['project']:
            try:
                projects_over_budget_count = self.env[
                    'project.task'
                ].search_count([
                    ('company_id', 'in', (company.id, False)),
                    ('date_deadline', '<', f"{today} 00:00:00"),
                    ('is_closed', '=', False),
                ])

            except Exception as e:
                _logger.warning(
                    "CEO Dashboard Summary: project calculation error: %s",
                    e,
                )

        # -------------------------------------------------------------
        # Financial summary
        # -------------------------------------------------------------

        net_profit = revenue - expenses

        net_margin = (
            round((net_profit / revenue) * 100, 1)
            if revenue
            else 0.0
        )

        rev_yoy_pct = (
            round(
                ((revenue - revenue_ly) / revenue_ly) * 100,
                1,
            )
            if revenue_ly > 0
            else 0.0
        )

        return {
            'total_revenue': revenue,
            'total_expenses': expenses,
            'rev_yoy_pct': rev_yoy_pct,
            'net_profit': net_profit,
            'net_margin': net_margin,
            'live_cash': cash,
            'overdue_amount': overdue_amount,
            'overdue_count': overdue_count,
            'dso': dso,
            'orders_mtd_count': orders_mtd_count,
            'orders_today_count': orders_today_count,
            'win_rate': win_rate,
            'ar_total': ar_total,
            'ap_total': ap_total,
            'net_working_capital_surplus': ar_total - ap_total,
            'inventory_value': inventory_value,
            'low_stock_count': low_stock_count,
            'pending_deliveries': pending_deliveries,
            'pending_receipts': pending_receipts,
            'turnover_rate': turnover_rate,
            'top_overdue': top_overdue,
            'projects_over_budget_count': projects_over_budget_count,
        }

    # ---------------------------------------------------------------------
    # 2. Finance & Invoicing
    # ---------------------------------------------------------------------

    def _get_finance_data(self, date_from, date_to, company, installed):
        revenue = 0.0
        revenue_ly = 0.0

        expenses = 0.0
        expenses_ly = 0.0

        cash = 0.0
        ar_total = 0.0
        ap_total = 0.0

        overdue_amount = 0.0
        overdue_count = 0
        dso = 0.0

        bank_accounts = []
        overdue_customers = []

        if installed['account']:
            try:
                revenue, expenses = self._calc_revenue_expense(
                    date_from,
                    date_to,
                    company,
                )

                ly_from = date_from - relativedelta(years=1)
                ly_to = date_to - relativedelta(years=1)

                revenue_ly, expenses_ly = self._calc_revenue_expense(
                    ly_from,
                    ly_to,
                    company,
                )

                cash = self._calc_cash(
                    date_to,
                    company,
                )

                ar_total, ap_total = self._calc_ar_ap(
                    date_to,
                    company,
                )

                # -----------------------------------------------------
                # Bank and cash accounts
                # -----------------------------------------------------

                journals = self.env['account.journal'].search([
                    ('company_id', '=', company.id),
                    ('type', 'in', ('bank', 'cash')),
                ])

                for journal in journals:
                    balance = 0.0

                    if journal.default_account_id:
                        lines = self.env['account.move.line'].search([
                            (
                                'account_id',
                                '=',
                                journal.default_account_id.id,
                            ),
                            ('parent_state', '=', 'posted'),
                            ('date', '<=', date_to),
                        ])

                        balance = sum(
                            lines.mapped('balance')
                        )

                    if (
                        balance == 0.0
                        and 'account.payment' in self.env
                    ):
                        payments = self.env['account.payment'].search([
                            ('journal_id', '=', journal.id),
                            ('state', '=', 'paid'),
                            ('date', '<=', date_to),
                        ])

                        balance = sum(
                            p.amount
                            if p.payment_type == 'inbound'
                            else -p.amount
                            for p in payments
                        )

                    bank_accounts.append({
                        'name': journal.name,
                        'amount': float(balance),
                    })

                # -----------------------------------------------------
                # Overdue invoices
                # -----------------------------------------------------

                overdue_recs = self._get_overdue_moves(company)

                if overdue_recs:
                    overdue_count = len(overdue_recs)

                    overdue_amount = sum(
                        overdue_recs.mapped('amount_residual')
                    )

                    days_in_period = max(
                        1,
                        (date_to - date_from).days + 1,
                    )

                    if revenue > 0:
                        dso = round(
                            (ar_total / revenue) * days_in_period,
                            1,
                        )

                    grouped = {}

                    for move in overdue_recs:
                        if move.partner_id:
                            grouped.setdefault(
                                move.partner_id,
                                [],
                            ).append(move)

                    sorted_customers = sorted(
                        grouped.items(),
                        key=lambda item: sum(
                            m.amount_residual
                            for m in item[1]
                        ),
                        reverse=True,
                    )[:5]

                    for partner, moves in sorted_customers:
                        latest_invoice = moves[0]

                        overdue_customers.append({
                            'id': partner.id,
                            'name': partner.name or 'Unknown',
                            'code': f'cust-{partner.id}',
                            'latest_invoice': (
                                latest_invoice.name
                                or 'INV/---'
                            ),
                            'contact': (
                                partner.contact_address_inline
                                or partner.phone
                                or partner.email
                                or 'Accounting Contact'
                            ),
                            'email': (
                                partner.email
                                or 'invoices@partner.com'
                            ),
                            'delay_days': max(
                                (
                                    fields.Date.context_today(self)
                                    - (
                                        latest_invoice.invoice_date_due
                                        or latest_invoice.invoice_date
                                        or fields.Date.context_today(self)
                                    )
                                ).days,
                                0,
                            ),
                            'amount': sum(
                                m.amount_residual
                                for m in moves
                            ),
                        })

            except Exception as e:
                _logger.warning(
                    "CEO Dashboard Finance: error: %s",
                    e,
                )

        net_profit = revenue - expenses

        net_margin = (
            round((net_profit / revenue) * 100, 1)
            if revenue
            else 0.0
        )

        revenue_growth_pct = (
            round(
                ((revenue - revenue_ly) / revenue_ly) * 100,
                1,
            )
            if revenue_ly > 0
            else 0.0
        )

        expenses_growth_pct = (
            round(
                ((expenses - expenses_ly) / expenses_ly) * 100,
                1,
            )
            if expenses_ly > 0
            else 0.0
        )

        return {
            'total_revenue': revenue,
            'revenue_ly': revenue_ly,
            'revenue_growth_pct': revenue_growth_pct,

            'total_expenses': expenses,
            'expenses_ly': expenses_ly,
            'expenses_growth_pct': expenses_growth_pct,

            'net_profit': net_profit,
            'net_margin': net_margin,

            'cash': cash,
            'bank_accounts': bank_accounts,

            'ar_total': ar_total,
            'ap_total': ap_total,
            'net_receivable_surplus': ar_total - ap_total,

            'overdue_amount': overdue_amount,
            'overdue_count': overdue_count,

            'overdue_ar_pct': (
                round(
                    (overdue_amount / ar_total) * 100,
                    1,
                )
                if ar_total > 0
                else 0.0
            ),

            'dso': dso,
            'overdue_customers': overdue_customers,
        }

    # ---------------------------------------------------------------------
    # 3. Sales & CRM
    # ---------------------------------------------------------------------

    def _get_sales_data(self, date_from, date_to, company, installed):
        today = fields.Date.context_today(self)

        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)
        year_start = today.replace(month=1, day=1)

        month_actual = 0.0

        orders_today = 0
        orders_week = 0
        orders_month = 0
        orders_ytd = 0

        pipeline_value = 0.0
        win_rate = 0.0
        avg_deal_size = 0.0
        new_leads = 0

        top_customers = []
        closing_opportunities = []

        # -------------------------------------------------------------
        # Sales
        # -------------------------------------------------------------

        if installed['sale']:
            try:
                Sale = self.env['sale.order']

                orders_today = Sale.search_count([
                    ('company_id', '=', company.id),
                    ('state', '=', 'sale'),
                    ('date_order', '>=', f"{today} 00:00:00"),
                ])

                orders_week = Sale.search_count([
                    ('company_id', '=', company.id),
                    ('state', '=', 'sale'),
                    ('date_order', '>=', f"{week_start} 00:00:00"),
                ])

                orders_month = Sale.search_count([
                    ('company_id', '=', company.id),
                    ('state', '=', 'sale'),
                    ('date_order', '>=', f"{month_start} 00:00:00"),
                ])

                orders_ytd = Sale.search_count([
                    ('company_id', '=', company.id),
                    ('state', '=', 'sale'),
                    ('date_order', '>=', f"{year_start} 00:00:00"),
                ])

                sales_month = Sale.search([
                    ('company_id', '=', company.id),
                    ('state', '=', 'sale'),
                    ('date_order', '>=', f"{month_start} 00:00:00"),
                ])

                month_actual = sum(
                    sales_month.mapped('amount_total')
                )

                # -----------------------------------------------------
                # Top customers
                # -----------------------------------------------------

                all_sales = Sale.search([
                    ('company_id', '=', company.id),
                    ('state', '=', 'sale'),
                ])

                if all_sales:
                    avg_deal_size = round(
                        sum(
                            all_sales.mapped('amount_total')
                        ) / len(all_sales),
                        2,
                    )

                    partner_map = {}

                    for order in all_sales:
                        partner = order.partner_id

                        if partner:
                            entry = partner_map.setdefault(
                                partner.id,
                                {
                                    'name': partner.name or 'Unknown',
                                    'category': (
                                        partner.category_id[0].name
                                        if partner.category_id
                                        else 'Direct Customer'
                                    ),
                                    'deals': 0,
                                    'amount': 0.0,
                                },
                            )

                            entry['deals'] += 1
                            entry['amount'] += order.amount_total

                    total_amount = (
                        sum(
                            entry['amount']
                            for entry in partner_map.values()
                        )
                        or 1.0
                    )

                    sorted_customers = sorted(
                        partner_map.values(),
                        key=lambda x: x['amount'],
                        reverse=True,
                    )[:5]

                    for customer in sorted_customers:
                        customer['pct'] = round(
                            (
                                customer['amount']
                                / total_amount
                            ) * 100,
                            1,
                        )

                    top_customers = sorted_customers

            except Exception as e:
                _logger.warning(
                    "CEO Dashboard Sales: error: %s",
                    e,
                )

        # -------------------------------------------------------------
        # CRM
        # -------------------------------------------------------------

        if installed['crm']:
            try:
                Lead = self.env['crm.lead']

                won = Lead.search_count([
                    ('company_id', 'in', (company.id, False)),
                    ('stage_id.is_won', '=', True),
                ])

                lost = Lead.search_count([
                    ('company_id', 'in', (company.id, False)),
                    ('active', '=', False),
                    ('probability', '=', 0),
                ])

                total_deals = won + lost

                win_rate = (
                    round(
                        (won / total_deals) * 100,
                        1,
                    )
                    if total_deals > 0
                    else 0.0
                )

                new_leads = Lead.search_count([
                    ('company_id', 'in', (company.id, False)),
                    ('create_date', '>=', f"{week_start} 00:00:00"),
                ])

                active_opportunities = Lead.search([
                    ('company_id', 'in', (company.id, False)),
                    ('type', '=', 'opportunity'),
                    ('active', '=', True),
                    ('stage_id.is_won', '=', False),
                ])

                pipeline_value = sum(
                    active_opportunities.mapped(
                        'expected_revenue'
                    )
                )

                closing_leads = Lead.search([
                    ('company_id', 'in', (company.id, False)),
                    ('type', '=', 'opportunity'),
                    ('active', '=', True),
                    ('stage_id.is_won', '=', False),
                ], order='expected_revenue desc', limit=5)

                for lead in closing_leads:
                    closing_opportunities.append({
                        'title': lead.name or 'Opportunity',
                        'customer': (
                            lead.partner_id.name
                            or lead.contact_name
                            or 'Prospective Customer'
                        ),
                        'rep': (
                            lead.user_id.name
                            or 'Unassigned'
                        ),
                        'amount': float(
                            lead.expected_revenue or 0.0
                        ),
                        'prob': int(
                            lead.probability or 0
                        ),
                        'closing_date': (
                            fields.Date.to_string(
                                lead.date_deadline
                            )
                            if lead.date_deadline
                            else 'Ongoing'
                        ),
                        'stage': (
                            lead.stage_id.name
                            or 'In Progress'
                        ),
                    })

            except Exception as e:
                _logger.warning(
                    "CEO Dashboard CRM: error: %s",
                    e,
                )

        return {
            'month_actual': month_actual,

            'orders_today': orders_today,
            'orders_week': orders_week,
            'orders_month': orders_month,
            'orders_ytd': orders_ytd,

            'pipeline_value': pipeline_value,
            'win_rate': win_rate,
            'avg_deal_size': avg_deal_size,
            'new_leads': new_leads,

            'top_customers': top_customers,
            'closing_opportunities': closing_opportunities,

            'weighted_closing_sum': sum(
                opportunity['amount']
                * (opportunity['prob'] / 100.0)
                for opportunity in closing_opportunities
            ),
        }

    # ---------------------------------------------------------------------
    # 4. Inventory & Operations
    # ---------------------------------------------------------------------

    def _get_inventory_data(
        self,
        date_from,
        date_to,
        company,
        installed,
    ):
        total_value = 0.0
        low_stock_count = 0
        pending_deliveries = 0
        pending_receipts = 0
        turnover_rate = 0.0
        overdue_po = 0

        reorder_products = []

        if installed['stock']:
            try:
                StockQuant = self.env['stock.quant']

                quants = StockQuant.search([
                    ('company_id', '=', company.id),
                    ('location_id.usage', '=', 'internal'),
                ])

                total_value = sum(
                    q.quantity * q.product_id.standard_price
                    for q in quants
                )

                StockPicking = self.env['stock.picking']

                pending_deliveries = StockPicking.search_count([
                    ('company_id', '=', company.id),
                    ('picking_type_code', '=', 'outgoing'),
                    ('state', 'not in', ('done', 'cancel')),
                ])

                pending_receipts = StockPicking.search_count([
                    ('company_id', '=', company.id),
                    ('picking_type_code', '=', 'incoming'),
                    ('state', 'not in', ('done', 'cancel')),
                ])

                # ---------------------------------------------------------
                # Reorder products
                # ---------------------------------------------------------

                if 'stock.warehouse.orderpoint' in self.env:
                    orderpoints = self.env[
                        'stock.warehouse.orderpoint'
                    ].search([
                        ('company_id', '=', company.id),
                    ], limit=5)

                    for orderpoint in orderpoints:
                        product = orderpoint.product_id

                        if (
                            product.qty_available
                            < orderpoint.product_min_qty
                        ):
                            low_stock_count += 1

                            reorder_products.append({
                                'sku': (
                                    product.default_code
                                    or f'PROD-{product.id}'
                                ),
                                'name': product.name,
                                'vendor': (
                                    product.seller_ids[0].partner_id.name
                                    if product.seller_ids
                                    else 'Standard Supplier'
                                ),
                                'on_hand': product.qty_available,
                                'min_qty': orderpoint.product_min_qty,
                                'max_qty': orderpoint.product_max_qty,
                                'cost': product.standard_price,
                            })

            except Exception as e:
                _logger.warning(
                    "CEO Dashboard Inventory: stock error: %s",
                    e,
                )

        # -------------------------------------------------------------
        # Purchase
        # -------------------------------------------------------------

        if installed['purchase']:
            try:
                today = fields.Date.context_today(self)

                overdue_po = self.env[
                    'purchase.order'
                ].search_count([
                    ('company_id', '=', company.id),
                    ('state', 'in', ('purchase', 'done')),
                    ('date_planned', '<', f"{today} 00:00:00"),
                ])

            except Exception as e:
                _logger.warning(
                    "CEO Dashboard Inventory: purchase error: %s",
                    e,
                )

        return {
            'total_value': total_value,
            'valuation_method': 'Standard / Automated',
            'low_stock_count': low_stock_count,
            'pending_deliveries': pending_deliveries,
            'pending_receipts': pending_receipts,
            'turnover_rate': turnover_rate,
            'overdue_po': overdue_po,
            'reorder_products': reorder_products,
        }

    # ---------------------------------------------------------------------
    # 5. Project & Operations
    # ---------------------------------------------------------------------

    def _get_project_data(
        self,
        date_from,
        date_to,
        company,
        installed,
    ):
        today = fields.Date.context_today(self)

        overdue_tasks = 0
        tasks_due_today = 0
        projects_over_budget = 0

        projects = []

        if installed['project']:
            try:
                Task = self.env['project.task']

                overdue_tasks = Task.search_count([
                    ('company_id', 'in', (company.id, False)),
                    ('date_deadline', '<', f"{today} 00:00:00"),
                    ('is_closed', '=', False),
                ])

                tasks_due_today = Task.search_count([
                    ('company_id', 'in', (company.id, False)),
                    ('date_deadline', '>=', f"{today} 00:00:00"),
                    ('date_deadline', '<=', f"{today} 23:59:59"),
                    ('is_closed', '=', False),
                ])

                Project = self.env['project.project']

                project_records = Project.search([
                    ('company_id', 'in', (company.id, False)),
                    ('active', '=', True),
                ], limit=5)

                for project in project_records:
                    allocated_hours = getattr(
                        project,
                        'allocated_hours',
                        0.0,
                    ) or 0.0

                    projects.append({
                        'name': project.name,
                        'lead': (
                            project.user_id.name
                            or 'Unassigned'
                        ),
                        'spent_hours': 0.0,
                        'allocated_hours': round(
                            allocated_hours,
                            1,
                        ),
                        'status': 'Active',
                        'health': 'good',
                    })

            except Exception as e:
                _logger.warning(
                    "CEO Dashboard Project: error: %s",
                    e,
                )

        return {
            'overdue_tasks': overdue_tasks,
            'tasks_due_today': tasks_due_today,
            'projects_over_budget': projects_over_budget,
            'billable_hours': 0.0,
            'billable_target': 0.0,
            'projects': projects,
            'tickets': [],
        }

    # ---------------------------------------------------------------------
    # Accounting Calculation Helpers
    # ---------------------------------------------------------------------

    def _calc_revenue_expense(
        self,
        date_from,
        date_to,
        company,
    ):
        domain_base = [
            ('company_id', '=', company.id),
            ('parent_state', '=', 'posted'),
            ('date', '>=', date_from),
            ('date', '<=', date_to),
        ]

        revenue_domain = domain_base + [
            (
                'account_id.account_type',
                'in',
                ['income', 'income_other'],
            ),
        ]

        expense_domain = domain_base + [
            (
                'account_id.account_type',
                'in',
                [
                    'expense',
                    'expense_depreciation',
                    'expense_direct_cost',
                ],
            ),
        ]

        revenue_result = self.env[
            'account.move.line'
        ]._read_group(
            revenue_domain,
            [],
            ['balance:sum'],
        )

        expense_result = self.env[
            'account.move.line'
        ]._read_group(
            expense_domain,
            [],
            ['balance:sum'],
        )

        revenue_value = (
            revenue_result[0][0]
            if (
                revenue_result
                and revenue_result[0]
                and revenue_result[0][0] is not None
            )
            else 0.0
        )

        expense_value = (
            expense_result[0][0]
            if (
                expense_result
                and expense_result[0]
                and expense_result[0][0] is not None
            )
            else 0.0
        )

        revenue = float(-revenue_value or 0.0)
        expenses = float(expense_value or 0.0)

        # -------------------------------------------------------------
        # Fallback to invoices and vendor bills
        # -------------------------------------------------------------

        if revenue == 0.0:
            invoices = self.env['account.move'].search([
                ('company_id', '=', company.id),
                (
                    'move_type',
                    'in',
                    ('out_invoice', 'out_refund'),
                ),
                ('state', '=', 'posted'),
                ('invoice_date', '>=', date_from),
                ('invoice_date', '<=', date_to),
            ])

            revenue = sum(
                (
                    move.amount_untaxed_signed
                    if move.move_type == 'out_invoice'
                    else -move.amount_untaxed_signed
                )
                for move in invoices
            )

        if expenses == 0.0:
            bills = self.env['account.move'].search([
                ('company_id', '=', company.id),
                (
                    'move_type',
                    'in',
                    ('in_invoice', 'in_refund'),
                ),
                ('state', '=', 'posted'),
                ('invoice_date', '>=', date_from),
                ('invoice_date', '<=', date_to),
            ])

            expenses = sum(
                (
                    bill.amount_untaxed_signed
                    if bill.move_type == 'in_invoice'
                    else -bill.amount_untaxed_signed
                )
                for bill in bills
            )

        return (
            float(revenue or 0.0),
            float(expenses or 0.0),
        )

    # ---------------------------------------------------------------------

    def _calc_cash(self, date_to, company):
        domain = [
            ('company_id', '=', company.id),
            ('parent_state', '=', 'posted'),
            ('date', '<=', date_to),
            ('account_id.account_type', '=', 'asset_cash'),
        ]

        result = self.env[
            'account.move.line'
        ]._read_group(
            domain,
            [],
            ['balance:sum'],
        )

        value = (
            result[0][0]
            if (
                result
                and result[0]
                and result[0][0] is not None
            )
            else 0.0
        )

        value = float(value or 0.0)

        # Fallback to payments.
        if value == 0.0 and 'account.payment' in self.env:
            payments = self.env['account.payment'].search([
                ('company_id', '=', company.id),
                ('journal_id.type', 'in', ('bank', 'cash')),
                ('state', '=', 'paid'),
                ('date', '<=', date_to),
            ])

            value = float(
                sum(
                    payment.amount
                    if payment.payment_type == 'inbound'
                    else -payment.amount
                    for payment in payments
                )
            )

        return value

    # ---------------------------------------------------------------------

    def _calc_ar_ap(self, date_to, company):
        AccountMove = self.env['account.move']

        domain_base = [
            ('company_id', '=', company.id),
            ('state', '=', 'posted'),
            ('invoice_date', '<=', date_to),
            (
                'payment_state',
                'in',
                ('not_paid', 'partial'),
            ),
        ]

        ar_moves = AccountMove.search(
            domain_base + [
                (
                    'move_type',
                    'in',
                    ('out_invoice', 'out_refund'),
                ),
            ]
        )

        ar = sum(
            (
                move.amount_residual
                if move.move_type == 'out_invoice'
                else -move.amount_residual
            )
            for move in ar_moves
        )

        ap_moves = AccountMove.search(
            domain_base + [
                (
                    'move_type',
                    'in',
                    ('in_invoice', 'in_refund'),
                ),
            ]
        )

        ap = sum(
            (
                move.amount_residual
                if move.move_type == 'in_invoice'
                else -move.amount_residual
            )
            for move in ap_moves
        )

        return (
            float(ar or 0.0),
            float(ap or 0.0),
        )

    # ---------------------------------------------------------------------

    def _get_overdue_moves(self, company):
        today = fields.Date.context_today(self)

        return self.env['account.move'].search([
            ('company_id', '=', company.id),
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            (
                'payment_state',
                'in',
                ('not_paid', 'partial'),
            ),
            ('invoice_date_due', '<', today),
        ], order='invoice_date_due asc')