from odoo import fields, models, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _prepare_invoice(self):
        res = super()._prepare_invoice()
        res.update({'lead_id': self.opportunity_id.id})
        return res


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    lead_id = fields.Many2one(related="order_id.opportunity_id", tracking=1)

    @api.model_create_multi
    def create(self, vals_lists):
        """Create functionality extended for adding 'analytic_distribution' """
        res = super().create(vals_lists)
        for line in res:
            if line.lead_id:
                line.analytic_distribution = {line.lead_id.analytic_account_id.id: 100.0}
        return res
