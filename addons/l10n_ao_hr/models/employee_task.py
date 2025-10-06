from odoo import fields, models, api, _
from datetime import datetime
from odoo.exceptions import UserError, ValidationError


class EmployeeTask(models.Model):
    _name = 'hr.employee.task'
    _description = 'Employee Task'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Name')
    owner = fields.Many2one(comodel_name='hr.employee', string='Owner')
    start_date = fields.Datetime('Start Date', default=datetime.now())
    end_date = fields.Datetime('End Date', default=datetime.now())
    total_time = fields.Char('Total Time', compute='compute_total_time')
    cancel_date = fields.Datetime('Cancel Date')
    state = fields.Selection(
        [('new', 'Novo'), ('in_progress', 'EM PROGRESSO'), ('done', 'FEITO'), ('canceled', 'CANCELADO')],
        default='new', string='State')
    description = fields.Html('Description')

    def start_task(self):
        self.state = 'in_progress'
        self.start_date = fields.Datetime.now()
        # self.message_post('Começou a executar a tarefa.')

    def cancel_task(self):
        self.state = 'canceled'
        self.cancel_date = fields.Datetime.now()
        # self.message_post('Cancelou a tarefa.')

    def done_task(self):
        self.state = 'done'
        self.end_date = fields.Datetime.now()
        # self.message_post('Terminou a tarefa.')

    @api.depends('start_date', 'end_date')
    def compute_total_time(self):
        for rec in self:
            if rec.end_date:
                rec.total_time = str(rec.end_date - rec.start_date)
            else:
                rec.total_time = '00:00'

    @api.constrains('start_date', 'end_date')
    def check_start_date(self):
        if self.start_date and self.end_date:
            print(self.end_date)
            if self.end_date < self.start_date and self.state == 'new':
                raise ValidationError(_('A data de término não pode ser menor que a data de início'))


class Employee(models.Model):
    _inherit = 'hr.employee'
    task_id = fields.One2many('hr.employee.task', 'owner', string='Task')
