from odoo import fields, models, api, _
from odoo.exceptions import (
    UserError, ValidationError
)
import phonenumbers
from datetime import date
from odoo.tools import date_utils, email_split, is_html_empty, groupby, parse_contact_from_email, SQL
from odoo.addons.crm.models import crm_lead
from odoo.addons.crm.models import crm_stage
import logging
_logger = logging.getLogger(__name__)

crm_lead.PARTNER_ADDRESS_FIELDS_TO_SYNC = [
    'street',
    'street2',
    'city',
    'zip',
    'religion_id',
    'city_id',
    'state_id',
    'country_id',
]

crm_stage.AVAILABLE_PRIORITIES = [
    ('0', 'Low'),
    ('1', 'Medium'),
    ('2', 'Normal'),
    ('3', 'High'),
    ('4', 'Very High'),
    ('5', 'Critical'),  # New one
]


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    # Inherited for changing the string.
    team_id = fields.Many2one(
        'crm.team', string='Department', check_company=True, index=True, tracking=True,
        compute='_compute_team_id', ondelete="set null", readonly=False, store=True, precompute=True)

    priority = fields.Selection(
        selection_add=crm_stage.AVAILABLE_PRIORITIES, string='Priority', index=True,
        default=crm_stage.AVAILABLE_PRIORITIES[0][0])

    checklist_input_ids = fields.Many2many(comodel_name='checklist.input', domain="[('lead_id','=',id)]")
    checklist_counts = fields.Integer(string="Checklist Counts ", compute="_compute_checklist_input_ids")
    service_category_id = fields.Many2one(comodel_name="product.category", domain="[('is_service','=',True)]",
                                          tracking=1, string="Category of Service")
    service_id = fields.Many2one(comodel_name="service.type",
                                 domain="[('service_category_id','=',service_category_id)]", tracking=1,
                                 string="Service")
    service_count = fields.Integer(string="Service Count")
    is_marriage_registation = fields.Boolean(compute="_compute_is_marriage_registation")
    date_of_marriage = fields.Date(string="Date of Marriage")
    date_delay_waring = fields.Char(string="Date Delay Warning")

    is_ec = fields.Boolean(compute="_compute_is_ec")
    ec_start_date = fields.Date(string="EC Start Date")
    ec_end_date = fields.Date(string="EC End Date")
    ec_end_date_warning = fields.Char(string="EC End Date Warning")
    # survey_no = fields.Char(string="Survey No")
    # sub_division_no = fields.Char(string="Sub Division No")
    whos_name_applied = fields.Char(string="On Whose Name To Be Applied")
    is_cc = fields.Boolean(compute="_compute_is_cc")
    document_no = fields.Char(string="Document No")
    document_year = fields.Char(string="Year")
    book_no = fields.Selection([('book_1', 'Book 1'), ('book_3/4', 'Book 3/4')], string="Book No")

    # Encumbrance Certificate Reports
    # ec_zone_ids = fields.Many2many('res.zone', string="Zone")
    # ec_district_ids = fields.Many2many('res.district', string="DRO")
    # ec_sro_ids = fields.Many2many('res.sro', string="SRO")
    # ec_village_ids = fields.Many2many('res.village', string="Village")
    # # ec_period = fields.Char(string="EC Period")
    # ec_plot_no = fields.Char(string="Plot Number")
    # ec_boundaries = fields.Char(string="Boundaries")
    # ec_extentions = fields.Char(string="Extentions")
    ec_additional_year_count = fields.Integer(
        string="Additional Years",
        compute="_compute_year_difference",
    )

    ec_additional_year_amount = fields.Float(
        string="Additional Year Amount",
        compute="_compute_year_difference",
    )

    ec_related_documents = fields.Binary("EC Related Document", attachment=True)  # store pdf
    ec_related_documents_filename = fields.Char("EC Document Filename")

    is_propertychecklist_needed = fields.Boolean(related="service_category_id.is_propertychecklist_needed",
                                                 string="Property Checklist Needed")
    is_document_registation = fields.Boolean(compute="_compute_is_document_registation")
    service_workflow_ids = fields.Many2many(comodel_name="workflow.master", compute="_compute_service_workflow_ids")
    workflow_master_id = fields.Many2one(comodel_name="workflow.master", string="Workflow Master", tracking=1,
                                         domain="[('category_id', '=', service_category_id)]")
    checklist_tracking_line = fields.One2many(comodel_name='crm.checklist.tracking',
                                              inverse_name='lead_id', string="Checklist")
    sequence = fields.Char(string="Sequence", required=True, copy=False, readonly=False,
                           default=lambda self: _('New'))
    zone_id = fields.Many2one('res.zone', tracking=1, string="Zone")
    religion_id = fields.Many2one('res.religion', string="Religion", tracking=1, compute="_compute_religion_id",
                                  inverse="_inverse_religion_id",
                                  store=True)
    district_id = fields.Many2one('res.district', tracking=1, string="DRO")
    sro_id = fields.Many2one('res.sro', tracking=1, string="SRO")
    sro_zone_ids = fields.Many2many(comodel_name="res.zone", compute='_compute_sro_zone_ids')
    sro_district_ids = fields.Many2many(comodel_name="res.district", compute='_compute_sro_district_ids')
    sro_ids = fields.Many2many(comodel_name="res.sro", compute='_compute_sro_ids')
    village_id = fields.Many2one('res.village', tracking=1, string="Village", domain="[('sro_id', '=', sro_id)]")
    compute_next_step = fields.Char(compute="_compute_next_step")
    name = fields.Char(
        string="Ticket Number",
        required=True, copy=False, readonly=True,
        index='trigram',
        default=lambda self: _('New'))
    property_type_id = fields.Many2one(comodel_name="property.type", tracking=1, string="Type of Property")
    # Buyer
    no_of_buyer = fields.Integer(string="No of Buyer", tracking=1, default=1)
    buyer_party_type = fields.Selection(selection=[('individual','Individual'), ('company_firm_trust','Company/Firm/Trust'), ('government', 'Government')], tracking=1, default="individual", string="Buyer's Party",)
    buyer_name = fields.Char(string="Name", tracking=1)
    buyer_company_tan_no = fields.Char(string="Company Tan No", tracking=1)
    is_buyer_minor = fields.Boolean(default=False, tracking=1)
    is_buyer_representative = fields.Boolean(default=False, tracking=1)
    # Seller
    no_of_seller = fields.Integer(string="No of Seller", tracking=1, default=1)
    seller_party_type = fields.Selection(selection=[('individual','Individual'), ('company_firm_trust','Company/Firm/Trust'), ('government', 'Government')], default="individual", tracking=1, string="Seller's Party",)
    seller_name = fields.Char(string="Name", tracking=1)
    seller_company_tan_no = fields.Char(string="Company Tan No", tracking=1)
    is_seller_minor = fields.Boolean(default=False, tracking=1)
    is_seller_representative = fields.Boolean(default=False, tracking=1)
    new_or_existing_customer = fields.Selection(
        selection=[('new_customer', 'New Customer'), ('existing_customer', 'Existing Customer')], tracking=1,
        copy=False, default="new_customer", index=True)
    is_address_required = fields.Selection(
        selection=[('required', 'Required'), ('not_required', 'Not Required')],
        copy=False, default="required", index=True)
    show_address = fields.Boolean(default=False)
    city_id = fields.Many2one("res.city", string="City ", compute='_compute_partner_address_values', readonly=False, tracking=1,
                              store=True)
    city = fields.Char(string='City', related="city_id.name", readonly=True)
    currency_id = fields.Many2one('res.currency', compute='_get_company_currency', readonly=True, tracking=1,
                                  string="Currency ")  # currency of amount currency
    total_invoiced = fields.Monetary(compute='_invoice_total', string="Total Invoiced",
                                     groups='account.group_account_invoice,account.group_account_readonly')
    total_expenses = fields.Monetary(string="Checklist Counts", compute='_expenses_total')
    total_vendor_bills = fields.Monetary(string="Vendor Bills", compute='_vendor_bills_total')
    invoice_ids = fields.One2many('account.move', 'lead_id', string='Orders')
    expense_ids = fields.One2many('hr.expense', 'lead_id', string='Expenses')

    timer_start = fields.Datetime()
    timer_pause = fields.Datetime()
    is_timer_running = fields.Boolean()
    remaining_hours = fields.Float("Remaining Hours", compute="compute_remaining_hours", readonly=True)

    display_timer_start_primary = fields.Boolean(compute='_compute_display_timer_buttons')
    display_timer_stop = fields.Boolean(compute='_compute_display_timer_buttons')
    display_timer_pause = fields.Boolean(compute='_compute_display_timer_buttons')
    display_timer_resume = fields.Boolean(compute='_compute_display_timer_buttons')

    analytic_account_id = fields.Many2one(comodel_name='account.analytic.account', readonly=True)

    ############
    # Compute
    ############
    @api.depends('ec_start_date', 'ec_end_date')
    def _compute_year_difference(self):
        for rec in self:
            if rec.ec_start_date and rec.ec_end_date and rec.ec_end_date >= rec.ec_start_date:
                total_years = rec.ec_end_date.year - rec.ec_start_date.year

                rec.ec_additional_year_count = total_years
                landoc_fees = self.env['landoc.fees'].search([('service_id', '=', rec.service_id.id)], limit=1)
                vendor_line = landoc_fees.vendor_fees_line.filtered(lambda l: l.ec_category == 'search_fee_additional_year')[:1]
                rate_per_year = vendor_line.rate
                rec.ec_additional_year_amount = total_years * rate_per_year
            else:
                rec.ec_additional_year_count = 0
                rec.ec_additional_year_amount = 0


    @api.depends('timer_start', 'timer_pause')
    def _compute_display_timer_buttons(self):
        for record in self:
            current_checklist = record.checklist_tracking_line.filtered(lambda l: l.active_step)
            start_p, stop, pause, resume = True, True, True, True
            if current_checklist.timer_start:
                start_p = False
                stop = True
            if current_checklist.timer_pause:
                pause = False
            else:
                resume = False
            if not current_checklist.timer_start:
                stop = False
                pause = False

            record.update({
                'display_timer_start_primary': start_p,
                'display_timer_stop': stop,
                'display_timer_pause': pause,
                'display_timer_resume': resume,
            })

    @api.depends('timer_start', 'timer_pause')
    def compute_remaining_hours(self):
        for record in self:
            checklist_remaining_hours = record.checklist_tracking_line.filtered(lambda l: l.active_step).remaining_hours
            if checklist_remaining_hours:
                record.remaining_hours = checklist_remaining_hours
            else:
                record.remaining_hours = False

    @api.depends('service_id')
    def _compute_is_marriage_registation(self):
        """
        To compute marriage registration boolean
        """
        for record in self:
            if record.service_id.service_type == 'marriage_registration':
                record.is_marriage_registation = True
            else:
                record.is_marriage_registation = False

    @api.depends('service_id')
    def _compute_is_document_registation(self):
        """
        To compute document registration boolean
        """
        for record in self:
            if record.service_id.service_type == 'document_registration':
                record.is_document_registation = True
            else:
                record.is_document_registation = False

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

    @api.depends('service_id')
    def _compute_is_cc(self):
        """
        To compute marriage CC boolean
        """
        for record in self:
            if record.service_id.service_type == 'certified_copy':
                record.is_cc = True
            else:
                record.is_cc = False

    @api.depends('service_category_id')
    def _compute_sro_zone_ids(self):
        """Compute the value of the field sro_zone_ids."""
        for record in self:
            company_ids = self.env.user.company_ids
            company_zone = company_ids.mapped('zone_ids')
            total_zone = False
            for company in company_ids:
                if not company.zone_ids:
                    total_zone = True
                    break
            if company_zone:
                record.sro_zone_ids = company_zone.ids
            if total_zone :
                record.sro_zone_ids = self.env['res.zone'].search([])

    @api.depends('zone_id')
    def _compute_sro_district_ids(self):
        """Compute the value of the field sro_district_ids."""
        for record in self:
            total_zone = []
            company_ids = self.env.user.company_ids
            company_sro_ids = company_ids.mapped('sro_ids')
            for company in company_ids:
                if not company.sro_ids and not company.zone_ids:
                    total_zone += self.env['res.district'].search([]).ids #('zone_id', 'in', company.zone_ids.ids)
                if not company.sro_ids and company.zone_ids:
                    total_zone += self.env['res.district'].search([('zone_id', 'in', company.zone_ids.ids)]).ids
            record.sro_district_ids = total_zone + company_sro_ids.mapped('district_id').ids


    @api.depends('district_id')
    def _compute_sro_ids(self):
        """Compute the value of the field sro_ids."""
        for record in self:
            total_zone = []
            company_ids = self.env.user.company_ids
            company_sro_ids = company_ids.mapped('sro_ids')
            for company in company_ids:
                if not company.sro_ids:
                    total_zone += self.env['res.sro'].search([]).ids
            record.sro_ids = total_zone + company_sro_ids.ids

    @api.onchange('date_of_marriage')
    def onchange_date_of_marriage(self):
        current_date = date.today()
        self.date_delay_waring = ""
        if self.date_of_marriage and self.date_of_marriage < current_date:
            delta = abs(self.date_of_marriage - current_date)
            if delta.days > 150:
                self.date_delay_waring = f"{delta.days} days ago, will charge {self.service_id.fees_above_one_hundred_fifty}"
            elif delta.days > 90:
                self.date_delay_waring = f"{delta.days} days ago, will charge {self.service_id.fees_above_ninety}"

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

    @api.onchange('checklist_tracking_line')
    def onchange_checklist_tracking_line(self):
        count = 1
        for line in self.checklist_tracking_line:
            line.sequence = count
            count += 1
        if len(self.checklist_tracking_line.filtered(lambda l: l.active_step)) > 1:
            raise UserError(_("Only one step can be active at a time."))

    @api.onchange('zone_id')
    def onchange_zone_id(self):
        self.write({
            'district_id': False,
            'sro_id': False,
            'village_id': False,
        })

    @api.onchange('district_id')
    def onchange_district_id(self):
        self.write({
            'sro_id': False,
            'village_id': False,
        })

    @api.onchange('sro_id')
    def onchange_sro_id(self):
        self.write({
            'village_id': False,
        })

    def action_mob_same_as_phone(self):
        self.write({'phone': self.mobile})

    @api.onchange('service_category_id')
    def onchange_service_category_id(self):
        self.write({
            'property_type_id': False,
            'workflow_master_id': False,
            'date_of_marriage': False,
            'date_delay_waring': False,
            'ec_start_date': False,
            'ec_end_date': False,
            # 'survey_no': False,
            'whos_name_applied': False,
            'document_no': False,
            'document_year': False,
            'book_no': False,
        })
        if self.service_category_id:
            service_type = self.env['service.type'].search([('service_category_id','=',self.service_category_id.id)])
            # self.service_category_id = service_type.mapped('service_category_id')
            self.service_id = service_type[0] if len(service_type.ids) == 1 else False
            self.service_count = len(service_type)

    @api.onchange('new_or_existing_customer')
    def onchange_new_or_existing_customer(self):
        self.write({
            'contact_name': False,
            'title': False,
            'partner_id': False,
            'street': False,
            'street2': False,
            'city': False,
            'state_id': False,
            'city_id': False,
            'zip': False,
            'country_id': False,
            'mobile': False,
            'phone': False,
            'religion_id': False,
        })

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        self.write({
            'street': self.partner_id.street,
            'street2': self.partner_id.street2,
            'city': self.partner_id.city,
            'state_id': self.partner_id.state_id.id,
            'city_id': self.partner_id.city_id.id,
            'zip': self.partner_id.zip,
            'country_id': self.partner_id.country_id.id,
            'mobile': self.partner_id.mobile,
            'phone': self.partner_id.phone,
            'religion_id': self.partner_id.religion_id.id,
        })

    @api.depends('partner_id')
    def _compute_religion_id(self):
        """ compute the new values when partner_id has changed """
        for lead in self:
            if not lead.religion_id or lead.partner_id.religion_id:
                lead.religion_id = lead.partner_id.religion_id.id

    def _inverse_religion_id(self):
        """ Update partner_id.religion_id when religion_id is changed on lead """
        for lead in self:
            if lead.partner_id:
                lead.partner_id.religion_id = lead.religion_id


    def get_valid_number(self, mobile):
        try:
            number = phonenumbers.parse(mobile)
            country_code = number.country_code
            if country_code:
                return mobile
        except Exception as e:
            return False

    # @api.constrains('mobile')
    # def mobile_whatsapp_validation(self):
    #     valid_mobile = self.get_valid_number(self.mobile)
    #     if not valid_mobile:
    #         raise ValidationError(
    #             'Kindly provide a valid WhatsApp number, ensuring that it includes the correct "country code".')

    @api.onchange('country_id')
    def _onchange_country_id(self):
        if self.country_id and self.country_id != self.state_id.country_id:
            self.city_id = False
            self.state_id = False

    @api.onchange('state_id')
    def _onchange_state(self):
        if self.state_id.country_id and self.country_id != self.state_id.country_id:
            self.country_id = self.state_id.country_id

    @api.onchange('city_id')
    def _onchange_city_id(self):
        if self.city_id.state_id and self.city_id.state_id != self.state_id:
            self.state_id = self.city_id.state_id
            self.country_id = self.city_id.country_id

    def _prepare_address_values_from_partner(self, partner):
        # Sync all address fields from partner, or none, to avoid mixing them.
        if any(partner[f] for f in crm_lead.PARTNER_ADDRESS_FIELDS_TO_SYNC):
            values = {f: partner[f] for f in crm_lead.PARTNER_ADDRESS_FIELDS_TO_SYNC}
        else:
            values = {f: self[f] for f in crm_lead.PARTNER_ADDRESS_FIELDS_TO_SYNC}
        return values

    @api.model
    def message_new(self, msg_dict, custom_values=None):
        """ Overrides mail_thread message_new that is called by the mailgateway
            through message_process.
            This override updates the document according to the email.
        """
        # remove default author when going through the mail gateway. Indeed we
        # do not want to explicitly set an user as responsible. We prefer that
        # assignment is done automatically (scoring) or manually. Otherwise it
        # would always be root (gateway user). It also allows to exclude portal
        # and public users.
        self = self.with_context(default_user_id=False)

        if custom_values is None:
            custom_values = {}
        defaults = {
            'name': msg_dict.get('subject') or _("No Subject"),
            'email_from': msg_dict.get('from'),
            'partner_id': msg_dict.get('author_id', False),
        }
        if msg_dict.get('priority') in dict(crm_stage.AVAILABLE_PRIORITIES):
            defaults['priority'] = msg_dict.get('priority')
        defaults.update(custom_values)

        return super(CrmLead, self).message_new(msg_dict, custom_values=defaults)

    def _merge_get_fields_address(self):
        """The address fields are propagated as a whole.

        The address is taken from the lead with the most non-empty address field
        (sorted by highest rank if multiple lead have the same amount of non-empty
        fields).
        """
        source_lead = max(self, key=lambda lead: len(list(
            lead[field] for field in crm_lead.PARTNER_ADDRESS_FIELDS_TO_SYNC
            if lead[field]
        )))
        return {fname: source_lead[fname] for fname in crm_lead.PARTNER_ADDRESS_FIELDS_TO_SYNC}

    def _merge_get_fields(self):
        return (
                crm_lead.CRM_LEAD_FIELDS_TO_MERGE
                + list(self._merge_get_fields_specific().keys())
                + crm_lead.PARTNER_ADDRESS_FIELDS_TO_SYNC
        )

    def _prepare_customer_values(self, partner_name, is_company=False, parent_id=False):
        res = super()._prepare_customer_values(partner_name, is_company, parent_id)
        res.update({
            'religion_id': self.religion_id.id,
            'city_id': self.city_id.id,
            'is_company': False,
        })
        return res

    def _prepare_opportunity_quotation_context(self):
        result = super()._prepare_opportunity_quotation_context()
        order_lines = []
        products_ids = self.env['product.template'].search([('categ_id', '=', self.service_category_id.id)])
        for line in products_ids:
            order_lines.append((0, 0, {'product_template_id': line.id, 'product_id': line.product_variant_id.id, 'product_uom_qty':1, 'analytic_distribution': {self.analytic_account_id.id:100}}))
        result.update({
            'default_order_line': order_lines,
        })
        return result

    def _create_customer(self):
        """ Create a partner from lead data and link it to the lead.

        :return: newly-created partner browse record
        """
        Partner = self.env['res.partner']
        # ------------------- For this project No need to create partner as company and its parent. ---------------------#
        # contact_name = self.contact_name
        # if not contact_name:
        #     contact_name = parse_contact_from_email(self.email_from)[0] if self.email_from else False
        #
        # if self.partner_name:
        #     partner_company = Partner.create(self._prepare_customer_values(self.partner_name, is_company=True))
        # elif self.partner_id:
        #     partner_company = self.partner_id
        # else:
        #     partner_company = None
        #
        # if contact_name:
        #     return Partner.create(self._prepare_customer_values(contact_name, is_company=False,
        #                                                         parent_id=partner_company.id if partner_company else False))
        #
        # if partner_company:
        #     return partner_company
        # ---------------------------------------------------------------------------------------------------------------#
        return Partner.create(self._prepare_customer_values(self.contact_name, is_company=False))

    def action_timer_start(self):
        self.checklist_tracking_line.filtered(lambda l: l.active_step).action_timer_start()

    def action_timer_stop(self):
        self.checklist_tracking_line.filtered(lambda l: l.active_step).action_timer_stop()

    def action_timer_pause(self):
        self.checklist_tracking_line.filtered(lambda l: l.active_step).action_timer_pause()

    def action_timer_resume(self):
        self.checklist_tracking_line.filtered(lambda l: l.active_step).action_timer_resume()

    @api.depends('invoice_ids')
    def _invoice_total(self):
        for lead in self:
            lead_invoices = self.env['account.move'].search([('lead_id', '=', self.id), ('move_type', '=', 'out_invoice')])
            lead.total_invoiced = sum(lead_invoices.mapped('amount_total'))

    @api.depends('invoice_ids')
    def _vendor_bills_total(self):
        for lead in self:
            lead_invoices = self.env['account.move'].search([('lead_id', '=', self.id),('move_type', '=', 'in_invoice')])
            lead.total_vendor_bills = sum(lead_invoices.mapped('amount_total'))

    @api.depends('expense_ids')
    def _expenses_total(self):
        for lead in self:
            lead_expenses = self.env['hr.expense'].search([('lead_id', '=', self.id)])
            lead.total_expenses = sum(lead_expenses.mapped('total_amount'))
        # self.total_expenses = 0

    def _get_company_currency(self):
        for partner in self:
            if partner.company_id:
                partner.currency_id = partner.sudo().company_id.currency_id
            else:
                partner.currency_id = self.env.company.currency_id

    @api.depends('checklist_tracking_line')
    def _compute_next_step(self):
        for step in self:
            next_step = ""
            for checklist in self.checklist_tracking_line:
                if checklist.active_step:
                    next_step = checklist.landoc_stage
            step.compute_next_step = next_step

    @api.depends('service_category_id')
    def _compute_service_workflow_ids(self):
        for workflow in self:
            # sub_service = self.env['product.category'].search([('parent_id','=',workflow.service_id.id)])
            # workflows_ids = self.env['workflow.master'].search([('category_id','in', sub_service.ids if sub_service else workflow.service_id.id)])
            workflow.service_workflow_ids = []  # workflows_ids.ids

    @api.depends('checklist_input_ids')
    def _compute_checklist_input_ids(self):
        """Compute checklists counts"""
        for rec in self:
            rec.checklist_counts = len(rec.checklist_input_ids)

    def action_view_crm_invoices(self):
        invoice_action = self.env['ir.actions.actions']._for_xml_id('account.action_move_out_invoice')
        invoice_action['domain'] = [('lead_id', '=', self.id), ('move_type', '=', 'out_invoice')]
        invoice_action['context'] = {'default_lead_id': self.id, 'default_move_type': 'out_invoice', 'default_partner_id': self.partner_id.id}
        return invoice_action

    def action_view_crm_expenses(self):
        expense_action = self.env['ir.actions.actions']._for_xml_id('hr_expense.hr_expense_actions_my_all')
        expense_action['domain'] = [('lead_id', '=', self.id)]
        expense_action['context'] = {'default_lead_id': self.id, 'default_analytic_distribution': {self.analytic_account_id.id:100.0}}
        return expense_action

    def action_view_process_services(self):
        expense_action = self.env['ir.actions.actions']._for_xml_id('landoc_services.action_crm_landoc_service')
        expense_action['domain'] = [('lead_id', '=', self.id)]
        return expense_action

    def action_create_landoc_services(self):
        landoc_service_action = self.env['ir.actions.actions']._for_xml_id('custom_crm.legal_service_process_act_window')
        landoc_service_action['target'] = 'new'
        landoc_service_action['context'] = {'default_lead_id': self.id,
                                     'default_service_category_id': self.service_category_id.id,
                                     'default_service_id': self.service_id.id,
                                     }
        return landoc_service_action

    def action_view_crm_vendor_bills(self):

        move_lines = []
        products_ids = self.service_id.mapped('vendor_products_ids')
        params = self.env['ir.config_parameter'].sudo()
        landoc_vendor_id = int(params.get_param('custom_landoc.landoc_vendor_id')) or False
        for product in products_ids:
            move_lines.append((0, 0, {'product_id': product.id,
                                      'quantity': 1,
                                      'price_unit': 1,
                                      'analytic_distribution': {self.analytic_account_id.id: 100}}))
        if not landoc_vendor_id:
            raise UserError(_("There is no default landoc vendor."))
        if not products_ids:
            raise UserError(_("There is no default vendor products."))

        vendor_bills = self.env['ir.actions.actions']._for_xml_id('account.action_move_in_invoice')
        vendor_bills['domain'] = [('lead_id', '=', self.id), ('move_type', '=', 'in_invoice')]
        vendor_bills['context'] = {'default_lead_id': self.id, 'default_move_type': 'in_invoice', 'default_partner_id': landoc_vendor_id, 'default_invoice_line_ids': move_lines}
        print(vendor_bills, 'vendottttttttttttttttttttt')
        return vendor_bills

    def action_create_vendor_bill_auto(self):

        self.ensure_one()

        products_ids = self.service_id.mapped('vendor_products_ids')
        params = self.env['ir.config_parameter'].sudo()
        landoc_vendor_id = int(params.get_param('custom_landoc.landoc_vendor_id') or 0)

        if not landoc_vendor_id:
            raise UserError("There is no default landoc vendor.")

        if not products_ids:
            raise UserError("There is no default vendor products.")

        move_lines = []

        for product in products_ids:
            move_lines.append((0, 0, {
                'product_id': product.id,
                'quantity': 1,
                'price_unit': 1,
                'analytic_distribution': {
                    self.analytic_account_id.id: 100
                },
            }))

        vendor_bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': landoc_vendor_id,
            'lead_id': self.id,
            'invoice_line_ids': move_lines,
        })

        return vendor_bill


    def action_previous(self):
        """Action Preview."""
        if self.display_timer_start_primary:
            action = self.env['ir.actions.actions']._for_xml_id('custom_crm.action_previous_checklist_tracking_wizard')
            action['context'] = {'default_lead_id': self.id}
            return action

    def action_next(self):
        """Action Next"""
        if self.display_timer_start_primary:
            action = self.env['ir.actions.actions']._for_xml_id('custom_crm.action_checklist_tracking_wizard_wizard')
            action['context'] = {'default_lead_id': self.id}
            return action

    def action_view_checklist(self):
        """Return action for loading checklist input window."""
        action = self.env['ir.actions.actions']._for_xml_id('custom_crm.checklist_input_act_window')
        action['domain'] = [('id', 'in', self.checklist_input_ids.ids)]
        return action

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _("New")) == _("New"):
                vals['name'] = self.env['ir.sequence'].with_company(self.company_id).next_by_code(
                    'crm.lead') or _('New')

        return super().create(vals_list)

    def action_create_checklist(self):
        """Create checklist items based on the selected Sub-Service"""
        check_list_model = self.env['checklist.input']
        checklist_inputs = []
        is_service_checklist = False
        serive_checklist = self.env['checklist.data'].search(
            [('checklist_type', '=', 'service'), ('service_id', '=', self.service_id.id)], limit=1)
        content_checklist = self.env['checklist.data'].search([('checklist_type', '=', 'content'), ('service_id', '=', self.service_id.id)], limit=1)
        content_vals = []
        if content_checklist and self.is_propertychecklist_needed:

            content_list = {'buyer': content_checklist.checklist_data_ids.filtered(lambda l: l.client_type == 'buyer'),
                            'seller': content_checklist.checklist_data_ids.filtered(
                                lambda l: l.client_type == 'seller'),
                            'witness': content_checklist.checklist_data_ids.filtered(
                                lambda l: l.client_type == 'witness'),
                            'minor_guardian': content_checklist.checklist_data_ids.filtered(
                                lambda l: l.client_type == 'minor_guardian'),
                            'representative': content_checklist.checklist_data_ids.filtered(
                                lambda l: l.client_type == 'representative')
                            }

            if content_list.get('buyer'):
                if content_list.get('minor_guardian') and self.is_buyer_minor and self.buyer_party_type == 'individual':
                    for minor_buyer in content_list.get('minor_guardian'):
                        vals = [(0, 0, {
                            # 'name': buyer.name,
                            # 'is_data_required': buyer.is_data_required,
                            'is_buyer_minor': self.is_buyer_minor,
                            'client_type': minor_buyer.client_type,
                            'client_type_name': f"Buyer Guardian",
                            # 'is_attachment_required': buyer.is_attachment_required
                        })]
                        content_vals.extend(vals)
                if content_list.get('representative') and self.is_buyer_representative:
                    representative_buyer = ''
                    if self.buyer_party_type == 'individual':
                        representative_buyer = 'Individual'
                    if self.buyer_party_type == 'company_firm_trust':
                        representative_buyer = 'Company/Firm/Trust'
                    if self.buyer_party_type == 'government':
                        representative_buyer = 'Government'

                    for rep_buyer in content_list.get('representative'):
                        vals = [(0, 0, {
                            # 'name': buyer.name,
                            # 'is_data_required': buyer.is_data_required,
                            'is_buyer_representative': self.is_buyer_representative,
                            'client_type': rep_buyer.client_type,
                            'client_type_name': f"Buyer {representative_buyer} Representative",
                            # 'is_attachment_required': buyer.is_attachment_required
                        })]
                        content_vals.extend(vals)
                for buyer_count in range(self.no_of_buyer):
                    for buyer in content_list.get('buyer'):
                        if self.buyer_party_type == 'individual':
                            vals = [(0, 0, {
                                # 'name': buyer.name,
                                # 'is_data_required': buyer.is_data_required,
                                'client_type': buyer.client_type,
                                'client_type_name': f"Buyer {buyer_count + 1}",
                                'order_sequence': buyer_count + 1,
                                # 'is_attachment_required': buyer.is_attachment_required
                            })]
                            content_vals.extend(vals)

            if content_list.get('seller'):
                if content_list.get('minor_guardian') and self.is_seller_minor and self.seller_party_type == 'individual':
                    for minor_seller in content_list.get('minor_guardian'):
                        vals = [(0, 0, {
                            # 'name': buyer.name,
                            # 'is_data_required': buyer.is_data_required,
                            'is_seller_minor': self.is_seller_minor,
                            'client_type': minor_seller.client_type,
                            'client_type_name': f"Seller Guardian",
                            # 'is_attachment_required': buyer.is_attachment_required
                        })]
                        content_vals.extend(vals)
                if content_list.get('representative') and self.is_seller_representative:
                    representative_seller = ''
                    if self.seller_party_type == 'individual':
                        representative_seller = 'Individual'
                    if self.seller_party_type == 'company_firm_trust':
                        representative_seller = 'Company/Firm/Trust'
                    if self.seller_party_type == 'government':
                        representative_seller = 'Government'
                    for rep_seller in content_list.get('representative'):
                        vals = [(0, 0, {
                            # 'name': buyer.name,
                            # 'is_data_required': buyer.is_data_required,
                            'is_buyer_representative': self.is_seller_representative,
                            'client_type': rep_seller.client_type,
                            'client_type_name': f"Seller {representative_seller} Representative",
                            # 'is_attachment_required': buyer.is_attachment_required
                        })]
                        content_vals.extend(vals)

                for seller_count in range(self.no_of_seller):
                    for seller in content_list.get('seller'):
                        if self.seller_party_type == 'individual':
                            vals = [(0, 0, {
                                # 'name': buyer.name,
                                # 'is_data_required': buyer.is_data_required,
                                'client_type': seller.client_type,
                                'client_type_name': f"Seller {seller_count + 1}",
                                'order_sequence': seller_count + 1,
                                # 'is_attachment_required': buyer.is_attachment_required
                            })]
                            content_vals.extend(vals)

            if content_list.get('witness'):
                params = self.env['ir.config_parameter'].sudo()
                no_witness=int(params.get_param('custom_landoc.no_witness')) or 2
                for witness_count in range(no_witness):
                    for witness in content_list.get('witness'):
                        vals = [(0, 0, {
                            # 'name': buyer.name,
                            # 'is_data_required': buyer.is_data_required,
                            'client_type': witness.client_type,
                            'client_type_name': f"Witness {witness_count + 1}",
                            'order_sequence': witness_count + 1,
                            # 'is_attachment_required': buyer.is_attachment_required
                        })]
                        content_vals.extend(vals)

        service_vals = []
        if serive_checklist:
            is_service_checklist = True
            for service in serive_checklist.checklist_data_ids:
                vals = [(0, 0, {'name': service.name,
                                'is_data_required': service.is_data_required,
                                'is_attachment_required': service.is_attachment_required})]
                service_vals.extend(vals)

        property_vals = []
        if self.is_propertychecklist_needed and self.property_type_id:
            for property in self.property_type_id.checklist_line:
                vals = [(0, 0, {'name': property.name,
                                'is_data_required': property.is_data_required,
                                # 'client_type': service.client_type,
                                'is_attachment_required': property.is_attachment_required})]
                property_vals.extend(vals)

        if content_vals or property_vals or service_vals:
            checklist_inputs += check_list_model.create(
                {'name': self.name, 'lead_id': self.id, 'is_service_checklist':is_service_checklist, 'checklist_line_ids': content_vals,
                 'service_checklist_line': service_vals, 'property_checklist_line': property_vals})
            self.checklist_input_ids = [checklist_input.id for checklist_input in checklist_inputs]
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'danger',
                    'message': _(f"Please configure checklist for {self.service_id.name} !"),
                }
            }
