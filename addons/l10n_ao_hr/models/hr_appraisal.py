from odoo import fields, models, api


class HrAppraisal(models.Model):
    _inherit = "hr.appraisal"

    is_feedback_review = fields.Boolean('Did you review 360?', tracking=True, help='Did you review 360?')
    appraisal_skill_line = fields.One2many(comodel_name='hr.appraisal.skill.line',
                                           inverse_name='appraisal_id',
                                           string='Appraisal Skill line', tracking=True)
    start_date = fields.Date('Start Date', default=fields.datetime.today())
    employee_answer = fields.Html('Employee Answer')
    manager_answer = fields.Html('Manager Answer')


class HrAppraisalSkillLines(models.Model):
    _name = 'hr.appraisal.skill.line'
    skill_id = fields.Many2one('hr.employee.skill', string='skill')
    appraisal_id = fields.Many2one('hr.appraisal', string='Appraisal')
