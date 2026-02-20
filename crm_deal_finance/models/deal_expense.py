from odoo import _, api, fields, models
from odoo.exceptions import UserError


class DealExpense(models.Model):
    _name = 'deal.expense'
    _description = 'Deal Expense'
    _order = 'expense_date desc, id desc'

    name = fields.Char(required=True)
    lead_id = fields.Many2one('crm.lead', required=True, ondelete='cascade')
    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        store=True,
        readonly=True,
    )
    expense_date = fields.Date(required=True, default=fields.Date.context_today)
    amount = fields.Monetary(required=True, currency_field='currency_id')
    partner_id = fields.Many2one('res.partner', string='Vendor')
    journal_id = fields.Many2one(
        'account.journal',
        required=True,
        domain="[('type', 'in', ('cash', 'bank')), ('company_id', '=', company_id)]",
    )
    payment_mode = fields.Selection(
        [('cash', 'Cash'), ('bank', 'Bank')],
        compute='_compute_payment_mode',
        store=True,
    )
    expense_account_id = fields.Many2one(
        'account.account',
        required=True,
        domain="[('deprecated', '=', False), ('account_type', '=', 'expense')]",
        check_company=True,
    )
    notes = fields.Text()
    auto_post = fields.Boolean(default=True)
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('confirmed', 'Confirmed'),
            ('posted', 'Posted'),
            ('cancelled', 'Cancelled'),
        ],
        default='draft',
        required=True
    )
    move_id = fields.Many2one('account.move', readonly=True, copy=False)

    @api.depends('journal_id.type')
    def _compute_payment_mode(self):
        for expense in self:
            expense.payment_mode = expense.journal_id.type if expense.journal_id.type in ('cash', 'bank') else False

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records.filtered(lambda r: r.auto_post):
            record.action_confirm()
            record.action_post()
        return records

    def action_confirm(self):
        for expense in self:
            if expense.state in ('confirmed', 'posted'):
                continue
            if expense.state == 'cancelled':
                raise UserError(_('Cancelled expenses cannot be confirmed.'))
            if expense.amount <= 0:
                raise UserError(_('Expense amount must be greater than zero.'))
            if not expense.journal_id:
                raise UserError(_('Please select a payment journal.'))
            if not expense.expense_account_id:
                raise UserError(_('Please select an expense account.'))
            expense.state = 'confirmed'

    def _prepare_move_vals(self):
        self.ensure_one()
        credit_account = self.journal_id.default_account_id
        if not credit_account:
            raise UserError(_('Selected journal is missing a default account.'))

        return {
            'move_type': 'entry',
            'date': self.expense_date,
            'ref': self.name,
            'journal_id': self.journal_id.id,
            'company_id': self.company_id.id,
            'lead_id': self.lead_id.id,
            'line_ids': [
                (0, 0, {
                    'name': self.name,
                    'account_id': self.expense_account_id.id,
                    'debit': self.amount,
                    'credit': 0.0,
                    'partner_id': self.partner_id.id,
                }),
                (0, 0, {
                    'name': self.name,
                    'account_id': credit_account.id,
                    'debit': 0.0,
                    'credit': self.amount,
                    'partner_id': self.partner_id.id,
                }),
            ],
        }

    def action_post(self):
        for expense in self:
            if expense.state == 'posted':
                continue
            if expense.state == 'cancelled':
                raise UserError(_('Cancelled expenses cannot be posted.'))
            if expense.state == 'draft':
                expense.action_confirm()
            if expense.move_id:
                raise UserError(_('Journal entry already created for this expense.'))

            move = self.env['account.move'].create(expense._prepare_move_vals())
            move.action_post()
            expense.write({'state': 'posted', 'move_id': move.id})

    def action_set_draft(self):
        for expense in self:
            if expense.move_id:
                raise UserError(_('Cannot reset to draft because a journal entry already exists.'))
            expense.state = 'draft'

    def action_cancel(self):
        for expense in self:
            if expense.move_id:
                raise UserError(_('Cannot cancel a posted expense. Please reverse the journal entry first.'))
            expense.state = 'cancelled'

    def action_open_move(self):
        self.ensure_one()
        if not self.move_id:
            raise UserError(_('No journal entry found for this expense.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Expense Journal Entry'),
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': self.move_id.id,
            'target': 'current',
        }
