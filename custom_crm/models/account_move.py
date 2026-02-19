from odoo import fields, models, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    lead_id = fields.Many2one(comodel_name="crm.lead", readonly=True, tracking=1)


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    lead_id = fields.Many2one(related="move_id.lead_id")

    @api.model_create_multi
    def create(self, vals_lists):
        """Create functionality extended for adding 'analytic_distribution' """
        res = super().create(vals_lists)
        for move in res:
            if move.lead_id:
                move.analytic_distribution = {move.lead_id.analytic_account_id.id: 100.0}
        return res

