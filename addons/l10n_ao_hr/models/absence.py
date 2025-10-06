from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, Warning
from datetime import datetime


class ModelName(models.Model):
    _name = 'absent.holiday.psi'
    _description = 'record absent psi'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    employee_id = fields.Many2one('hr.employee', string='Nome do trabalhador', tracking=True)
    state = fields.Selection([('new', 'Novo'), ('sign', 'Assinado'), ('rejected', 'Rejected')], default='new')
    job_id = fields.Many2one('hr.job', related='employee_id.job_id', tracking=True)
    contract_id = fields.Many2one('hr.contract', related='employee_id.contract_id')
    date_contract_id = fields.Date(related='contract_id.date_start', tracking=True)
    subsidy = fields.Boolean('subsidy holiday', default=datetime.today(), tracking=True)
    qty_day = fields.Integer('vacation day')
    qty_mother_day = fields.Integer('day of mother')
    balance_holiday_present_date = fields.Integer('Balance holiday present date')
    day_holiday_enjoy = fields.Integer('Day holiday enjoy')
    date_ref_year = fields.Date()
    date_start = fields.Date()
    end_date = fields.Date()
    date_presentation = fields.Date()
    sign = fields.Boolean('Sign')
    date_sign = fields.Date()
    day_holiday_approved_now = fields.Integer('day holiday approved now')
    date_holiday_enjoy_still = fields.Integer('day holiday still enjoy')
    date_check_rh = fields.Text('human resources check')
    date_rh_check = fields.Date()
    employee_id_approved = fields.Many2one('hr.employee', string='Approved', tracking=True)
    employee_id_approved_text = fields.Text('Approval of the Human Resources Coordinator')
    date_rh_approved = fields.Date()

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
    department_boss_id = fields.Many2one('hr.employee', string='Verificação dos Recursos Humanos', tracking=True)
    department_boss = fields.Boolean(string='Verificação dos Recursos Humanos', tracking=True)

    resident_representative_id = fields.Many2one('hr.employee',
                                                 string='Aprovação do Supervisor/Director do departamento',
                                                 tracking=True)
    resident_representative = fields.Boolean(string='Aprovação do Supervisor/Director do departamento', tracking=True)
    resident_representative_date = fields.Date('Date', tracking=True)
    department_boss_date = fields.Date('Date', tracking=True)
    hr_manager_id = fields.Many2one('hr.employee', string='HAprovação  do(a) Coordenador(a) dos Recursos Humanos  ',
                                    tracking=True)
    hr_manager_date = fields.Date('Date', tracking=True)
    hr_manager = fields.Boolean('Aprovação  do(a) Coordenador(a) dos Recursos Humanos  ', tracking=True)

    request_by = fields.Many2one('hr.employee', string='Request By', tracking=True)
    received_by = fields.Many2one('hr.employee', string='Received By', tracking=True)
    received_date = fields.Date(string='Received Date', tracking=True)
    other_details = fields.Text('Other Details', tracking=True)

    employee_sign_date = fields.Date('Employee Sign Date', tracking=True)

    def get_employee_user(self):
        employee_id = self.env['hr.employee'].search([('user_id', '=', self._uid)])
        if employee_id:
            return employee_id

    def button_employee_rejected(self):
        self.state='rejected'

    def button_employee_sign(self):
        if self.env.user.employee_id.id == self.employee_id.id:
            self.employee_sign_date = fields.datetime.today()
            self.state = 'sign'
        else:
            raise Warning(_('Somente o Funcionário pode assinar esta solicitação de ausência'))

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
