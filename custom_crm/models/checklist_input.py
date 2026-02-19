from odoo import fields, models, api, _
from odoo.exceptions import (
    UserError,
)


class ChecklistInput(models.Model):
    _name = 'checklist.input'
    _description = 'Checklist Input'

    name = fields.Char(string="Checklist Name")
    lead_id = fields.Many2one(comodel_name="crm.lead", string="Lead", readonly=True)
    is_service_checklist = fields.Boolean(string="Service Checklist")
    checklist_line_ids = fields.One2many(comodel_name="checklist.input.line", inverse_name="checklist_id")
    service_checklist_line = fields.One2many(comodel_name="service.checklist.line", inverse_name="checklist_id")
    property_checklist_line = fields.One2many(comodel_name="property.checklist.line", inverse_name="checklist_id")
    state = fields.Selection(selection=[
        ('draft', "Draft"),
        ('confirm', "Confirm"),
    ], string="Status",
        readonly=True, copy=False, index=True,
        default='draft')
    company_id = fields.Many2one(comodel_name='res.company',index=True)


    def action_set_to_confirm(self):
        """Action set to confirm"""
        # for content_checklist in self.checklist_line_ids:
        #     if content_checklist.is_data_required or content_checklist.is_attachment_required:
        #         if content_checklist.is_data_required and not content_checklist.data_field:
        #             raise UserError(_("Data is required !"))
        #         if content_checklist.is_attachment_required and not content_checklist.attachments:
        #             raise UserError(_("Attachments is required !"))

        for service_checklist in self.service_checklist_line:
            if service_checklist.is_data_required or service_checklist.is_attachment_required:
                if service_checklist.is_data_required and not service_checklist.data_field:
                    raise UserError(_(f"'{service_checklist.name}' Data is required !"))
                if service_checklist.is_attachment_required and not service_checklist.attachments:
                    raise UserError(_(f"'{service_checklist.name}' Attachments is required !"))

        for property_checklist in self.property_checklist_line:
            if property_checklist.is_data_required or property_checklist.is_attachment_required:
                if property_checklist.is_data_required and not property_checklist.data_field:
                    raise UserError(_(f"'{property_checklist.name}' Data is required !"))
                if property_checklist.is_attachment_required and not property_checklist.attachments:
                    raise UserError(_(f"'{property_checklist.name}' Attachments is required !"))
        self.state = 'confirm'

    def action_set_to_draft(self):
        """Action set to draft"""
        self.state = 'draft'
