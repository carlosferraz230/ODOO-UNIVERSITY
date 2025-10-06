from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT
from datetime import datetime


class Employee(models.Model):
    _inherit = 'hr.employee'

    employee_number = fields.Char('Employee Number', tracking=True)
    private_email = fields.Char(related='address_home_id.email', string="Email Privado", groups="hr.group_hr_user",
                                tracking=True)
    phone = fields.Char(related='address_home_id.phone', related_sudo=False, readonly=False, string="Telefone Privado",
                        groups="hr.group_hr_user", tracking=True)
    notes = fields.Text('Notes', groups="hr.group_hr_user", tracking=True)
    color = fields.Integer('Índice de cores', default=0, groups="hr.group_hr_user", tracking=True)
    barcode = fields.Char(string="ID do crachá", help="ID usado para identificação do funcionário.",
                          groups="hr.group_hr_user",
                          copy=False, tracking=True)
    pin = fields.Char(string="PIN", groups="hr.group_hr_user", copy=False,
                      help="PIN usado para Check In/Out no Modo Quiosque (se habilitado na Configuração).",
                      tracking=True)
    social_security = fields.Char('Número de segurança', size=40, tracking=True)
    fiscal_number = fields.Char('Número fiscal', size=40, tracking=True)
    registration_number = fields.Char('Número de registro do funcionário', groups="hr.group_hr_user", copy=False,
                                      tracking=True)
    payment_method = fields.Selection([('bank', 'Transferência'), ('cash', 'Dinheiro')],
                                      'Forma de pagamento', default='bank', tracking=True)
    admission_date = fields.Date('Data de início', tracking=True)
    last_work_date = fields.Date('Data final', tracking=True)
    age = fields.Integer('Idade', compute='_compute_age', store=True, tracking=True)
    bank_bank = fields.Many2one('res.bank', string='Banco', tracking=True)
    bank_account = fields.Char('Conta Bancaria', size=40, tracking=True)
    bank_iban = fields.Char('IBAN', size=40, tracking=True)
    is_foreign = fields.Boolean('É Estrangeiro?', help='If this employee is foreign, please check this box',
                                tracking=True)
    emergence_contact = fields.Many2one(comodel_name='res.partner', string='Contato de Emergências')
    langs = fields.Many2many(comodel_name='res.lang', string='língua', tracking=True)
    father = fields.Many2one(comodel_name='hr.father', string='Pai', tracking=True)
    mother = fields.Many2one(comodel_name='hr.mother', string='Mãe', tracking=True)
    job_id = fields.Many2one(comodel_name='hr.job', string='Cargo', tracking=True)
    establishment = fields.Many2one(comodel_name='hr.establishment', string='Local de trabalho', tracking=True)
    country_id = fields.Many2one('res.country', 'Nationality (Country)',
                                 groups="hr.group_hr_user", default=lambda l: l._default_country(), tracking=True)
    qualification = fields.Text(string='Qualificação', tracking=True)
    certificate = fields.Selection(selection_add=[
        ('primary_school', 'Primary school'),
        ('high_school', 'High school'),
        ('pre_university', 'Pre University'),
        ('university_attendance', 'University Attendance'),
        ('licensed', 'Licensed'),
        ('postgraduate', 'Postgraduate'),
        ('postgraduate_professional_training', 'Postgraduate Professional Training'),
        ('phd', 'PHD')
    ], default='other', groups="hr.group_hr_user", tracking=True)
    vehicle = fields.Char(string='Company Vehicle', groups="hr.group_hr_user", tracking=True)
    contract_id = fields.Many2one('hr.contract', string='Current Contract',
                                  groups="hr.group_hr_user", domain="[('company_id', '=', company_id)]",
                                  help='Current contract of the employee', tracking=True)
    calendar_mismatch = fields.Boolean(related='contract_id.calendar_mismatch', tracking=True)
    exempt_irt = fields.Boolean(string="IRT", default=1, tracking=True)
    exempt_ss = fields.Boolean(string="SS", default=1, tracking=True)
    location_province = fields.Many2one('res.country.state', string='Provincia')
    County_address = fields.Many2one('res.country.state.county', string='Municipio')
    structure_type_id = fields.Many2one(comodel_name='hr.payroll.structure.type', string="Salary Structure Type")
    company_partner = fields.Boolean(string="Governing Body")
    end_date = fields.Datetime(string='End Date', default=datetime.now())


    @api.constrains('birthday')
    def _check_birth_date(self):
        for res in self:
            if res.birthday >= fields.Date.today():
                raise ValidationError(_(
                    "A data de nascimento não pode ser maior que a data atual!"))
            if res.birthday:
                res.age = fields.Date.today().year - res.birthday.year
                if res.age < 17:
                    raise ValidationError(_(
                        "Não é admitido funcionários menores de 18 anos\n"
                    ))

    @api.depends('birthday')
    def _compute_age(self):
        for res in self:
            if res.birthday:
                res.age = fields.Date.today().year - res.birthday.year

    def _default_country(self):
        return self.env.ref('base.ao').id

    @api.model
    def create(self, vals):
        result = super(Employee, self).create(vals)
        if result.father:
            result.father.child_ids |= result
        if result.mother:
            result.mother.child_ids |= result
        return result

    def get_all_employee_contract(self):
        contract_ids = self.env['hr.contract'].search([('employee_id', '=', self.id)])
        if contract_ids:
            return contract_ids

    # def _get_contract(self):
    #     contract = self.env['hr.contract'].search([('employee_id', '=', self.id)]).id
    #     return contract

    def get_all_employee_list(self):
        return self.env['hr.employee'].search([])

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "O nome desse Funcionário já existe na lista !"),
    ]


class HrEstablishment(models.Model):
    _name = 'hr.establishment'

    name = fields.Char(string="Work Location")


class ContractActiveCompany(models.Model):
    _name = 'hr.contract.company.assets'
    _description = 'Company Assets'

    name = fields.Char(string='Name')
    purchase_date = fields.Date('Purchase Date')
    ref = fields.Char(string='Reference')
    cost_price = fields.Float(string='Cost')
