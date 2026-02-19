from odoo import fields, models, api, _
from odoo.exceptions import (
    UserError, ValidationError
)


class LandocFees(models.Model):
    _name = 'landoc.fees'
    _description = 'Landoc Fees'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(tracking=1)
    service_category_id = fields.Many2one(comodel_name="product.category", domain="[('is_service','=',True)]",
                                          required=True,
                                          tracking=1, string="Category of Service")
    service_id = fields.Many2one(comodel_name="service.type",
                                 domain="[('service_category_id','=',service_category_id)]", tracking=1, required=True,
                                 string="Service")
    service_count = fields.Integer()
    customer_fees_line = fields.One2many(comodel_name="landoc.customer.fees", inverse_name="fees_id")
    vendor_fees_line = fields.One2many(comodel_name="landoc.vendor.fees", inverse_name="fees_id")
    is_ec = fields.Boolean(compute='_compute_is_ec')

    ################
    # Compute
    ################
    @api.depends('service_id')
    def _compute_is_ec(self):
        """
        To compute EC boolean
        """
        for record in self:
            if record.service_id.service_type == 'encumbrance_certificate':
                record.is_ec = True
            else:
                record.is_ec = False

    ###########
    # Onchange
    ###########

    @api.onchange('service_id')
    def onchange_service_id_method(self):
        if self.service_id and self.search_count([('service_id', '=', self.service_id.id)]) >=1:
            raise UserError(_(f'Service {self.service_id.name} already exists.'))

    @api.onchange('service_category_id')
    def onchange_service_category_id_method(self):
        self.service_id = False
        self.vendor_fees_line = False

        if self.service_category_id:
            service_type = self.env['service.type'].search([('service_category_id','=',self.service_category_id.id)])
            self.service_id = service_type[0] if len(service_type.ids) == 1 else False
            self.service_count = len(service_type)



class LandocCustomerFees(models.Model):
    _name = 'landoc.customer.fees'
    _description = 'Landoc Customer Fees'

    fees_id = fields.Many2one(comodel_name="landoc.fees")
    product_id = fields.Many2one(comodel_name="product.product")
    rate = fields.Float()


class LandocVendorFees(models.Model):
    _name = 'landoc.vendor.fees'
    _description = 'Landoc Vendor Fees'

    fees_id = fields.Many2one(comodel_name="landoc.fees")
    product_id = fields.Many2one(comodel_name="product.product")
    ec_category = fields.Selection([('application_fee', 'Application Fee'), ('search_fee_1st_year', 'Search Fee 1st Year'),
                       ('search_fee_additional_year', 'Search Fee for Additional Year'), ('computer_fees', 'Computer Fees'),], string="EC Fees Category")
    rate = fields.Float()
