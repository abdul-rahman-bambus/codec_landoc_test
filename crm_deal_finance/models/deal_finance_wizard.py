from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare


class DealFinanceWizard(models.TransientModel):
    _name = 'deal.finance.wizard'
    _description = 'Deal Financial Actions Wizard'

    # ---------------------------------------------------------
    # CORE CONTEXT
    # ---------------------------------------------------------
    lead_id = fields.Many2one('crm.lead', readonly=True)
    partner_id = fields.Many2one('res.partner', readonly=True)
    company_id = fields.Many2one('res.company', readonly=True)
    analytic_account_id = fields.Many2one('account.analytic.account', readonly=True)
    sale_order_id = fields.Many2one('sale.order', readonly=True)

    # ---------------------------------------------------------
    # LEAD LEVEL FINANCIALS (READONLY)
    # ---------------------------------------------------------
    total_quoted_amount = fields.Monetary(
        string="Total Quoted",
        compute="_compute_financials",
        readonly=True
    )
    total_invoiced_amount = fields.Monetary(
        string="Total Invoiced",
        compute="_compute_financials",
        readonly=True
    )
    total_paid_amount = fields.Monetary(
        string="Total Paid",
        compute="_compute_financials",
        readonly=True
    )
    total_outstanding_amount = fields.Monetary(
        string="Outstanding",
        compute="_compute_financials",
        readonly=True
    )
    currency_id = fields.Many2one('res.currency', readonly=True)

    # ---------------------------------------------------------
    # ACTION TOGGLES
    # ---------------------------------------------------------
    create_invoice = fields.Boolean()
    create_payment = fields.Boolean()
    create_vendor_bill = fields.Boolean()
    create_vendor_payment = fields.Boolean()
    create_expense = fields.Boolean()

    # ---------------------------------------------------------
    # CUSTOMER PAYMENT
    # ---------------------------------------------------------
    customer_payment_amount = fields.Float()
    customer_payment_journal_id = fields.Many2one(
        'account.journal',
        domain="[('type','in',('bank','cash'))]"
    )

    # ---------------------------------------------------------
    # PLACEHOLDERS (NEXT PHASE)
    # ---------------------------------------------------------
    vendor_id = fields.Many2one('res.partner')
    vendor_bill_amount = fields.Float()
    vendor_payment_amount = fields.Float()
    vendor_payment_journal_id = fields.Many2one('account.journal')

    expense_amount = fields.Float()
    expense_journal_id = fields.Many2one('account.journal')

    # ---------------------------------------------------------
    # DEFAULTS
    # ---------------------------------------------------------
    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        lead = self.env['crm.lead'].browse(self.env.context.get('default_lead_id'))

        if lead:
            res.update({
                'lead_id': lead.id,
                'partner_id': lead.partner_id.id,
                'company_id': lead.company_id.id,
                'analytic_account_id': lead.analytic_account_id.id,
                'sale_order_id': lead.order_ids[:1].id,
            })
        return res

    # ---------------------------------------------------------
    # COMPUTE LEAD FINANCIALS
    # ---------------------------------------------------------
    def _compute_financials(self):
        for wiz in self:
            wiz.total_quoted_amount = 0.0
            wiz.total_invoiced_amount = 0.0
            wiz.total_paid_amount = 0.0
            wiz.total_outstanding_amount = 0.0
            wiz.currency_id = False

            if not wiz.lead_id:
                continue

            sale_orders = wiz.lead_id.order_ids

            invoices = self.env['account.move'].search([
                ('move_type', '=', 'out_invoice'),
                ('invoice_origin', 'in', sale_orders.mapped('name')),
                ('state', '=', 'posted'),
            ])

            wiz.total_quoted_amount = sum(sale_orders.mapped('amount_total'))
            wiz.total_invoiced_amount = sum(invoices.mapped('amount_total'))
            wiz.total_paid_amount = sum(
                inv.amount_total - inv.amount_residual for inv in invoices
            )
            wiz.total_outstanding_amount = (
                wiz.total_invoiced_amount - wiz.total_paid_amount
            )

            wiz.currency_id = (
                invoices[:1].currency_id.id
                or wiz.company_id.currency_id.id
            )

    # ---------------------------------------------------------
    # VIEW SALE ORDERS (FORM / LIST)
    # ---------------------------------------------------------
    def action_open_sale_orders(self):
        self.ensure_one()
        orders = self.lead_id.order_ids

        if not orders:
            return False

        if len(orders) == 1:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'sale.order',
                'res_id': orders.id,
                'view_mode': 'form',
            }

        return {
            'type': 'ir.actions.act_window',
            'name': 'Sale Orders',
            'res_model': 'sale.order',
            'view_mode': 'list,form',
            'domain': [('opportunity_id', '=', self.lead_id.id)],
        }

    # ---------------------------------------------------------
    # VIEW INVOICES (FORM / LIST)
    # ---------------------------------------------------------
    def action_open_invoices(self):
        self.ensure_one()

        invoices = self.env['account.move'].search([
            ('move_type', '=', 'out_invoice'),
            ('invoice_origin', 'in', self.lead_id.order_ids.mapped('name')),
            ('state', '!=', 'cancel'),
        ])

        if not invoices:
            return False

        if len(invoices) == 1:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'res_id': invoices.id,
                'view_mode': 'form',
            }

        return {
            'type': 'ir.actions.act_window',
            'name': 'Invoices',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [
                ('move_type', '=', 'out_invoice'),
                ('invoice_origin', 'in', self.lead_id.order_ids.mapped('name')),
            ],
        }

    # ---------------------------------------------------------
    # PAYMENT ONCHANGE
    # ---------------------------------------------------------
    @api.onchange('create_payment')
    def _onchange_create_payment(self):
        if not self.create_payment:
            return

        if self.total_outstanding_amount > 0:
            self.customer_payment_amount = self.total_outstanding_amount

    # ---------------------------------------------------------
    # CONFIRM ACTION
    # ---------------------------------------------------------
    def action_confirm(self):
        self.ensure_one()

        if not self.sale_order_id:
            raise UserError("No Sale Order found for this Opportunity.")

        if not self.company_id:
            raise UserError("Company is required to proceed.")

        invoice = False

        # --------------------------------------------------
        # 1. CREATE & POST INVOICE
        # --------------------------------------------------
        if self.create_invoice:
            invoices = self.sale_order_id._create_invoices()
            invoice = invoices[:1]
            invoice.action_post()

        # --------------------------------------------------
        # 2. CREATE & POST CUSTOMER PAYMENT (PARTIAL OK)
        # --------------------------------------------------
        if self.create_payment:
            if not self.customer_payment_journal_id:
                raise UserError("Please select a payment journal.")

            if not invoice:
                invoice = self.env['account.move'].search([
                    ('move_type', '=', 'out_invoice'),
                    ('invoice_origin', 'in', self.lead_id.order_ids.mapped('name')),
                    ('state', '=', 'posted'),
                ], order="invoice_date desc", limit=1)

            if not invoice:
                raise UserError("No posted invoice found for payment.")

            if float_compare(
                self.customer_payment_amount,
                invoice.amount_residual,
                precision_rounding=invoice.currency_id.rounding
            ) == 1:
                raise UserError("Payment amount cannot exceed outstanding amount.")

            payment = self.env['account.payment'].create({
                'payment_type': 'inbound',
                'partner_type': 'customer',
                'partner_id': invoice.partner_id.id,
                'amount': self.customer_payment_amount,
                'journal_id': self.customer_payment_journal_id.id,
                'company_id': self.company_id.id,
            })

            payment.action_post()

            # SAFE RECONCILIATION (ODOO 18)
            lines = (payment.move_id.line_ids + invoice.line_ids).filtered(
                lambda l: l.account_id.reconcile
            )
            lines.reconcile()

        # --------------------------------------------------
        # NEXT PHASE STUBS
        # --------------------------------------------------
        if self.create_vendor_bill:
            raise UserError("Vendor Bill logic will be added next.")

        if self.create_vendor_payment:
            raise UserError("Vendor Payment logic will be added next.")

        if self.create_expense:
            raise UserError("Expense logic will be added next.")

        return {'type': 'ir.actions.act_window_close'}
