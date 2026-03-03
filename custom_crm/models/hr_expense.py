from odoo import fields, models, api


class HrExpenses(models.Model):
    _inherit = 'hr.expense'

    lead_id = fields.Many2one(comodel_name="crm.lead", readonly=True, copy=False, tracking=1)

    def _is_company_expense(self):
        """Return True when expense is company-paid (not employee reimbursement)."""
        self.ensure_one()
        payment_mode = getattr(self, 'payment_mode', False)
        return payment_mode in ('company_account', 'company_paid')

    def _auto_process_lead_expense(self):
        """Auto submit/approve/post only for lead-linked company expenses."""
        self.ensure_one()
        if not self.lead_id or not self._is_company_expense():
            return

        # Draft -> Submit
        if self.state in ('draft',):
            self.action_submit_expenses()

        # Submit -> Approve
        if self.state in ('reported', 'submitted'):
            self.action_approve_expense_sheets()

        # Approve -> Post
        if self.state in ('approved',):
            self.action_post()

    @api.model_create_multi
    def create(self, vals_lists):
        """Create functionality extended for:
        1) Adding analytic_distribution from lead analytic account
        2) Auto-posting lead-linked company expenses
        """
        res = super().create(vals_lists)
        for expense in res:
            if expense.lead_id and expense.lead_id.analytic_account_id:
                expense.analytic_distribution = {expense.lead_id.analytic_account_id.id: 100.0}
            expense._auto_process_lead_expense()
        return res
