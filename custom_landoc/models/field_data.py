from odoo import fields, models, api


class FieldData(models.Model):
    _name = 'field.data'
    _description = 'Field Data'
    _order = 'sequence, id'

    name = fields.Char(string="Description")
    sequence = fields.Integer(string="Sequence", default=10)
    checklist_data_id = fields.Many2one(comodel_name="checklist.data")
    checklist_type = fields.Selection(related="checklist_data_id.checklist_type")
    client_type = fields.Selection(selection=[('buyer', 'Buyer'), ('seller', 'Seller'), ('witness', 'Witness'),
                                              ('minor_guardian', 'Minor/Guardian'), ('representative', 'Representative')], string="Client Type",
                                   copy=False, index=True)
    is_data_required = fields.Boolean(string="Data")
    is_attachment_required = fields.Boolean(string="Attachment")
    company_id = fields.Many2one(comodel_name='res.company', index=True)
