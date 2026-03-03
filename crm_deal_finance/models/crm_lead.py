from odoo import models, fields, api
from odoo.exceptions import UserError

class CrmLead(models.Model):
    _inherit = 'crm.lead'

    # -------------------------------------------------
    # RELATIONS
    # -------------------------------------------------

    sale_order_ids = fields.One2many(
        'sale.order',
        'opportunity_id',
        string='Sale Orders'
    )

    invoice_ids = fields.One2many(
        'account.move',
        'lead_id',
        domain=[('move_type', '=', 'out_invoice')],
        string='Invoices'
    )

    vendor_bill_ids = fields.One2many(
        'account.move',
        'lead_id',
        domain=[('move_type', '=', 'in_invoice')],
        string='Vendor Bills'
    )

    expense_ids = fields.One2many(
        'hr.expense',
        'lead_id',
        string='Expenses'
    )


    # -------------------------------------------------
    # CURRENCY
    # -------------------------------------------------

    company_currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        store=True,
        readonly=True
    )

    # -------------------------------------------------
    # FINANCIAL TOTALS
    # -------------------------------------------------

    ticket_invoiced_amount = fields.Monetary(
        compute='_compute_financials',
        currency_field='company_currency_id'
    )

    ticket_collected_amount = fields.Monetary(
        compute='_compute_financials',
        currency_field='company_currency_id'
    )

    ticket_expense_amount = fields.Monetary(
        compute='_compute_financials',
        currency_field='company_currency_id'
    )

    ticket_outstanding_amount = fields.Monetary(
        compute='_compute_financials',
        currency_field='company_currency_id'
    )

    ticket_accounting_margin = fields.Monetary(
        compute='_compute_financials',
        currency_field='company_currency_id'
    )

    ticket_cash_margin = fields.Monetary(
        compute='_compute_financials',
        currency_field='company_currency_id'
    )

    ticket_collection_ratio = fields.Float(
        compute='_compute_financials'
    )

    # -------------------------------------------------
    # BUTTON VISIBILITY
    # -------------------------------------------------

    can_confirm_quotation = fields.Boolean(
        compute='_compute_button_visibility'
    )

    can_create_invoice = fields.Boolean(
        compute='_compute_button_visibility'
    )

    can_register_payment = fields.Boolean(
        compute='_compute_button_visibility'
    )

    can_register_vendor_payment = fields.Boolean(
        compute='_compute_button_visibility'
    )

    # -------------------------------------------------
    # COMPUTE FINANCIALS
    # -------------------------------------------------

    @api.depends('invoice_ids', 'vendor_bill_ids', 'expense_ids.state', 'expense_ids.total_amount')
    def _compute_financials(self):
        for lead in self:

            invoices = lead.invoice_ids.filtered(
                lambda inv: inv.state == 'posted'
            )

            invoiced = sum(invoices.mapped('amount_total'))
            collected = sum(
                inv.amount_total - inv.amount_residual
                for inv in invoices
            )

            outstanding = invoiced - collected

            vendor_paid = sum(
                bill.amount_total - bill.amount_residual
                for bill in lead.vendor_bill_ids.filtered(lambda b: b.state == 'posted')
            )

            expense_amount = sum(
                lead.expense_ids.filtered(
                    lambda e: e.state in ('approved', 'done')
                ).mapped('total_amount')
            ) + vendor_paid

            lead.ticket_invoiced_amount = invoiced
            lead.ticket_collected_amount = collected
            lead.ticket_outstanding_amount = outstanding
            lead.ticket_expense_amount = expense_amount
            lead.ticket_accounting_margin = invoiced - expense_amount
            lead.ticket_cash_margin = collected - expense_amount
            lead.ticket_collection_ratio = (
                (collected / invoiced) * 100 if invoiced else 0.0
            )

    # -------------------------------------------------
    # COMPUTE BUTTON VISIBILITY
    # -------------------------------------------------

    @api.depends('sale_order_ids', 'invoice_ids', 'ticket_outstanding_amount')
    def _compute_button_visibility(self):
        for lead in self:
            lead.can_confirm_quotation = any(
                order.state == 'draft' for order in lead.sale_order_ids
            )

            lead.can_create_invoice = any(
                order.invoice_status != 'invoiced'
                for order in lead.sale_order_ids
            )

            lead.can_register_payment = lead.ticket_outstanding_amount > 0

            lead.can_register_vendor_payment = any(
            bill.state == 'posted' and bill.amount_residual > 0
            for bill in lead.vendor_bill_ids
        )

    # -------------------------------------------------
    # ACTIONS
    # -------------------------------------------------

    def action_confirm_quotation(self):
        self.ensure_one()
        draft_orders = self.sale_order_ids.filtered(
            lambda o: o.state == 'draft'
        )
        if not draft_orders:
            raise UserError("No draft quotations found.")
        draft_orders.action_confirm()

    def action_create_invoice(self):
        self.ensure_one()
        orders = self.sale_order_ids.filtered(
            lambda o: o.state == 'sale'
        )
        if not orders:
            raise UserError("No confirmed Sale Orders found.")
        invoices = orders._create_invoices()
        invoices.write({'lead_id': self.id})
        invoices.action_post()

    def action_register_payment(self):
        self.ensure_one()
        invoices = self.invoice_ids.filtered(
            lambda inv: inv.state == 'posted' and inv.amount_residual > 0
        )
        if not invoices:
            raise UserError("No outstanding invoices found.")

        return {
            'name': 'Register Payment',
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment.register',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_model': 'account.move',
                'active_ids': invoices.ids,
            },
        }

    def action_register_vendor_payment(self):
        self.ensure_one()

        vendor_bills = self.vendor_bill_ids.filtered(
            lambda bill: bill.state == 'posted' and bill.amount_residual > 0
        )

        if not vendor_bills:
            raise UserError("No outstanding vendor bills found.")

        return {
            'name': 'Register Vendor Payment',
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment.register',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_model': 'account.move',
                'active_ids': vendor_bills.ids,
            },
        }

    def action_create_vendor_bill(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Vendor Bill',
            'res_model': 'account.move',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_move_type': 'in_invoice',
                'default_lead_id': self.id,
            }
        }

    def action_log_expense(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Log Expense',
            'res_model': 'hr.expense',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_lead_id': self.id,
                'default_analytic_distribution': {self.analytic_account_id.id: 100.0} if self.analytic_account_id else False,
            }
        }

    def action_open_finance_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Deal Financial Actions',
            'res_model': 'deal.finance.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_lead_id': self.id,
            }
        }
