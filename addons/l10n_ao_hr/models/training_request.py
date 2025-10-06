from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, Warning


class TrainingRequest(models.Model):
    _name = 'hr.training.request'
    _description = 'Training Request'
    _rec_name = 'employee_id'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    employee_id = fields.Many2one('hr.employee', string='Employee', tracking=True)
    department_id = fields.Many2one(
        'hr.department', related='employee_id.department_id', string='Department', store=True, tracking=True)
    job_id = fields.Many2one('hr.job', related='employee_id.job_id', tracking=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, tracking=True)
    currency_id = fields.Many2one('res.currency', string='Currency', related='company_id.currency_id', tracking=True)
    mobile_phone = fields.Char("Phone", related='employee_id.mobile_phone', groups="hr.group_hr_user", tracking=True)
    institution_address = fields.Char('Institution Address', tracking=True)
    institution_phone = fields.Char('Institution Phone', tracking=True)
    institution_email = fields.Char('Institution Email', tracking=True)
    course_type = fields.Char('Course Type', tracking=True)
    course_amount = fields.Monetary('Course Amount', tracking=True)
    payment_method = fields.Selection([('cash', 'Cash'), ('check', 'Check'), ('bank_transfer', 'Bank Transfer')],
                                      string='Payment Method', default='cash', tracking=True)
    employee_payment_amount = fields.Monetary('Employee 15% amount', tracking=True)
    course_start_date = fields.Datetime('Start Date', tracking=True)
    course_end_date = fields.Datetime('End Date', tracking=True)
    initials = fields.Char('Initials', tracking=True)
    department_boss_id = fields.Many2one('hr.employee', string='Department Boss', tracking=True)
    department_boss = fields.Boolean(string='Department Boss', tracking=True)

    resident_representative_id = fields.Many2one('hr.employee', string='Resident Representative',
                                                 tracking=True)
    resident_representative = fields.Boolean(string='Resident Representative', tracking=True)
    resident_representative_date = fields.Date('Date', tracking=True)
    department_boss_date = fields.Date('Date', tracking=True)
    hr_manager_id = fields.Many2one('hr.employee', string='Hr Manager', tracking=True)
    hr_manager_date = fields.Date('Date', tracking=True)
    hr_manager = fields.Boolean('Hr Manager', tracking=True)

    request_by = fields.Many2one('hr.employee', string='Request By', tracking=True)
    received_by = fields.Many2one('hr.employee', string='Received By', tracking=True)
    received_date = fields.Date(string='Received Date', tracking=True)
    other_details = fields.Text('Other Details', tracking=True)

    employee_sign_date = fields.Date('Employee Sign Date', tracking=True)

    def get_employee_user(self):
        employee_id = self.env['hr.employee'].search([('user_id', '=', self._uid)])
        if employee_id:
            return employee_id

    def button_employee_sign(self):
        if self.env.user.employee_id.id == self.employee_id.id:
            self.employee_sign_date = fields.datetime.today()
        else:
            raise Warning(_('Only Employee can sign this training request!'))

    def department_boss_approve(self):
        self.department_boss = True
        self.department_boss_id = self.get_employee_user().id
        self.department_boss_date = fields.date.today()

    def department_boss_disapprove(self):
        self.department_boss = False
        self.department_boss_id = self.get_employee_user().id
        self.department_boss_date = fields.date.today()

    def hr_manager_approve(self):
        self.hr_manager = True
        self.hr_manager_id = self.get_employee_user().id
        self.hr_manager_date = fields.date.today()

    def hr_manager_disapprove(self):
        self.hr_manager = False
        self.hr_manager_id = self.get_employee_user().id
        self.hr_manager_date = fields.date.today()

    def resident_approve(self):
        self.resident_representative = True
        self.resident_representative_id = self.get_employee_user().id
        self.resident_representative_date = fields.date.today()

    def resident_disapprove(self):
        self.resident_representative = False
        self.resident_representative_id = self.get_employee_user().id
        self.resident_representative_date = fields.date.today()
