from odoo import api, models, fields, _
from datetime import date


class LegalServiceProcess(models.TransientModel):
    _name = 'legal.service.process'
    _description = 'Legal Service Process'

    service_category_id = fields.Many2one(comodel_name="product.category", domain="[('is_service','=',True)]",
                                          tracking=1, string="Category of Service")
    service_id = fields.Many2one(comodel_name="service.type",
                                 domain="[('service_category_id','=',service_category_id)]", tracking=1,
                                 string="Service")
    workflow_master_id = fields.Many2one(comodel_name="workflow.master", string="Workflow Master")
    lead_id = fields.Many2one(comodel_name="crm.lead", string="Lead")

    # EC Fields...
    ec_start_date = fields.Date(string="EC Start Date")
    ec_end_date = fields.Date(string="EC End Date")
    ec_end_date_warning = fields.Char(string="EC End Date Warning")
    is_ec_apply = fields.Boolean(string="Is EC Applied")
    is_ec = fields.Boolean(compute="_compute_is_ec")

    ####################
    # Compute Function
    ####################

    @api.depends('service_id')
    def _compute_is_ec(self):
        """
        To compute marriage EC boolean
        """
        for record in self:
            if record.service_id.service_type == 'encumbrance_certificate':
                record.is_ec = True
            else:
                record.is_ec = False

    #############
    # Onchange.
    #############
    @api.onchange('ec_end_date', 'ec_start_date')
    def onchange_ec_end_date(self):
        # Workflow Automation
        if self.ec_start_date and self.ec_start_date.year < 1975:
            self.workflow_master_id = self.env['workflow.master'].search([('ec_year_applicable', '=', 'before_1975')], limit=1)
        if self.ec_start_date and self.ec_start_date.year >= 1975:
            self.workflow_master_id = self.env['workflow.master'].search([('ec_year_applicable', '=', 'after_1975')], limit=1)

        # EC end date warning
        current_date = date.today()
        self.ec_end_date_warning = ""
        if self.ec_end_date and self.ec_start_date and current_date:
            if self.ec_end_date == current_date or self.ec_end_date > current_date:
                self.ec_end_date_warning = f"Entered date is a future date"
                self.ec_end_date = False
            if self.ec_end_date and self.ec_start_date and self.ec_end_date < self.ec_start_date:
                self.ec_end_date_warning = f"End date can not be less than start date"
                self.ec_end_date = False

    ###########
    # Action.
    ###########
    def generate_landoc_service(self):
        crm_landoc_service = self.env['crm.landoc.service']
        crm_landoc_service.create({
            'name': f"{self.lead_id.name} - {self.lead_id.service_id.name}",
            'service_category_id': self.lead_id.service_category_id.id,
            'property_type_id': self.lead_id.property_type_id.id,
            'workflow_master_id': self.lead_id.workflow_master_id.id,
            'service_id': self.lead_id.service_id.id,
            'zone_id': self.lead_id.zone_id.id,
            'district_id': self.lead_id.district_id.id,
            'sro_id': self.lead_id.sro_id.id,
            'ec_village_id': self.lead_id.village_id.id,
            'ec_start_date': self.lead_id.ec_start_date,
            'ec_end_date': self.lead_id.ec_end_date,
            'survey_no': '-',
            'lead_id': self.lead_id.id,
        })
        if self.is_ec_apply:
            ec_service_obj = self.env['service.type'].search([('service_type','=','encumbrance_certificate')], limit=1)
            crm_landoc_service.create({
                'name': f"{self.lead_id.name} - {ec_service_obj.name}",
                'service_category_id': ec_service_obj.service_category_id.id,
                'workflow_master_id': self.workflow_master_id.id,
                'service_id': ec_service_obj.id,
                'zone_id': self.lead_id.zone_id.id,
                'district_id': self.lead_id.district_id.id,
                'sro_id': self.lead_id.sro_id.id,
                'ec_village_id': self.lead_id.village_id.id,
                'ec_start_date': self.ec_start_date,
                'ec_end_date': self.ec_end_date,
                'survey_no': '-',
                'lead_id': self.lead_id.id,
            })
