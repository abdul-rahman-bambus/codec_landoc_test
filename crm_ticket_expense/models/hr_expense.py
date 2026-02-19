
from odoo import models, fields

class HrExpense(models.Model):
    _inherit = 'hr.expense'

    lead_id = fields.Many2one(
        'crm.lead',
        string='CRM Ticket'
    )
