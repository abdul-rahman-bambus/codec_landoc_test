from odoo import api, models, fields


class ChecklistTrackingPrevious(models.TransientModel):
    _name = 'checklist.tracking.previous'
    _description = 'Checklist Tracking Previous'

    choose_step = fields.Selection(selection=[('just_before_step','Just Before Step'), ('jump_previous_checklist_step','Jump Previous Checklist Step')], default="just_before_step", string="Step")
    lead_id = fields.Many2one(comodel_name="crm.lead", readonly=True)
    crm_checklist_tracking_id = fields.Many2one(comodel_name="crm.checklist.tracking", string="Step  ")
    compute_steps = fields.Many2many(comodel_name="crm.checklist.tracking", compute="_compute_steps")
    company_id = fields.Many2one(comodel_name='res.company',index=True)

    @api.depends('lead_id')
    def _compute_steps(self):
        for step in self:
            previous_ids = []
            for checklist in step.lead_id.checklist_tracking_line:
                if checklist.active_step:
                    break
                previous_ids.append(checklist.id)
            step.compute_steps = previous_ids

    def action_previous_checklist(self):
        if self.choose_step == 'just_before_step':
            previous_checklist = self.env['crm.checklist.tracking']
            for checklist in self.lead_id.checklist_tracking_line:
                if not checklist.active_step:
                    previous_checklist = checklist
                if checklist.active_step:
                    break
            if previous_checklist:
                for rec in self.lead_id.checklist_tracking_line:
                    rec.active_step = False
            previous_checklist.active_step = True
            self.lead_id.team_id = previous_checklist.department_id.id

        if self.choose_step == 'jump_previous_checklist_step':
            for rec in self.lead_id.checklist_tracking_line:
                rec.active_step = False
            self.crm_checklist_tracking_id.active_step = True
            self.lead_id.team_id = self.crm_checklist_tracking_id.department_id.id

