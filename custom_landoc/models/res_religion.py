from odoo import models, fields

class Religion(models.Model):
    _name = "res.religion"
    _description = "Religion Information"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Religion Name", tracking=1, required=True)
    code = fields.Char(string="Code", tracking=1)
    company_id = fields.Many2one(comodel_name='res.company', tracking=1, index=True)
