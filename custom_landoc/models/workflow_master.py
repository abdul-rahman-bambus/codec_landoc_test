from odoo import fields, models, api, _


class WorkflowMaster(models.Model):
    _name = 'workflow.master'
    _description = 'Workflow Master'
    _rec_name = "name"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    sequence = fields.Char(string="Sequence", required=True, copy=False, readonly=False,
                           default=lambda self: _('New'))
    name = fields.Char(string="Name", required=True, tracking=True)
    add_default_workflow = fields.Boolean(string="Add Default Workflow")
    workflow_ids = fields.One2many(comodel_name="workflow.line", inverse_name='workflow_id')
    category_id = fields.Many2one(comodel_name="product.category", tracking=True,
                                    domain="[('is_service','=',True)]",
                                    string="Category")
    checklist_ids = fields.One2many(comodel_name='service.checklist',
                                    inverse_name='workflow_master_id', string="Checklist")
    company_id = fields.Many2one(comodel_name='res.company', tracking=1, index=True)
    is_ec_service = fields.Boolean(string="Is EC Service", tracking=True)
    ec_year_applicable = fields.Selection(selection=[('before_1975', 'Before 1975'),('after_1975', 'After 1975'),], tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        """Extended ORM:- CREATE"""
        for vals in vals_list:
            if vals.get('sequence', _('New')) == _('New'):
                vals['sequence'] = self.env['ir.sequence'].with_company(vals.get('company_id')).next_by_code(
                    'workflow.master') or _('New')

        return super().create(vals_list)

    @api.onchange('add_default_workflow')
    def _onchange_add_default_workflow(self):
        """Onchange functionality for default workflow."""
        if self.add_default_workflow:
            update_list = []
            work_flows = self.env['workflow.default'].search([])
            for work_flow in work_flows:
                update_list.append((0, 0, {
                    'department_id': work_flow.department_id.id,
                    'landoc_stage': work_flow.landoc_stage,
                    'stage_id': work_flow.stage_id.id,
                    'default_workflow': work_flow.default_workflow,
                }))
            self.write({'workflow_ids': update_list})
        else:
            for work_flow_e in self.workflow_ids.filtered(lambda w: w.default_workflow):
                work_flow_e.unlink()

