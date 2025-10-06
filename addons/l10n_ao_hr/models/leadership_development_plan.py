from odoo import fields, models, api, _
from odoo.exceptions import Warning


class HrCareerPlan(models.Model):
    _name = 'hr.career.plan'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Career Plan'

    name = fields.Char('Name', tracking=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', tracking=True)
    manager_id = fields.Many2one('hr.employee', related='employee_id.parent_id', string='Employee Manager',
                                 tracking=True)
    career_goals = fields.Text('Career Goals', tracking=True)
    strategy = fields.Text('Strategy', tracking=True)
    manager_comments = fields.Text('Remarks by Supervisor', tracking=True)
    manager_sign_date = fields.Date('Manager Sign Date', tracking=True)
    employee_comments = fields.Text('Employee Comments', tracking=True)
    employee_sign_date = fields.Date('Employee Sign Date', tracking=True)
    action_plan_line = fields.One2many(comodel_name='career.action.plan.line',
                                       inverse_name='career_plan_id',
                                       string='Career Plan line', tracking=True)
    mid_term_line = fields.One2many(comodel_name='career.mid.term.line', inverse_name='career_plan_id',
                                    string='Mid Term Goal', tracking=True)
    long_term_line = fields.One2many(comodel_name='career.long.term.line', inverse_name='career_plan_id',
                                     string='Long Term Goal', tracking=True)
    swot_analyse_line = fields.One2many(comodel_name='swot.analyse.line', inverse_name='career_plan_id',
                                        string='Swot Analysis', tracking=True)
    career_goals_line = fields.One2many(comodel_name='career.goals.line', inverse_name='career_plan_id',
                                        string='Career Goals', tracking=True)

    def button_employee_sign(self):
        if self.env.user.employee_id.id == self.employee_id.id:
            self.employee_sign_date = fields.datetime.today()
        else:
            raise Warning(_('Only Employee can sign this plan!'))

    def button_manager_sign(self):
        if self.env.user.employee_id.id == self.manager_id.id:
            self.employee_sign_date = fields.datetime.today()
        else:
            raise Warning(_('Only Employee can sign this plan!'))


class SwotAnalyseLine(models.Model):
    _name = 'swot.analyse.line'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    strengths = fields.Char('Strengths', tracking=True)
    weaknesses = fields.Char('Weaknesses', tracking=True)
    opportunities = fields.Char('Opportunities', tracking=True)
    threats = fields.Char('Threats', tracking=True)
    career_plan_id = fields.Many2one(comodel_name='hr.career.plan', string='Career Plan')


class CareerGoals(models.Model):
    _name = 'career.goals.line'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    action = fields.Char('Action', tracking=True)
    employee_id = fields.Many2one('hr.employee', string='Assign to', tracking=True)
    deadline = fields.Date('Deadline', tracking=True)
    progress = fields.Char('Progress', tracking=True)
    career_plan_id = fields.Many2one(comodel_name='hr.career.plan', string='Career Plan')


class CareerActionPlan(models.Model):
    _name = 'career.action.plan.line'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    action = fields.Char('Action', tracking=True)
    employee_id = fields.Many2one('hr.employee', string='Assign to', tracking=True)
    deadline = fields.Date('Deadline', tracking=True)
    progress = fields.Char('Progress', tracking=True)
    career_plan_id = fields.Many2one(comodel_name='hr.career.plan', string='Career Plan')


class CareerMidTermGol(models.Model):
    _name = 'career.mid.term.line'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    action = fields.Char('Action', tracking=True)
    employee_id = fields.Many2one('hr.employee', string='Assign to', tracking=True)
    deadline = fields.Date('Deadline', tracking=True)
    progress = fields.Char('Progress', tracking=True)
    career_plan_id = fields.Many2one(comodel_name='hr.career.plan', string='Career Plan')


class CareerMidTermGol(models.Model):
    _name = 'career.long.term.line'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    action = fields.Char('Action', tracking=True)
    employee_id = fields.Many2one('hr.employee', string='Assign to', tracking=True)
    deadline = fields.Date('Deadline', tracking=True)
    progress = fields.Char('Progress', tracking=True)
    career_plan_id = fields.Many2one(comodel_name='hr.career.plan', string='Career Plan')
