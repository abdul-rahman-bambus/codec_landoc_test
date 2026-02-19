from odoo import fields, models, api

SERVICE_TYPES = [
    ('certified_copy', 'Certified Copy'),
    ('document_consulting', 'Document Consulting'),
    ('document_registration', 'Document Registration'),
    ('encumbrance_certificate', 'Encumbrance Certificate'),
    ('legal_opinion', 'Legal Opinion'),
    ('marriage_registration', 'Marriage Registration'),
    ('revenue_and_local_body_department_works', 'Revenue & Local Body Department Works'),
    ('stamp_paper', 'Stamp Paper'),
    ('unregistered_agreement', 'Unregistered Agreement'),
]


class ServiceType(models.Model):
    _name = 'service.type'
    _description = 'Service Type'
    _rec_name = "name"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Service", tracking=1)
    code = fields.Char(string="Code", tracking=1)
    service_category_id = fields.Many2one('product.category', tracking=1, domain="[('is_service','=',True)]", required=True, string="Service Category")
    company_id = fields.Many2one(comodel_name='res.company', tracking=1, index=True)
    # is_marriage_registation = fields.Boolean(string="Marriage")
    # is_ec = fields.Boolean(string="Encumbrance Certificate (EC)")
    # is_cc = fields.Boolean(string="Certified Copy")
    fees_above_ninety = fields.Float(string="Fees Above Ninety", tracking=1)
    fees_above_one_hundred_fifty = fields.Float(string="Fees Above One Hundred Fifty", tracking=1)
    service_type = fields.Selection(selection=SERVICE_TYPES, required=True, tracking=1)

    vendor_products_ids = fields.Many2many(comodel_name='product.product', domain="[('type','=', 'service'), ('purchase_ok','=',True)]")
