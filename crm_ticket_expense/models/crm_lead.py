
from odoo import models, fields, api

class CrmLead(models.Model):
    _inherit = 'crm.lead'

    expense_ids = fields.One2many(
        'deal.expense',
        'lead_id',
        string='Expenses'
    )

    payment_move_ids = fields.One2many(
        'account.move',
        'lead_id',
        string='Payments',
        domain=[('move_type', 'in', ('out_receipt', 'out_invoice'))],
        readonly=True
    )

    vendor_payment_move_ids = fields.One2many(
        'account.move',
        'lead_id',
        string='Payments',
        domain=[('move_type', 'in', ('in_receipt', 'in_invoice'))],
        readonly=True
    )

    expense_count = fields.Integer(compute="_compute_expense_count")
    company_currency_id = fields.Many2one(
    'res.currency',
    related='company_id.currency_id',
    store=True,
    readonly=True
)
    invoice_amount_due = fields.Monetary(compute="_compute_invoice_due", currency_field='company_currency_id')

        # -------------------------------------------------
    # Core Financial Fields
    # -------------------------------------------------
    ticket_invoiced_amount = fields.Monetary(
        compute='_compute_ticket_financials',
        currency_field='company_currency_id',
        string='Invoiced Revenue'
    )

    ticket_collected_amount = fields.Monetary(
        compute='_compute_ticket_financials',
        currency_field='company_currency_id',
        string='Collected Amount'
    )

    ticket_expense_amount = fields.Monetary(
        compute='_compute_ticket_financials',
        currency_field='company_currency_id',
        string='Expenses'
    )

    ticket_outstanding_amount = fields.Monetary(
        compute='_compute_ticket_financials',
        currency_field='company_currency_id',
        string='Outstanding'
    )

    ticket_accounting_margin = fields.Monetary(
        compute='_compute_ticket_financials',
        currency_field='company_currency_id',
        string='Accounting Margin'
    )

    ticket_cash_margin = fields.Monetary(
        compute='_compute_ticket_financials',
        currency_field='company_currency_id',
        string='Cash Margin'
    )

    ticket_collection_ratio = fields.Float(
    compute='_compute_ticket_collection_ratio',
    string='Collection %'
)

    ticket_financial_status = fields.Selection(
        [
            ('profit', 'Profit'),
            ('loss', 'Loss'),
            ('pending', 'Pending Collection'),
            ('not_started', 'No Financial Activity')
        ],
        compute='_compute_ticket_financial_status',
        string='Financial Status'
    )

    @api.depends(
    'ticket_invoiced_amount',
    'ticket_collected_amount',
    'ticket_expense_amount',
    'ticket_outstanding_amount',
    'ticket_accounting_margin',
    'payment_move_ids',
    'vendor_payment_move_ids',
    'invoice_ids',
    'expense_ids'
    )
    def _compute_ticket_financial_status(self):
        for lead in self:
            if not lead.ticket_invoiced_amount and not lead.ticket_collected_amount:
                lead.ticket_financial_status = 'not_started'
            elif lead.ticket_outstanding_amount > 0:
                lead.ticket_financial_status = 'pending'
            elif lead.ticket_accounting_margin < 0:
                lead.ticket_financial_status = 'loss'
            else:
                lead.ticket_financial_status = 'profit'

    @api.depends('payment_move_ids', 'vendor_payment_move_ids', 'invoice_ids', 'expense_ids')
    def _compute_ticket_collection_ratio(self):
        for lead in self:
            if lead.ticket_invoiced_amount:
                lead.ticket_collection_ratio = (
                    lead.ticket_collected_amount / lead.ticket_invoiced_amount
                ) * 100
            else:
                lead.ticket_collection_ratio = 0.0

    @api.depends('payment_move_ids', 'vendor_payment_move_ids', 'invoice_ids', 'expense_ids')
    def _compute_ticket_financials(self):
        AccountMove = self.env['account.move']
        DealExpense = self.env['deal.expense']

        for lead in self:
            # -----------------------------
            # Invoiced Revenue
            # -----------------------------
            invoices = AccountMove.search([
                ('lead_id', '=', lead.id),
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
            ])
            invoiced_amount = sum(invoices.mapped('amount_total'))

            # -----------------------------
            # Collected Amount (Payments)
            # -----------------------------
            # Customer Invoice
            payments = AccountMove.search([
                ('lead_id', '=', lead.id),
                ('move_type', 'in', ('out_receipt', 'out_invoice')),
                ('state', '=', 'posted'),
            ])
            # Vendor Bills
            vendor_payments = AccountMove.search([
                ('lead_id', '=', lead.id),
                ('move_type', '=', 'in_invoice'),
                ('state', '=', 'posted'),
            ])
            collected_amount = sum(payments.mapped('amount_total')) - sum(payments.mapped('amount_residual'))

            # -----------------------------
            # Expenses
            # -----------------------------
            expenses = DealExpense.search([
                ('lead_id', '=', lead.id),
                ('state', '=', 'posted'),
            ])
            vendor_amount_total = sum(vendor_payments.mapped('amount_total')) - sum(vendor_payments.mapped('amount_residual'))
            expense_amount = sum(expenses.mapped('amount') + [vendor_amount_total])

            # -----------------------------
            # Derived Values
            # -----------------------------
            lead.ticket_invoiced_amount = invoiced_amount
            lead.ticket_collected_amount = collected_amount
            lead.ticket_expense_amount = expense_amount
            lead.ticket_outstanding_amount = invoiced_amount - collected_amount
            lead.ticket_accounting_margin = invoiced_amount - expense_amount
            lead.ticket_cash_margin = collected_amount - expense_amount

    @api.depends('payment_move_ids', 'vendor_payment_move_ids', 'invoice_ids')
    def _compute_invoice_due(self):
        for lead in self:
            invoices = self.env['account.move'].search([
                ('lead_id', '=', lead.id),
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
            ])
            lead.invoice_amount_due = sum(invoices.mapped('amount_residual'))

    @api.depends('expense_ids')
    def _compute_expense_count(self):
        for lead in self:
            lead.expense_count = self.env['deal.expense'].search_count([
                ('lead_id', '=', lead.id)
            ])


    def action_log_expense(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Log Expense',
            'res_model': 'deal.expense',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_lead_id': self.id,
                'default_employee_id': self.env.user.employee_id.id if self.env.user.employee_id else False,
                'default_analytic_distribution': {self.analytic_account_id.id: 100.0} if self.analytic_account_id else False,
            }
        }


    def action_receive_payment(self):
        self.ensure_one()

        invoice = self.env['account.move'].search([
            ('lead_id', '=', self.id),
            ('move_type', '=', 'out_invoice'),
            ('state', '!=', 'cancel'),
        ], limit=1)

        if not invoice:
            invoice = self._create_invoice_from_ticket()

        return {
            'type': 'ir.actions.act_window',
            'name': 'Register Payment',
            'res_model': 'account.payment.register',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_model': 'account.move',
                'active_ids': invoice.ids,
            }
        }


    def _create_invoice_from_ticket(self):
        self.ensure_one()
        return self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'lead_id': self.id,
            'invoice_line_ids': [(0, 0, {
                'name': self.name,
                'quantity': 1,
                'price_unit': self.expected_revenue or 0.0,
            })],
        })
