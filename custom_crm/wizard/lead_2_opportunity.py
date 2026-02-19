from odoo import fields, models, api


class Lead2OpportunityPartner(models.TransientModel):
    _inherit = 'crm.lead2opportunity.partner'

    @api.model
    def _get_new_name_type(self):
        selection = [('convert', 'Convert to opportunity'), ]
        return selection

    name = fields.Selection(
        selection='_get_new_name_type',
        string='Conversion Action', compute=False, default='convert', readonly=False, store=True, compute_sudo=False)

    action_view = fields.Selection([
        ('create', 'Create a new customer'),
        ('exist', 'Link to an existing customer'),
        #('nothing', 'Do not link to a customer')
    ], string='Related Customer', compute='_compute_action', readonly=False, store=True, compute_sudo=False)

    @api.depends('lead_id')
    def _compute_action(self):
        for convert in self:
            # partner = convert.lead_id._find_matching_partner()
            if convert.lead_id.new_or_existing_customer == 'existing_customer':
                convert.action = 'exist'
                convert.action_view = 'exist'
            elif convert.lead_id.new_or_existing_customer == 'new_customer':
                convert.action = 'create'
                convert.action_view = 'create'

    @api.onchange('action_view')
    def action_view_onchange_method(self):
        self.action = self.action_view


    def action_apply(self):
        res = super().action_apply()
        analytic_plan_id = self.env.ref('custom_crm.analytic_landoc_lead')
        analytic = self.env['account.analytic.account'].create({
            'name': self.lead_id.name,
            'partner_id': self.lead_id.partner_id.id,
            'company_id': self.lead_id.company_id.id,
            'plan_id': analytic_plan_id.id,
            'lead_id': self.lead_id.id,
        })
        self.lead_id.analytic_account_id = analytic.id
        return res
